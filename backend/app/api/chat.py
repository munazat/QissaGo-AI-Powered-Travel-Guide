"""Chatbot endpoints. Every message and the current preferences are saved in PostgreSQL."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.intake.conversation import Turn, greeting, handle_turn
from app.db.models import ChatMessage, ChatSession, User
from app.db.session import get_db
from app.schemas.api import ChatIn, ChatMessageOut, ChatSessionOut, ChatTurnOut
from app.schemas.preferences import TripPreferences
from app.services.catalog import Catalog
from app.services.llm import LLM

from .deps import catalog, current_user, llm

router = APIRouter(prefix="/chat", tags=["chat"])


def _session(db: Session, session_id: str, user: User) -> ChatSession:
    s = db.get(ChatSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Chat not found")
    return s


def _turn_out(s: ChatSession, turn: Turn) -> ChatTurnOut:
    return ChatTurnOut(
        session_id=s.id,
        reply=turn.reply,
        suggestions=turn.suggestions,
        awaiting=turn.awaiting,
        missing=turn.preferences.missing(),
        ready=turn.ready,
        action=turn.action,
        preferences=turn.preferences,
    )


@router.post("/sessions", response_model=ChatTurnOut, status_code=201)
def start(
    user: User = Depends(current_user), db: Session = Depends(get_db), cat: Catalog = Depends(catalog)
) -> ChatTurnOut:
    turn = greeting(user.name, cat)
    s = ChatSession(user_id=user.id, preferences=turn.preferences.model_dump(mode="json"), awaiting=turn.awaiting)
    s.messages.append(ChatMessage(role="bot", content=turn.reply))
    db.add(s)
    db.commit()
    return _turn_out(s, turn)


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
def get_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ChatSessionOut:
    s = _session(db, session_id, user)
    prefs = TripPreferences(**s.preferences)
    return ChatSessionOut(
        session_id=s.id,
        reply=s.messages[-1].content if s.messages else "",
        suggestions=[],
        awaiting=s.awaiting,
        missing=prefs.missing(),
        ready=s.status in ("ready", "planned"),
        preferences=prefs,
        messages=[ChatMessageOut(role=m.role, content=m.content, created_at=m.created_at) for m in s.messages],
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatTurnOut)
def send(
    session_id: str,
    body: ChatIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    cat: Catalog = Depends(catalog),
    model: LLM = Depends(llm),
) -> ChatTurnOut:
    if not (body.text and body.text.strip()) and not body.patch:
        raise HTTPException(400, "Send a message or a choice")
    s = _session(db, session_id, user)
    patch = body.patch.model_dump(exclude_none=True) if body.patch else None
    turn = handle_turn(
        TripPreferences(**s.preferences), s.awaiting, cat, dt.date.today(), model, text=body.text, patch=patch
    )
    if body.text and body.text.strip():
        s.messages.append(
            ChatMessage(
                role="user", content=body.text.strip(), extracted={k: str(v) for k, v in turn.extracted.items()}
            )
        )
    s.messages.append(ChatMessage(role="bot", content=turn.reply))
    s.preferences = turn.preferences.model_dump(mode="json")
    s.awaiting = turn.awaiting
    s.status = "ready" if turn.ready else "collecting"
    db.commit()
    return _turn_out(s, turn)
