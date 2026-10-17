"""Request and response shapes for the API."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field

from .preferences import PreferencesPatch, TripPreferences


# ----------------------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class AuthOut(BaseModel):
    token: str
    user: UserOut


# ----------------------------------------------------------------------------- chat
class ChatIn(BaseModel):
    """Send `text` (typed message) and/or `patch` (button taps)."""

    text: str | None = Field(default=None, max_length=1000)
    patch: PreferencesPatch | None = None


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: dt.datetime


class ChatTurnOut(BaseModel):
    session_id: str
    reply: str
    suggestions: list[str]  # quick-reply chips
    awaiting: str  # field the bot is asking about ("" if none)
    missing: list[str]
    ready: bool  # true when plans can be generated
    action: str = ""  # "generate" when the user just confirmed
    preferences: TripPreferences


class ChatSessionOut(ChatTurnOut):
    messages: list[ChatMessageOut]


# ----------------------------------------------------------------------------- itineraries
class GenerateIn(BaseModel):
    """Either a chat session id, or full preferences from the quick-select form."""

    session_id: str | None = None
    preferences: TripPreferences | None = None


class ItinerarySummary(BaseModel):
    id: str
    batch_id: str
    city_id: str
    city_name: str
    variant: str
    title: str
    label: str
    match_score: int
    total_cost: int
    start_date: dt.date
    days: int
    saved: bool
    image: str
    created_at: dt.datetime


class ItineraryOut(ItinerarySummary):
    preferences: dict
    plan: dict


class GenerateOut(BaseModel):
    batch_id: str
    itineraries: list[ItineraryOut]
    trace: list[dict]
    weather_source: str
