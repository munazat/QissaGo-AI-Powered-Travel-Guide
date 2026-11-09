from __future__ import annotations

import re

from .contracts import ChangeKind, ChangeRequest

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "first": 1, "second": 2, "third": 3}
_ACTION_WORDS = r"add|include|visit|find|recommend|remove|delete|skip|visited|move|shift|relocate|start"


def parse_change(text: str) -> ChangeRequest:
    changes = parse_changes(text)
    if len(changes) != 1:
        raise ValueError("This request contains multiple changes. Use parse_changes instead.")
    return changes[0]


def parse_changes(text: str) -> list[ChangeRequest]:
    value = _normalise(text)
    if not value:
        raise ValueError("Please describe what should change.")
    parts = [part.strip() for part in re.split(r"\s*(?:;|\band then\b|\bthen\b)\s*", value) if part.strip()]
    changes: list[ChangeRequest] = []
    for part in parts:
        changes.extend(_parse_part(part))
    if not changes:
        raise ValueError("I could not identify a change. Try saying what to add, remove, move, or when to start.")
    return changes


def _parse_part(value: str) -> list[ChangeRequest]:
    day = _day(value, r"\b(?:day|on)\s*(\d+)\b")
    target = _day(value, r"\b(?:to|into|for)\s*day\s*(\d+)\b")
    context = _context(value)
    has_action = re.search(
        r"\b(?:add|include|visit|find|recommend|replace|remove|delete|skip|move|shift|relocate|start|visited)\b",
        value,
    )
    if context and not has_action:
        return [ChangeRequest(kind=ChangeKind.UPDATE_CONTEXT, day=day, context=context)]
    chunks = [chunk.strip() for chunk in re.split(r"\s*,\s*(?=[a-z])|\s+\band\b\s+", value) if chunk.strip()]
    if len(chunks) > 1:
        return [change for chunk in chunks for change in _parse_part(chunk)]
    if re.search(r"\b(?:budget|money|funds|cash|left)\b", value) and re.search(
        r"\b(?:have|remaining|reduce|lower|increase|raise|set)\b", value
    ):
        amount = _budget_amount(value)
        if amount is None:
            raise ValueError("How much budget do you have left?")
        return [ChangeRequest(kind=ChangeKind.UPDATE_BUDGET, budget_amount=amount)]
    if "start later" in value or "later start" in value or "delay" in value or "start at" in value:
        return [ChangeRequest(kind=ChangeKind.START_LATER, day=day or 1, minutes=_minutes(value))]
    if re.search(r"\b(?:move|shift|relocate|change)\b", value):
        place = _place(value)
        if not target:
            raise ValueError("Which day should I move that stop to?")
        return [ChangeRequest(kind=ChangeKind.MOVE, place_id=place, day=day, target_day=target)]
    if re.search(r"\b(?:already visited|visited)\b", value):
        ordinals = _ordinals(value)
        if ordinals:
            return [ChangeRequest(kind=ChangeKind.MARK_VISITED, place_id=ordinal, day=day) for ordinal in ordinals]
        place = _place(value)
        if not place:
            raise ValueError("Which stop should I mark as visited?")
        return [ChangeRequest(kind=ChangeKind.MARK_VISITED, place_id=place, day=day)]
    if re.search(r"\b(?:remove|delete|skip)\b", value):
        place = _place(value)
        if not place:
            raise ValueError("Which stop should I remove?")
        return [ChangeRequest(kind=ChangeKind.REMOVE, place_id=place, day=day)]
    if re.search(r"\b(?:add|include|visit|find|recommend|replace)\b", value):
        place = _topic(value) or _place(value)
        if not place:
            raise ValueError("What place or type of place should I add?")
        return [ChangeRequest(kind=ChangeKind.ADD, place_id=place, day=day or 1, context=context)]
    raise ValueError("I could not identify a change. Try saying what to add, remove, move, or when to start.")


def _context(text: str) -> dict[str, str | int | float | bool]:
    context: dict[str, str | int | float | bool] = {}
    if re.search(r"\b(?:rain|raining|rainy|storm|wet)\b", text):
        context["weather"] = "rainy"
    elif re.search(r"\b(?:sunny|clear|hot|heat)\b", text):
        context["weather"] = "clear"
    if re.search(r"\b(?:tired|exhausted|fatigued|low energy|need a break)\b", text):
        context["fatigue"] = "high"
    if re.search(r"\b(?:wheelchair|wheel chair|accessible|accessibility|avoid stairs)\b", text):
        context["accessibility"] = "step_free"
    if re.search(r"\b(?:nearby|near me|close by|close to me)\b", text):
        context["max_distance_km"] = 3.0
    distance = re.search(r"\b(?:within|under|less than)\s+(\d+(?:\.\d+)?)\s*km\b", text)
    if distance:
        context["max_distance_km"] = float(distance.group(1))
    time_match = re.search(r"\b(?:current time is|it is|it's|at)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        if time_match.group(3) == "pm" and hour < 12:
            hour += 12
        if time_match.group(3) == "am" and hour == 12:
            hour = 0
        context["current_time"] = f"{hour:02d}:{minute:02d}"
    elif re.search(r"\b(?:running late|behind schedule|we are late)\b", text):
        context["time_status"] = "late"
    return context


def _day(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _minutes(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:minutes?|mins?|hours?|hrs?)", text)
    if not match:
        return 60
    amount = int(match.group(1))
    return amount * 60 if "hour" in match.group(0) else amount


def _budget_amount(text: str) -> int | None:
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakh|lac)?", text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    multiplier = {"k": 1_000, "thousand": 1_000, "lakh": 100_000, "lac": 100_000}.get(match.group(2), 1)
    return round(amount * multiplier)


def _ordinals(text: str) -> list[str]:
    match = re.search(r"\b(first|second|third)\s+(two|three)\b|\b(first|second|third)\b", text)
    if not match:
        return []
    start = match.group(1) or match.group(3)
    count = int({"two": 2, "three": 3}.get(match.group(2), 1))
    names = ["first", "second", "third"]
    start_index = names.index(start)
    return names[start_index : start_index + count]


def _place(text: str) -> str | None:
    match = re.search(
        r"\b(?:add|include|visit|visited|find|recommend|replace|remove|delete|skip|move|shift|relocate)\b\s+"
        r"(?:(?:the|a|an)\s+)?(?:(?:place|stop)\s+)?([a-z0-9_-]+)",
        text,
    )
    return match.group(1) if match else None


def _topic(text: str) -> str | None:
    for topic in ("cultural", "culture", "historical", "history", "museum", "indoor", "nature", "food", "shopping"):
        if topic in text:
            return topic
    return None


def _normalise(text: str) -> str:
    value = re.sub(r"[^\w\s,;.-]", " ", text.lower())
    value = re.sub(r"\s+", " ", value).strip()
    return value
