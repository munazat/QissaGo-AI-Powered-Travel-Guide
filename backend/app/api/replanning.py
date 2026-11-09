from __future__ import annotations

import copy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.budget import trip_totals
from app.db.models import Itinerary, ItineraryVersion, ReplanRequest, User
from app.db.session import get_db
from app.replanning.parser import parse_changes
from app.replanning.service import apply_changes
from app.schemas.replanning import (
    ProgressBody,
    ReplanBody,
    ReplanResponse,
    RestoreBody,
    VersionResponse,
    WeatherSuggestionResponse,
)
from app.services.catalog import Catalog

from .deps import catalog, current_user

router = APIRouter(prefix="/itineraries", tags=["replanning"])


def _owned(db: Session, itinerary_id: str, user: User) -> Itinerary:
    itinerary = db.get(Itinerary, itinerary_id)
    if not itinerary or itinerary.user_id != user.id:
        raise HTTPException(404, "Itinerary not found")
    return itinerary


def _prefs(itinerary: Itinerary) -> dict:
    prefs = copy.deepcopy(itinerary.preferences)
    prefs["city_id"] = itinerary.city_id
    prefs["city"] = itinerary.city_id
    prefs["size"] = prefs.get("group_size") or 1
    prefs["days"] = itinerary.days
    prefs["day_start"] = "11:00" if "late_start" in prefs.get("needs", []) else "09:00"
    return prefs


def _execution(itinerary: Itinerary) -> dict:
    return copy.deepcopy(itinerary.plan.get("execution", {}))


def _preview(itinerary: Itinerary, body: ReplanBody, cat: Catalog) -> tuple[dict, object, object]:
    changes = [body.change] if body.change else parse_changes(body.request_text)
    next_plan, diff = apply_changes(itinerary.plan, _prefs(itinerary), changes, cat, _execution(itinerary))
    p = _prefs(itinerary)
    p["city"] = cat.cities[itinerary.city_id]
    p["budget"] = p.get("budget") or next_plan.get("totals", {}).get("budget", 0)
    totals = trip_totals(next_plan["days"], p, next_plan.get("totals", {}).get("hotel", "budget"))
    if not totals["within"]:
        raise ValueError("That change would exceed the trip budget.")
    next_plan["totals"] = totals
    return next_plan, diff, changes


@router.post("/{itinerary_id}/replan", response_model=ReplanResponse)
def replan(
    itinerary_id: str,
    body: ReplanBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    cat: Catalog = Depends(catalog),
) -> ReplanResponse:
    itinerary = _owned(db, itinerary_id, user)
    try:
        next_plan, diff, changes = _preview(itinerary, body, cat)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    latest = (
        db.query(ItineraryVersion)
        .filter(ItineraryVersion.itinerary_id == itinerary.id)
        .order_by(ItineraryVersion.version.desc())
        .first()
    )
    version_number = (latest.version if latest else 0) + 1
    request = ReplanRequest(
        itinerary_id=itinerary.id,
        user_id=user.id,
        request_text=body.request_text,
        parsed_change={"changes": [change.model_dump(mode="json") for change in changes]},
        status="applied",
    )
    db.add(request)
    db.add(
        ItineraryVersion(
            itinerary_id=itinerary.id,
            version=version_number,
            plan=copy.deepcopy(itinerary.plan),
            reason=body.request_text,
        )
    )
    itinerary.plan = next_plan
    itinerary.total_cost = next_plan["totals"]["total"]
    db.commit()
    return ReplanResponse(
        itinerary_id=itinerary.id,
        version=version_number,
        plan=next_plan,
        diff=diff,
        trace=[{"agent": "Replanning Agent", "message": f"Updated day(s): {diff.affected_days}"}],
    )


@router.post("/{itinerary_id}/replan/preview", response_model=ReplanResponse)
def replan_preview(
    itinerary_id: str,
    body: ReplanBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    cat: Catalog = Depends(catalog),
) -> ReplanResponse:
    itinerary = _owned(db, itinerary_id, user)
    try:
        next_plan, diff, _ = _preview(itinerary, body, cat)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return ReplanResponse(
        itinerary_id=itinerary.id,
        version=0,
        plan=next_plan,
        diff=diff,
        trace=[{"agent": "Replanning Agent", "message": "Preview only; no changes were saved."}],
    )


@router.get("/{itinerary_id}/progress")
def progress(itinerary_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    itinerary = _owned(db, itinerary_id, user)
    return _execution(itinerary)


@router.put("/{itinerary_id}/progress")
def update_progress(
    itinerary_id: str,
    body: ProgressBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    itinerary = _owned(db, itinerary_id, user)
    if body.day > itinerary.days:
        raise HTTPException(400, "That day is outside this itinerary.")
    known = {
        item.get("id")
        for day in itinerary.plan.get("days", [])
        for item in day.get("items", [])
        if item.get("kind") == "stop"
    }
    requested = set(body.completed_stop_ids) | set(body.skipped_stop_ids)
    unknown = requested - known
    if unknown:
        raise HTTPException(400, f"Unknown stop(s) for day {body.day}: {', '.join(sorted(unknown))}")
    execution = body.model_dump(exclude_none=True)
    itinerary.plan = copy.deepcopy(itinerary.plan)
    itinerary.plan["execution"] = execution
    db.commit()
    return execution


@router.get("/{itinerary_id}/versions", response_model=list[VersionResponse])
def versions(
    itinerary_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[VersionResponse]:
    _owned(db, itinerary_id, user)
    rows = (
        db.query(ItineraryVersion)
        .filter(ItineraryVersion.itinerary_id == itinerary_id)
        .order_by(ItineraryVersion.version.desc())
        .all()
    )
    return [
        VersionResponse(id=row.id, version=row.version, reason=row.reason, created_at=row.created_at) for row in rows
    ]


@router.post("/{itinerary_id}/versions/restore", response_model=ReplanResponse)
def restore(
    itinerary_id: str,
    body: RestoreBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReplanResponse:
    itinerary = _owned(db, itinerary_id, user)
    version = (
        db.query(ItineraryVersion)
        .filter(ItineraryVersion.itinerary_id == itinerary_id, ItineraryVersion.version == body.version)
        .first()
    )
    if not version:
        raise HTTPException(404, "Itinerary version not found")
    latest = (
        db.query(ItineraryVersion)
        .filter(ItineraryVersion.itinerary_id == itinerary.id)
        .order_by(ItineraryVersion.version.desc())
        .first()
    )
    next_number = (latest.version if latest else 0) + 1
    db.add(
        ItineraryVersion(
            itinerary_id=itinerary.id,
            version=next_number,
            plan=copy.deepcopy(itinerary.plan),
            reason=f"Restored version {body.version}",
        )
    )
    itinerary.plan = copy.deepcopy(version.plan)
    itinerary.total_cost = itinerary.plan.get("totals", {}).get("total", itinerary.total_cost)
    db.commit()
    return ReplanResponse(
        itinerary_id=itinerary.id,
        version=next_number,
        plan=itinerary.plan,
        diff={"affected_days": [], "reason": f"restore:{body.version}"},
        trace=[{"agent": "Replanning Agent", "message": f"Restored version {body.version}"}],
    )


@router.get("/{itinerary_id}/weather-suggestions", response_model=WeatherSuggestionResponse)
def weather_suggestions(
    itinerary_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    cat: Catalog = Depends(catalog),
) -> WeatherSuggestionResponse:
    itinerary = _owned(db, itinerary_id, user)
    suggestions = []
    indoor = [p for p in cat.pois(itinerary.city_id) if not p["outdoor"]]
    for day in itinerary.plan.get("days", []):
        weather = day.get("weather", {})
        if not weather.get("rainy"):
            continue
        replacement = indoor[0] if indoor else None
        for stop in day.get("items", []):
            if stop.get("kind") != "stop" or not stop.get("outdoor"):
                continue
            suggestions.append(
                {
                    "day": day["day"],
                    "stop_id": stop["id"],
                    "stop_name": stop["name"],
                    "message": f"Rain is likely on day {day['day']}; consider replacing {stop['name']}.",
                    "suggested_place_id": replacement["id"] if replacement else None,
                    "suggested_place_name": replacement["name"] if replacement else None,
                }
            )
    return WeatherSuggestionResponse(suggestions=suggestions)
