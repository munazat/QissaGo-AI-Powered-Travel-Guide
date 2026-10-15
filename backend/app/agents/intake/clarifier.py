"""Clarification handler: finds missing or contradictory details and asks ONE clear question,
with quick-reply suggestions the app shows as tappable chips."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.agents import costs
from app.schemas.preferences import TripPreferences
from app.services.catalog import Catalog


@dataclass
class Question:
    field: str
    text: str
    suggestions: list[str] = field(default_factory=list)


def money(v: int) -> str:
    return f"Rs {v:,}"


def ask(field_name: str, prefs: TripPreferences, cat: Catalog) -> Question:
    if field_name == "city":
        names = [c["name"] for c in cat.cities.values()]
        return Question("city", "Which city would you like to visit?", names)
    if field_name == "days":
        return Question("days", "How many days is the trip?", ["1 day", "2 days", "3 days", "4 days", "5 days"])
    if field_name == "start_date":
        return Question("start_date", "When does the trip start?", ["Tomorrow", "This weekend", "Next week"])
    if field_name == "group_type":
        return Question("group_type", "Who is travelling?", ["Solo", "Couple", "Family", "Friends"])
    if field_name == "group_size":
        return Question("group_size", "How many people in total?", ["3 people", "4 people", "5 people", "6 people"])
    if field_name == "budget":
        sug = []
        if prefs.city in cat.cities and prefs.days:
            low = costs.round_up(
                costs.minimum_trip_cost(
                    cat.cities[prefs.city],
                    prefs.days,
                    prefs.size(),
                    "no_stay" in prefs.needs,
                    prefs.home_city,
                    prefs.travel_mode,
                )
            )
            sug = [money(low), money(costs.round_up(int(low * 1.6))), money(costs.round_up(low * 3))]
        return Question("budget", "What is your total budget in rupees?", sug)
    if field_name == "interests":
        labels = [i["label"] for i in cat.interests.values()]
        return Question("interests", "What would you like to see? Pick a few, or say anything.", labels + ["Anything"])
    if field_name == "pace":
        return Question("pace", "What pace do you prefer?", ["Relaxed", "Balanced", "Packed"])
    return Question("", "Anything else?", [])


def check_conflicts(prefs: TripPreferences, cat: Catalog, today: dt.date) -> Question | None:
    """Contradictions are fixed before anything else. The bad value is cleared."""
    if prefs.start_date and prefs.start_date < today:
        prefs.start_date = None
        q = ask("start_date", prefs, cat)
        q.text = "That date has already passed. " + q.text
        return q
    expected = {"solo": 1, "couple": 2}.get(prefs.group_type or "")
    if expected and prefs.group_size and prefs.group_size != expected:
        prefs.group_type = None
        q = ask("group_type", prefs, cat)
        q.text = f"You mentioned {prefs.group_size} people. " + q.text
        return q
    if prefs.budget is not None and prefs.city in cat.cities and prefs.days:
        floor = costs.minimum_trip_cost(
            cat.cities[prefs.city],
            prefs.days,
            prefs.size(),
            "no_stay" in prefs.needs,
            prefs.home_city,
            prefs.travel_mode,
        )
        if prefs.budget < floor:
            low = costs.round_up(floor)
            prefs.budget = None
            return Question(
                "budget",
                f"For {prefs.size()} {'person' if prefs.size() == 1 else 'people'} over {prefs.days} "
                f"{'day' if prefs.days == 1 else 'days'} in {cat.cities[prefs.city]['name']}, "
                f"the minimum is about {money(low)}. What budget should I use?",
                [money(low), money(costs.round_up(int(low * 1.5))), "Fewer days"],
            )
    return None


def next_question(prefs: TripPreferences, cat: Catalog, today: dt.date) -> Question | None:
    conflict = check_conflicts(prefs, cat, today)
    if conflict:
        return conflict
    missing = prefs.missing()
    if missing:
        return ask(missing[0], prefs, cat)
    if not prefs.interests_answered:
        return ask("interests", prefs, cat)
    return None


def summary(prefs: TripPreferences, cat: Catalog) -> str:
    city = cat.cities[prefs.city]["name"]
    n = prefs.size()
    parts = [
        f"{city}, {prefs.days} {'day' if prefs.days == 1 else 'days'} from {prefs.start_date:%a %d %b}",
        f"{n} {'person' if n == 1 else 'people'}",
        money(prefs.budget),
    ]
    if prefs.interests:
        parts.append(", ".join(cat.interests[i]["label"].lower() for i in prefs.interests if i in cat.interests))
    parts.append(f"{prefs.pace} pace")
    return "; ".join(parts) + "."
