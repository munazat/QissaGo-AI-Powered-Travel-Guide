"""Generate, view, save and list itineraries."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.db.models import AgentRun, ChatSession, City, Itinerary, User
from app.db.session import get_db
from app.schemas.api import GenerateIn, GenerateOut, ItineraryOut, ItinerarySummary
from app.schemas.preferences import TripPreferences
from app.services.catalog import Catalog

from .deps import catalog, current_user

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


def summary(it: Itinerary, city_name: str) -> dict:
    return {
        "id": it.id,
        "batch_id": it.batch_id,
        "city_id": it.city_id,
        "city_name": city_name,
        "variant": it.variant,
        "title": it.title,
        "label": it.plan.get("label", ""),
        "match_score": it.match_score,
        "total_cost": it.total_cost,
        "start_date": it.start_date,
        "days": it.days,
        "saved": it.saved,
        "image": it.plan.get("image", ""),
        "created_at": it.created_at,
    }


def full(it: Itinerary, city_name: str) -> ItineraryOut:
    return ItineraryOut(**summary(it, city_name), preferences=it.preferences, plan=it.plan)


def _owned(db: Session, itinerary_id: str, user: User) -> Itinerary:
    it = db.get(Itinerary, itinerary_id)
    if not it or it.user_id != user.id:
        raise HTTPException(404, "Itinerary not found")
    return it


def _city_name(db: Session, city_id: str) -> str:
    c = db.get(City, city_id)
    return c.name if c else city_id


@router.post("/generate", response_model=GenerateOut)
def generate(
    body: GenerateIn, user: User = Depends(current_user), db: Session = Depends(get_db), cat: Catalog = Depends(catalog)
) -> GenerateOut:
    session = None
    if body.session_id:
        session = db.get(ChatSession, body.session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(404, "Chat not found")
        prefs = TripPreferences(**session.preferences)
    elif body.preferences:
        prefs = body.preferences
    else:
        raise HTTPException(400, "Send a chat session or trip preferences")
    if prefs.missing():
        raise HTTPException(400, f"Missing trip details: {', '.join(prefs.missing())}")
    if prefs.start_date and prefs.start_date < dt.date.today():
        raise HTTPException(400, "The start date has already passed")

    try:
        result = Orchestrator().run(prefs, cat)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    batch_id = uuid.uuid4().hex
    city_name = cat.cities[prefs.city]["name"]
    saved: list[Itinerary] = []
    for p in result["plans"]:
        plan = {**p["plan"], "label": p["label"], "image": p["image"]}
        it = Itinerary(
            user_id=user.id,
            session_id=session.id if session else None,
            batch_id=batch_id,
            city_id=prefs.city,
            variant=p["variant"],
            title=p["title"],
            match_score=p["match_score"],
            total_cost=p["plan"]["totals"]["total"],
            start_date=prefs.start_date,
            days=prefs.days,
            preferences=prefs.model_dump(mode="json"),
            plan=plan,
        )
        db.add(it)
        saved.append(it)
    for t in result["trace"]:
        db.add(AgentRun(batch_id=batch_id, agent=t["agent"], message=t["message"], duration_ms=t["ms"]))
    if session:
        session.status = "planned"
    db.commit()
    return GenerateOut(
        batch_id=batch_id,
        itineraries=[full(i, city_name) for i in saved],
        trace=result["trace"],
        weather_source=result["weather_source"],
    )


@router.get("", response_model=list[ItinerarySummary])
def list_saved(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(Itinerary, City.name)
        .join(City, City.id == Itinerary.city_id)
        .filter(Itinerary.user_id == user.id, Itinerary.saved.is_(True))
        .order_by(Itinerary.created_at.desc())
        .all()
    )
    return [summary(it, name) for it, name in rows]


RECENT_BATCHES = 6


@router.get("/recent", response_model=list[ItinerarySummary])
def recent(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    """Best option of each of the user's latest plan batches, newest first."""
    rows = (
        db.query(Itinerary, City.name)
        .join(City, City.id == Itinerary.city_id)
        .filter(Itinerary.user_id == user.id)
        .order_by(Itinerary.created_at.desc())
        .limit(RECENT_BATCHES * 3)
        .all()
    )
    best: dict[str, tuple[Itinerary, str]] = {}
    for it, name in rows:
        if it.batch_id not in best or it.match_score > best[it.batch_id][0].match_score:
            best[it.batch_id] = (it, name)
    return [summary(it, name) for it, name in list(best.values())[:RECENT_BATCHES]]


@router.get("/batch/{batch_id}", response_model=list[ItineraryOut])
def batch(batch_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[ItineraryOut]:
    rows = (
        db.query(Itinerary)
        .filter(Itinerary.batch_id == batch_id, Itinerary.user_id == user.id)
        .order_by(Itinerary.match_score.desc())
        .all()
    )
    if not rows:
        raise HTTPException(404, "Plans not found")
    name = _city_name(db, rows[0].city_id)
    return [full(i, name) for i in rows]


@router.get("/{itinerary_id}", response_model=ItineraryOut)
def get_one(itinerary_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ItineraryOut:
    it = _owned(db, itinerary_id, user)
    return full(it, _city_name(db, it.city_id))


@router.post("/{itinerary_id}/save", response_model=ItinerarySummary)
def save(itinerary_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    it = _owned(db, itinerary_id, user)
    it.saved = True
    db.commit()
    return summary(it, _city_name(db, it.city_id))


@router.delete("/{itinerary_id}/save", response_model=ItinerarySummary)
def unsave(itinerary_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    it = _owned(db, itinerary_id, user)
    it.saved = False
    db.commit()
    return summary(it, _city_name(db, it.city_id))
