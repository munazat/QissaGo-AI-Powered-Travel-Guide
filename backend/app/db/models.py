"""Database tables (PostgreSQL).

Places data (cities, interests, places) is loaded from CSV files by `scripts/seed_db.py`.
Everything else (users, chats, itineraries, agent runs) is written by the app.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


# ----------------------------------------------------------------------------- places
poi_interests = Table(
    "poi_interests",
    Base.metadata,
    Column("poi_id", ForeignKey("pois.id", ondelete="CASCADE"), primary_key=True),
    Column("interest_id", ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True),
)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "lahore"
    name: Mapped[str] = mapped_column(String(80))
    province: Mapped[str] = mapped_column(String(80), default="")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    aliases: Mapped[str] = mapped_column(String(200), default="")  # "lhr|lahor"
    hotel_budget: Mapped[int] = mapped_column(Integer)  # PKR per room per night
    hotel_mid: Mapped[int] = mapped_column(Integer)
    meal_pp_day: Mapped[int] = mapped_column(Integer)  # PKR per person per day
    transport_per_km: Mapped[int] = mapped_column(Integer)  # PKR per car per km
    jeep_per_day: Mapped[int] = mapped_column(Integer, default=0)  # PKR per hired jeep with driver, 0 = not needed
    speed_kmh: Mapped[float] = mapped_column(Float, default=24.0)  # typical local driving speed
    road_factor: Mapped[float] = mapped_column(Float, default=1.35)  # road km per straight-line km
    wiki_title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(300), default="")  # path under /static
    image_credit: Mapped[str] = mapped_column(String(300), default="")

    pois: Mapped[list[Poi]] = relationship(back_populates="city")


class Interest(Base):
    __tablename__ = "interests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "history"
    label: Mapped[str] = mapped_column(String(80))
    keywords: Mapped[str] = mapped_column(String(400), default="")  # words the chatbot recognises


class Poi(Base):
    """A place a traveller can visit."""

    __tablename__ = "pois"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # e.g. "lhr_fort"
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40))
    cost_pp: Mapped[int] = mapped_column(Integer, default=0)  # PKR per person for locals, entry + typical extras
    cost_foreign: Mapped[int] = mapped_column(Integer, default=0)  # PKR per person for foreign visitors
    access: Mapped[str] = mapped_column(String(20), default="")  # "jeep" when only reachable by hired jeep
    visit_minutes: Mapped[int] = mapped_column(Integer, default=60)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    outdoor: Mapped[bool] = mapped_column(Boolean, default=True)
    best_time: Mapped[str] = mapped_column(String(10), default="any")  # morning|midday|evening|any
    open_time: Mapped[str] = mapped_column(String(5), default="09:00")
    close_time: Mapped[str] = mapped_column(String(5), default="21:00")
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 3 = must-see, 1 = optional
    wiki_title: Mapped[str] = mapped_column(String(200), default="")
    wiki_url: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(300), default="")
    image_credit: Mapped[str] = mapped_column(String(300), default="")
    image_license: Mapped[str] = mapped_column(String(120), default="")

    city: Mapped[City] = relationship(back_populates="pois")
    interests: Mapped[list[Interest]] = relationship(secondary=poi_interests)


# ----------------------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ----------------------------------------------------------------------------- chat
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="collecting")  # collecting|ready|planned
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    awaiting: Mapped[str] = mapped_column(String(40), default="")  # field the bot just asked about
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", order_by="ChatMessage.id", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | bot
    content: Mapped[str] = mapped_column(Text)
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)  # what the extractor found
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


# ----------------------------------------------------------------------------- itineraries
class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)  # the 3 options made together
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"))
    variant: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(120))
    match_score: Mapped[int] = mapped_column(Integer)
    total_cost: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[dt.date] = mapped_column()
    days: Mapped[int] = mapped_column(Integer)
    preferences: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[dict] = mapped_column(JSON)  # days, stops, totals, stats
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AgentRun(Base):
    """One row per agent per plan generation: evidence of the multi-agent pipeline."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    agent: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
