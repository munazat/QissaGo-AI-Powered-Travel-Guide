from __future__ import annotations

from app.replanning.contracts import ChangeKind, ChangeRequest
from app.replanning.parser import parse_change
from app.replanning.service import apply_change
from app.services.catalog import Catalog


def _catalog() -> Catalog:
    return Catalog(
        cities={
            "lahore": {
                "id": "lahore",
                "transport_per_km": 10,
                "speed_kmh": 24,
                "road_factor": 1.35,
            }
        },
        pois_by_city={
            "lahore": [
                {
                    "id": "lhr_museum",
                    "name": "Museum",
                    "category": "museum",
                    "tags": ["history"],
                    "lat": 31.52,
                    "lon": 74.34,
                    "minutes": 60,
                    "open": "09:00",
                    "close": "18:00",
                    "best_time": "morning",
                    "outdoor": False,
                    "priority": 2,
                }
            ]
        },
    )


def _stop(stop_id: str, name: str) -> dict:
    return {
        "kind": "stop",
        "id": stop_id,
        "name": name,
        "lat": 31.52,
        "lon": 74.34,
        "minutes": 60,
        "open": "09:00",
        "close": "18:00",
        "best_time": "morning",
        "outdoor": False,
        "tags": ["history"],
        "priority": 2,
    }


def _plan() -> dict:
    return {
        "days": [
            {
                "day": 1,
                "date": "2026-11-10",
                "items": [_stop("lhr_fort", "Fort")],
                "weather": {"hot": False, "rainy": False, "rain_pct": 0},
            },
            {
                "day": 2,
                "date": "2026-11-11",
                "items": [_stop("lhr_bazaar", "Bazaar")],
                "weather": {"hot": False, "rainy": False, "rain_pct": 0},
            },
        ]
    }


def test_parser_supports_change_types():
    assert parse_change("remove stop lhr_fort on day 1").kind == ChangeKind.REMOVE
    assert parse_change("start later by 90 minutes on day 2").minutes == 90


def test_remove_rebuilds_only_affected_day():
    plan = _plan()
    updated, diff = apply_change(
        plan,
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        ChangeRequest(kind=ChangeKind.REMOVE, place_id="lhr_fort", day=1),
        _catalog(),
    )
    assert diff.affected_days == [1]
    assert updated["days"][0]["items"] == []
    assert updated["days"][1] == plan["days"][1]


def test_add_rebuilds_requested_day():
    updated, diff = apply_change(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        ChangeRequest(kind=ChangeKind.ADD, place_id="lhr_museum", day=1),
        _catalog(),
    )
    assert diff.added == ["Museum"]
    assert updated["days"][0]["items"][0]["id"] == "lhr_fort"
    assert updated["days"][0]["items"][1]["id"] == "lhr_museum"
