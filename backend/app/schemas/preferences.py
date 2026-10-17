"""Trip preferences: the one object filled by the chatbot AND by the quick-select buttons."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

GroupType = Literal["solo", "couple", "family", "friends"]
Pace = Literal["relaxed", "balanced", "packed"]
Need = Literal["kids", "elderly", "indoor", "late_start", "no_stay"]
TravellerType = Literal["local", "foreign"]
TravelMode = Literal["bus", "car"]

DEFAULT_GROUP_SIZE = {"solo": 1, "couple": 2, "family": 4, "friends": 4}
MAX_DAYS = 7

# Required before plans can be made, in the order the chatbot asks for them.
REQUIRED_FIELDS = ["city", "days", "start_date", "group_type", "budget"]


class TripPreferences(BaseModel):
    """Everything is optional while chatting; the clarification handler asks for what's missing."""

    city: str | None = None
    start_date: dt.date | None = None
    days: int | None = Field(default=None, ge=1, le=MAX_DAYS)
    budget: int | None = Field(default=None, ge=0)  # total PKR for the whole group
    group_type: GroupType | None = None
    group_size: int | None = Field(default=None, ge=1, le=30)
    interests: list[str] = []
    interests_answered: bool = False  # true once the user picked interests or said "anything"
    exclusions: list[str] = []  # interest ids the user does not want
    excluded_places: list[str] = []  # place ids the user does not want
    pace: Pace = "balanced"
    needs: list[Need] = []
    traveller_type: TravellerType = "local"  # foreign visitors pay foreign entry fees
    home_city: str | None = None  # optional: add the road trip from this city
    travel_mode: TravelMode = "bus"

    def missing(self) -> list[str]:
        out = []
        for f in REQUIRED_FIELDS:
            if f == "budget" and self.group_type in ("family", "friends") and not self.group_size:
                out.append("group_size")  # ask "how many people" before the budget
            if getattr(self, f) is None:
                out.append(f)
        return out

    def size(self) -> int:
        if self.group_size:
            return self.group_size
        return DEFAULT_GROUP_SIZE.get(self.group_type or "", 1)


class PreferencesPatch(BaseModel):
    """What a button tap sends: only the fields that changed."""

    city: str | None = None
    start_date: dt.date | None = None
    days: int | None = Field(default=None, ge=1, le=MAX_DAYS)
    budget: int | None = Field(default=None, ge=0)
    group_type: GroupType | None = None
    group_size: int | None = Field(default=None, ge=1, le=30)
    interests: list[str] | None = None
    exclusions: list[str] | None = None
    pace: Pace | None = None
    needs: list[Need] | None = None
    traveller_type: TravellerType | None = None
    home_city: str | None = None
    travel_mode: TravelMode | None = None
