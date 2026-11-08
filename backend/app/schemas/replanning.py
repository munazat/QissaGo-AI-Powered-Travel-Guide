from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.replanning.contracts import ChangeRequest, ReplanDiff


class ReplanBody(BaseModel):
    request_text: str = Field(min_length=1, max_length=1000)
    change: ChangeRequest | None = None
    preview: bool = False


class ProgressBody(BaseModel):
    day: int = Field(ge=1, le=31)
    completed_stop_ids: list[str] = Field(default_factory=list)
    skipped_stop_ids: list[str] = Field(default_factory=list)
    current_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    current_lat: float | None = Field(default=None, ge=-90, le=90)
    current_lon: float | None = Field(default=None, ge=-180, le=180)


class ReplanResponse(BaseModel):
    itinerary_id: str
    version: int
    plan: dict
    diff: ReplanDiff
    trace: list[dict]


class VersionResponse(BaseModel):
    id: int
    version: int
    reason: str | None
    created_at: datetime


class RestoreBody(BaseModel):
    version: int = Field(ge=1)


class WeatherSuggestionResponse(BaseModel):
    suggestions: list[dict]
