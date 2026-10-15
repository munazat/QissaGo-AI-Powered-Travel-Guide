"""Destination agent: scores every place in the city three different ways (one per plan option)."""

from __future__ import annotations

from . import costs
from .base import Agent

VARIANTS = [
    {
        "id": "balanced",
        "title": "Balanced Explorer",
        "label": "Balanced",
        "w_interest": 0.50,
        "w_priority": 0.30,
        "w_cost": 0.20,
        "hotel": "mid",
    },
    {
        "id": "deepdive",
        "title": "Interest Deep-Dive",
        "label": "Your interests",
        "w_interest": 0.75,
        "w_priority": 0.20,
        "w_cost": 0.05,
        "hotel": "mid",
    },
    {
        "id": "saver",
        "title": "Smart Saver",
        "label": "Lowest cost",
        "w_interest": 0.35,
        "w_priority": 0.20,
        "w_cost": 0.45,
        "hotel": "budget",
    },
]

# When a user says "no shopping", places that ARE shopping places are removed entirely.
CATEGORY_INTEREST = {
    "mall": "shopping",
    "market": "shopping",
    "mosque": "spiritual",
    "shrine": "spiritual",
    "church": "spiritual",
    "food street": "food",
    "dining street": "food",
    "park": "nature",
    "garden": "nature",
    "beach": "nature",
    "lake": "nature",
    "viewpoint": "nature",
    "zoo": "family",
    "safari park": "family",
    "amusement park": "family",
    "hiking trail": "adventure",
    "caves": "adventure",
    "island": "adventure",
    "museum": "history",
    "tomb": "history",
    "tombs": "history",
    "monument": "history",
    "arts centre": "art",
    "fort": "history",
    "palace": "history",
    "heritage site": "history",
    "national park": "nature",
    "waterfall": "nature",
    "glacier": "adventure",
    "valley": "nature",
    "adventure": "adventure",
}


def interest_match(poi: dict, interests: list[str]) -> float:
    if not interests:
        return 0.5
    hits = len(set(poi["tags"]) & set(interests))
    return min(1.0, hits / min(len(interests), 2))


def allowed(poi: dict, prefs: dict) -> bool:
    if poi["id"] in prefs["excluded_places"]:
        return False
    if CATEGORY_INTEREST.get(poi["category"]) in prefs["exclusions"]:
        return False
    return True


def score(poi: dict, v: dict, prefs: dict, wet_trip: bool, hot_trip: bool) -> float:
    s = (
        v["w_interest"] * interest_match(poi, prefs["interests"])
        + v["w_priority"] * (poi["priority"] - 1) / 2
        + v["w_cost"] * (1 - min(costs.entry_pp(poi, prefs.get("traveller_type", "local")), 3000) / 3000)
    )
    needs = prefs["needs"]
    if set(poi["tags"]) & set(prefs["exclusions"]):
        s *= 0.4
    if "kids" in needs and "family" in poi["tags"]:
        s += 0.15
    if "elderly" in needs and "adventure" in poi["tags"]:
        s *= 0.5
    if "indoor" in needs and poi["outdoor"]:
        s *= 0.8
    if wet_trip and poi["outdoor"]:
        s *= 0.85
    if hot_trip and poi["outdoor"] and poi["best_time"] == "midday":
        s *= 0.9
    return round(s, 4)


class DestinationAgent(Agent):
    name = "Destination Agent"
    role = "Ranks the places that match your interests"

    def run(self, state: dict) -> str:
        p = state["prefs"]
        pool = [poi for poi in state["catalog"].pois(p["city_id"]) if allowed(poi, p)]
        if not pool:
            raise ValueError("No places left after your exclusions")
        days = state["weather"]["days"]
        wet = sum(d["rainy"] for d in days) > len(days) / 2
        hot = sum(d["hot"] for d in days) > len(days) / 2
        state["ranked"] = {}
        for v in VARIANTS:
            scored = [{**poi, "score": score(poi, v, p, wet, hot)} for poi in pool]
            scored.sort(key=lambda x: -x["score"])
            state["ranked"][v["id"]] = scored
        removed = len(state["catalog"].pois(p["city_id"])) - len(pool)
        extra = f", {removed} excluded" if removed else ""
        return f"Scored {len(pool)} places three ways{extra}."
