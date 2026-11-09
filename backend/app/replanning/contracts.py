from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ChangeKind(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    MARK_VISITED = "mark_visited"
    MOVE = "move"
    START_LATER = "start_later"
    CHANGE_DAY = "change_day"


class ChangeRequest(BaseModel):
    kind: ChangeKind
    place_id: str | None = None
    day: int | None = Field(default=None, ge=1, le=31)
    target_day: int | None = Field(default=None, ge=1, le=31)
    minutes: int = Field(default=60, ge=15, le=240)

    @model_validator(mode="after")
    def validate_fields(self) -> ChangeRequest:
        if (
            self.kind
            in (ChangeKind.ADD, ChangeKind.REMOVE, ChangeKind.MARK_VISITED, ChangeKind.MOVE, ChangeKind.CHANGE_DAY)
            and not self.place_id
        ):
            raise ValueError("place_id is required for this change")
        if self.kind in (ChangeKind.ADD, ChangeKind.CHANGE_DAY) and not self.day:
            raise ValueError("day is required for this change")
        if self.kind in (ChangeKind.MOVE, ChangeKind.CHANGE_DAY) and not self.target_day:
            raise ValueError("target_day is required for this change")
        return self


class ChangeSet(BaseModel):
    changes: list[ChangeRequest] = Field(min_length=1, max_length=10)


class ReplanIn(BaseModel):
    request_text: str = Field(min_length=1, max_length=1000)
    change: ChangeRequest | None = None


class ReplanDiff(BaseModel):
    affected_days: list[int]
    added: list[str] = []
    removed: list[str] = []
    visited: list[str] = []
    moved: list[str] = []
    reason: str


class ReplanOut(BaseModel):
    itinerary_id: str
    version: int
    plan: dict
    diff: ReplanDiff
    trace: list[dict]


class VersionSummary(BaseModel):
    id: int
    version: int
    reason: str | None
    created_at: object


class WeatherSuggestion(BaseModel):
    day: int
    stop_id: str
    stop_name: str
    message: str
    suggested_place_id: str | None = None
    suggested_place_name: str | None = None
