"""Cost rules: foreign fees, jeep days, mountain travel and the road trip to the city."""

import datetime as dt

import pytest

from app.agents import costs
from app.agents.budget import jeep_days, trip_totals
from app.services import distances, geo

CITY = {
    "id": "hunza",
    "hotel_budget": 3000,
    "hotel_mid": 15500,
    "meal_pp_day": 1000,
    "transport_per_km": 150,
    "jeep_per_day": 15000,
    "speed_kmh": 20.0,
    "road_factor": 1.6,
}


def stop(pid, local, foreign=0, access="", leg_cost=0):
    return {
        "kind": "stop",
        "id": pid,
        "cost_pp": local,
        "cost_foreign": foreign or local,
        "access": access,
        "leg": {"km": 3, "minutes": 10, "cost": leg_cost} if leg_cost else None,
    }


def prefs(**kw):
    base = {
        "city": CITY,
        "city_id": "hunza",
        "size": 2,
        "days": 2,
        "budget": 200_000,
        "needs": set(),
        "traveller_type": "local",
        "home_city": None,
        "travel_mode": "bus",
    }
    return {**base, **kw}


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setattr(
        distances, "_table", lambda: {("lahore", "hunza"): (900.0, 18.0), ("hunza", "lahore"): (900.0, 18.0)}
    )


def test_foreign_visitors_pay_the_foreign_fee():
    fort = stop("baltit", 600, 1600)
    assert costs.entry_pp(fort) == 600
    assert costs.entry_pp(fort, "foreign") == 1600
    assert costs.entry_pp(stop("free", 0), "foreign") == 0


def test_jeep_hire_per_day_and_per_five_people():
    assert costs.jeeps(5) == 1 and costs.jeeps(6) == 2
    assert costs.jeep_cost(CITY, jeep_days=2, size=6) == 15000 * 2 * 2
    assert costs.jeep_cost({"jeep_per_day": 0}, 3, 4) == 0


def test_jeep_days_replace_taxi_fares():
    days = [
        {"day": 1, "items": [stop("a", 100, leg_cost=0), stop("b", 100, leg_cost=900)]},
        {"day": 2, "items": [stop("deosai", 500, access="jeep"), stop("c", 0, leg_cost=2000)]},
    ]
    assert jeep_days(days) == {2}
    t = trip_totals(days, prefs(), "budget")
    assert t["transport"] == 900  # day 2 driving is inside the jeep hire
    assert t["jeep"] == 15000 and t["jeep_days"] == 1
    assert t["entries"] == (100 + 100 + 500 + 0) * 2
    assert t["total"] == t["entries"] + t["transport"] + t["jeep"] + t["meals"] + t["stay"]


def test_foreign_totals_use_foreign_fees():
    days = [{"day": 1, "items": [stop("fort", 600, 1600)]}]
    local = trip_totals(days, prefs(), "budget")
    foreign = trip_totals(days, prefs(traveller_type="foreign"), "budget")
    assert foreign["entries"] - local["entries"] == (1600 - 600) * 2
    assert foreign["traveller_type"] == "foreign"


def test_road_trip_by_bus_or_car(table):
    assert costs.travel_to_city(None, "hunza", 2) == 0
    assert costs.travel_to_city("hunza", "hunza", 2) == 0
    assert costs.travel_to_city("lahore", "hunza", 2, "bus") == 2 * 900 * costs.BUS_PKR_PER_KM * 2
    car = costs.travel_to_city("lahore", "hunza", 2, "car")
    assert car == round(2 * 900 * costs.PETROL_PKR_PER_LITRE / costs.CAR_KM_PER_LITRE, -2)
    # One car for up to four people, so a family of four pays the same fuel as a couple.
    assert costs.travel_to_city("lahore", "hunza", 4, "car") == car
    assert costs.travel_to_city("karachi", "hunza", 2) == 0  # no distance known


def test_road_trip_is_in_totals_and_minimum(table):
    days = [{"day": 1, "items": [stop("a", 0)]}]
    t = trip_totals(days, prefs(home_city="lahore"), "budget")
    assert t["travel_to_city"] == 36000 and t["home_city"] == "lahore"
    assert t["total"] == t["meals"] + t["stay"] + 36000
    assert costs.minimum_trip_cost(CITY, 2, 2, home_id="lahore") - costs.minimum_trip_cost(CITY, 2, 2) == 36000


def test_mountain_legs_are_slower_and_longer():
    a, b = {"lat": 36.30, "lon": 74.60}, {"lat": 36.35, "lon": 74.65}
    city = geo.leg(a, b, 100)
    mountain = geo.leg(a, b, 100, speed_kmh=20, road_factor=1.6)
    assert mountain["km"] > city["km"]
    assert mountain["minutes"] > city["minutes"]


def test_distances_file_is_symmetric():
    table = distances._table()
    if not table:
        pytest.skip("road_distances.csv not generated")
    for (a, b), (km, _) in table.items():
        assert distances.road_km(b, a) == km
        assert km > 0
    assert distances.road_km("lahore", "lahore") == 0


def test_plan_with_jeep_place_marks_legs(catalog):
    """End to end: a Skardu plan that visits a jeep-only place shows jeep legs and jeep hire."""
    from app.agents.orchestrator import Orchestrator
    from app.schemas.preferences import TripPreferences

    jeep_places = [p for p in catalog.pois("skardu") if p["access"] == "jeep"]
    if not jeep_places:
        pytest.skip("no jeep-only place in the catalog")
    prefs_ = TripPreferences(
        city="skardu",
        start_date=dt.date.today() + dt.timedelta(days=40),
        days=3,
        budget=400_000,
        group_type="couple",
        interests=["nature", "adventure"],
        interests_answered=True,
    )
    result = Orchestrator().run(prefs_, catalog)
    for plan in result["plans"]:
        t = plan["plan"]["totals"]
        for day in plan["plan"]["days"]:
            if day.get("jeep"):
                legs = [s["leg"] for s in day["items"] if s["kind"] == "stop" and s.get("leg")]
                assert all(leg["mode"] == "jeep" and leg["cost"] == 0 for leg in legs)
        assert t["jeep"] == costs.jeep_cost(catalog.cities["skardu"], t["jeep_days"], 2)
