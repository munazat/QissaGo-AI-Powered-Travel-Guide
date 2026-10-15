"""Intake agent (planning side): turns confirmed TripPreferences into the plan settings
every other agent uses. The chat side of intake lives in conversation.py."""

from __future__ import annotations

from app.agents.base import Agent
from app.schemas.preferences import TripPreferences

PACE = {
    "relaxed": {"stops": 3, "start": "10:00"},
    "balanced": {"stops": 4, "start": "09:00"},
    "packed": {"stops": 5, "start": "08:30"},
}


class IntakeAgent(Agent):
    name = "Intake Agent"
    role = "Checks the trip details and sets the daily rhythm"

    def run(self, state: dict) -> str:
        prefs: TripPreferences = state["request"]
        cat = state["catalog"]
        missing = prefs.missing()
        if missing:
            raise ValueError(f"Missing trip details: {', '.join(missing)}")
        if prefs.city not in cat.cities:
            raise ValueError(f"Unknown city '{prefs.city}'")
        pace = PACE[prefs.pace]
        stops = pace["stops"]
        start = pace["start"]
        if "elderly" in prefs.needs or "kids" in prefs.needs:
            stops = min(stops, 3)
        if "late_start" in prefs.needs:
            start = "11:00"
        valid = set(cat.interests)
        state["prefs"] = {
            "city": cat.cities[prefs.city],
            "city_id": prefs.city,
            "days": prefs.days,
            "start_date": prefs.start_date,
            "budget": prefs.budget,
            "group_type": prefs.group_type,
            "size": prefs.size(),
            "interests": [i for i in prefs.interests if i in valid],
            "exclusions": [i for i in prefs.exclusions if i in valid],
            "excluded_places": set(prefs.excluded_places),
            "pace": prefs.pace,
            "stops_per_day": stops,
            "day_start": start,
            "needs": set(prefs.needs),
            "traveller_type": prefs.traveller_type,
            "home_city": prefs.home_city if prefs.home_city in cat.cities and prefs.home_city != prefs.city else None,
            "travel_mode": prefs.travel_mode,
        }
        p = state["prefs"]
        return (
            f"{p['city']['name']}, {p['days']} days, {p['size']} travellers, Rs {p['budget']:,}, "
            f"{p['pace']} pace ({stops} stops a day from {start})."
        )
