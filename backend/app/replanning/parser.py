from __future__ import annotations

import re

from .contracts import ChangeKind, ChangeRequest


def parse_change(text: str) -> ChangeRequest:
    value = text.strip().lower()
    day = _day(value, r"(?:day|on)\s*(\d+)")
    target = _day(value, r"(?:to|into)\s*day\s*(\d+)")
    place = _place(value)

    if "start later" in value or "later start" in value:
        return ChangeRequest(kind=ChangeKind.START_LATER, day=day, minutes=_minutes(value))
    if "change day" in value or "another day" in value:
        return ChangeRequest(kind=ChangeKind.CHANGE_DAY, place_id=place, day=day, target_day=target)
    if any(word in value for word in ("remove", "delete", "skip")):
        return ChangeRequest(kind=ChangeKind.REMOVE, place_id=place, day=day)
    if any(word in value for word in ("move", "shift")) and target:
        return ChangeRequest(kind=ChangeKind.MOVE, place_id=place, day=day, target_day=target)
    if any(word in value for word in ("add", "include", "visit")):
        return ChangeRequest(kind=ChangeKind.ADD, place_id=place, day=day or 1)
    raise ValueError("I could not identify an add, remove, move, start-later, or change-day request.")


def _day(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _minutes(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:minutes?|mins?|hours?)", text)
    if not match:
        return 60
    amount = int(match.group(1))
    return amount * 60 if "hour" in match.group(0) else amount


def _place(text: str) -> str | None:
    match = re.search(r"(?:place|stop|at|visit)\s+([a-z0-9_-]+)", text)
    return match.group(1) if match else None
