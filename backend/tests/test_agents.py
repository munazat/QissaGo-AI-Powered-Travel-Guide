"""Itinerary agents: every plan must be valid for many different trips."""

import datetime as dt

import pytest

from app.agents.base import hm_to_min
from app.agents.orchestrator import Orchestrator
from app.schemas.preferences import TripPreferences

START = dt.date.today() + dt.timedelta(days=40)

TRIPS = [
    dict(city="lahore", days=3, budget=90_000, group_type="family", group_size=4, interests=["history", "food"]),
    dict(city="karachi", days=2, budget=25_000, group_type="couple", group_size=2, pace="relaxed"),
    dict(
        city="islamabad",
        days=4,
        budget=300_000,
        group_type="friends",
        group_size=5,
        interests=["adventure", "nature"],
        pace="packed",
    ),
    dict(city="lahore", days=1, budget=15_000, group_type="solo", group_size=1, needs=["no_stay"]),
    dict(city="karachi", days=5, budget=200_000, group_type="family", group_size=6, needs=["kids", "elderly"]),
    dict(
        city="hunza",
        days=3,
        budget=400_000,
        group_type="couple",
        group_size=2,
        interests=["nature", "history"],
        traveller_type="foreign",
        home_city="lahore",
        travel_mode="car",
    ),
    dict(city="kalam", days=2, budget=250_000, group_type="friends", group_size=5, interests=["nature"]),
    dict(city="bahawalpur", days=2, budget=120_000, group_type="family", group_size=4, interests=["history"]),
]


def run(catalog, **kw):
    prefs = TripPreferences(start_date=START, interests_answered=True, **kw)
    return prefs, Orchestrator().run(prefs, catalog)


def stops(plan):
    return [s for d in plan["plan"]["days"] for s in d["items"] if s["kind"] == "stop"]


@pytest.mark.parametrize("trip", TRIPS)
def test_three_valid_plans(catalog, trip):
    prefs, result = run(catalog, **trip)
    assert len(result["plans"]) == 3
    assert {p["variant"] for p in result["plans"]} == {"balanced", "deepdive", "saver"}
    assert result["plans"][0]["label"] == "Best match"
    scores = [p["match_score"] for p in result["plans"]]
    assert scores == sorted(scores, reverse=True) and all(0 <= s <= 100 for s in scores)
    for plan in result["plans"]:
        days = plan["plan"]["days"]
        assert len(days) == prefs.days
        assert plan["plan"]["totals"]["total"] <= prefs.budget
        for day in days:
            last_end = 0
            n = 0
            for item in day["items"]:
                start, end = hm_to_min(item["start"]), hm_to_min(item["end"])
                assert start >= last_end, f"overlap in {plan['title']} day {day['day']}"
                last_end = end
                if item["kind"] == "stop":
                    n += 1
                    assert hm_to_min(item["open"]) <= start and end <= hm_to_min(item["close"])
                    assert item["city_id"] == prefs.city
                    assert "map_url" in item and "cost_group" in item
            assert n <= {"relaxed": 3, "balanced": 4, "packed": 5}[prefs.pace]
        ids = [s["id"] for s in stops(plan)]
        assert len(ids) == len(set(ids)), "a place appears twice"


def test_trace_has_every_agent(catalog):
    _, result = run(catalog, **TRIPS[0])
    names = [t["agent"] for t in result["trace"]]
    assert names == [
        "Intake Agent",
        "Weather Agent",
        "Destination Agent",
        "Budget Agent",
        "Scheduling Agent",
        "Validator Agent",
        "Enrichment Agent",
        "Orchestrator Agent",
    ]


def test_exclusions_are_respected(catalog):
    _, result = run(catalog, **{**TRIPS[0], "exclusions": ["shopping"], "excluded_places": ["lhr_fort"]})
    for plan in result["plans"]:
        for s in stops(plan):
            assert s["id"] != "lhr_fort"
            assert s["category"] not in ("mall", "market")


def test_interest_plan_matches_interests(catalog):
    _, result = run(catalog, **TRIPS[2])
    deep = next(p for p in result["plans"] if p["variant"] == "deepdive")
    matching = [s for s in stops(deep) if {"adventure", "nature"} & set(s["tags"])]
    assert len(matching) / len(stops(deep)) >= 0.6


def test_saver_is_cheapest_or_close(catalog):
    _, result = run(catalog, **TRIPS[2])
    by = {p["variant"]: p["plan"]["totals"]["total"] for p in result["plans"]}
    assert by["saver"] <= min(by["balanced"], by["deepdive"])


def test_late_start(catalog):
    _, result = run(catalog, **{**TRIPS[1], "needs": ["late_start"]})
    for plan in result["plans"]:
        for s in stops(plan):
            assert hm_to_min(s["start"]) >= 11 * 60


def test_missing_details_rejected(catalog):
    with pytest.raises(ValueError):
        Orchestrator().run(TripPreferences(city="lahore"), catalog)


def test_mountain_city_plan_is_slower_and_foreign_fees_apply(catalog):
    hunza = catalog.cities["hunza"]
    assert hunza["speed_kmh"] < catalog.cities["lahore"]["speed_kmh"] or hunza["road_factor"] > 1.35
    prefs, result = run(catalog, **TRIPS[5])
    for plan in result["plans"]:
        t = plan["plan"]["totals"]
        assert t["traveller_type"] == "foreign" and t["home_city"] == "lahore" and t["travel_mode"] == "car"
        for s in stops(plan):
            assert s["cost_group"] == (s["cost_foreign"] or s["cost_pp"]) * prefs.size()
