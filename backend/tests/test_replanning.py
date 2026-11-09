from __future__ import annotations

import pytest

from app.db.models import Itinerary
from app.db.session import SessionLocal
from app.replanning.contracts import ChangeKind, ChangeRequest
from app.replanning.parser import parse_change, parse_changes
from app.replanning.service import apply_change, apply_changes
from app.services.catalog import Catalog, load_catalog


def _generated_itinerary(client, auth) -> dict:
    response = client.post(
        "/api/v1/itineraries/generate",
        headers=auth,
        json={
            "preferences": {
                "city": "lahore",
                "start_date": "2099-01-10",
                "days": 2,
                "budget": 500000,
                "group_type": "solo",
                "group_size": 1,
                "interests": ["history"],
            }
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["itineraries"][0]


def _first_stop(plan: dict) -> dict:
    return next(item for day in plan["days"] for item in day["items"] if item.get("kind") == "stop")


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


def test_move_rebuilds_source_and_target_days():
    updated, diff = apply_change(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        ChangeRequest(kind=ChangeKind.MOVE, place_id="lhr_fort", day=1, target_day=2),
        _catalog(),
    )

    assert diff.affected_days == [1, 2]
    assert diff.moved == ["Fort"]
    assert updated["days"][0]["items"] == []
    assert [item["id"] for item in updated["days"][1]["items"]] == ["lhr_bazaar", "lhr_fort"]


def test_start_later_rejects_schedule_past_day_limit():
    plan = _plan()
    plan["days"][0]["items"][0].update({"start": "20:30", "end": "21:30"})

    with pytest.raises(ValueError, match="allowed end time"):
        apply_change(
            plan,
            {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
            ChangeRequest(kind=ChangeKind.START_LATER, day=1, minutes=60),
            _catalog(),
        )


def test_add_rejects_duplicate_and_unknown_places():
    plan = _plan()
    prefs = {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"}
    catalog = _catalog()
    catalog.pois_by_city["lahore"].append(_stop("lhr_fort", "Fort"))

    with pytest.raises(ValueError, match="already in the itinerary"):
        apply_change(
            plan,
            prefs,
            ChangeRequest(kind=ChangeKind.ADD, place_id="lhr_fort", day=1),
            catalog,
        )

    with pytest.raises(ValueError, match="not available"):
        apply_change(
            plan,
            prefs,
            ChangeRequest(kind=ChangeKind.ADD, place_id="unknown", day=1),
            catalog,
        )


def test_parser_rejects_unsupported_request():
    with pytest.raises(ValueError, match="could not identify"):
        parse_change("make the trip more relaxing")


def test_parser_accepts_natural_aliases_and_multiple_changes():
    changes = parse_changes("remove the fort on day 1 and start later by 30 mins on day 1")

    assert [change.kind for change in changes] == [ChangeKind.REMOVE, ChangeKind.START_LATER]
    assert changes[0].place_id == "fort"
    assert changes[1].minutes == 30


def test_parser_marks_multiple_visited_stops():
    changes = parse_changes("I've already visited the first two places")

    assert [change.kind for change in changes] == [ChangeKind.MARK_VISITED, ChangeKind.MARK_VISITED]
    assert [change.place_id for change in changes] == ["first", "second"]


@pytest.mark.parametrize(
    ("text", "amount"),
    [
        ("I only have Rs 20,000 left", 20_000),
        ("Reduce the remaining budget to 25k", 25_000),
        ("I have 1.5 lakh left for the trip", 150_000),
    ],
)
def test_parser_accepts_budget_updates(text, amount):
    change = parse_change(text)

    assert change.kind == ChangeKind.UPDATE_BUDGET
    assert change.budget_amount == amount


def test_budget_update_is_persisted_in_execution_state():
    updated, diff = apply_changes(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        parse_changes("I only have Rs 20,000 left"),
        _catalog(),
    )

    assert diff.budget_amount == 20_000
    assert updated["execution"]["remaining_budget"] == 20_000


def test_budget_update_is_reflected_in_plan_totals(client, auth):
    itinerary = _generated_itinerary(client, auth)

    response = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan",
        headers=auth,
        json={"request_text": "I have Rs 20,000 left"},
    )

    assert response.status_code == 200, response.text
    totals = response.json()["plan"]["totals"]
    assert totals["budget"] == 20_000
    assert totals["remaining_budget"] == 20_000


def test_parser_extracts_combined_trip_context():
    change = parse_change("It is raining, I am tired, keep me somewhere nearby and avoid stairs on day 1")

    assert change.kind == ChangeKind.UPDATE_CONTEXT
    assert change.day == 1
    assert change.context == {
        "weather": "rainy",
        "fatigue": "high",
        "accessibility": "step_free",
        "max_distance_km": 3.0,
    }


def test_parser_keeps_context_with_a_place_request():
    change = parse_change("Find a nearby indoor place on day 2")

    assert change.kind == ChangeKind.ADD
    assert change.place_id == "indoor"
    assert change.day == 2
    assert change.context["max_distance_km"] == 3.0


def test_context_update_persists_and_changes_weather():
    updated, diff = apply_changes(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        parse_changes("It is raining on day 1"),
        _catalog(),
    )

    assert diff.context["weather"] == "rainy"
    assert updated["execution"]["context"]["weather"] == "rainy"
    assert updated["days"][0]["weather"]["rainy"] is True


def test_mark_visited_keeps_stop_and_locks_it():
    updated, diff = apply_changes(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        parse_changes("I've already visited the first place"),
        _catalog(),
    )

    assert diff.visited == ["Fort"]
    assert updated["execution"]["completed_stop_ids"] == ["lhr_fort"]
    assert updated["days"][0]["items"][0]["id"] == "lhr_fort"


def test_multiple_changes_can_use_a_catalog_topic():
    updated, diff = apply_changes(
        _plan(),
        {"city": "lahore", "city_id": "lahore", "size": 2, "day_start": "09:00"},
        parse_changes("remove the fort on day 1; add a cultural place on day 2"),
        _catalog(),
    )

    assert diff.removed == ["Fort"]
    assert diff.added == ["Museum"]
    assert updated["days"][0]["items"] == []
    assert updated["days"][1]["items"][0]["id"] == "lhr_bazaar"


def test_preview_does_not_persist_and_apply_creates_version(client, auth):
    itinerary = _generated_itinerary(client, auth)
    stop = _first_stop(itinerary["plan"])
    request = {"request_text": f"remove stop {stop['id']} on day 1"}

    preview = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan/preview",
        headers=auth,
        json=request,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["version"] == 0
    assert preview.json()["diff"]["removed"] == [stop["name"]]

    unchanged = client.get(f"/api/v1/itineraries/{itinerary['id']}", headers=auth)
    assert unchanged.status_code == 200
    assert _first_stop(unchanged.json()["plan"])["id"] == stop["id"]

    applied = client.post(f"/api/v1/itineraries/{itinerary['id']}/replan", headers=auth, json=request)
    assert applied.status_code == 200, applied.text
    assert applied.json()["version"] == 1
    assert all(item.get("id") != stop["id"] for day in applied.json()["plan"]["days"] for item in day["items"])

    versions = client.get(f"/api/v1/itineraries/{itinerary['id']}/versions", headers=auth)
    assert versions.status_code == 200
    assert [version["version"] for version in versions.json()] == [1]


def test_restore_creates_new_version_with_previous_plan(client, auth):
    itinerary = _generated_itinerary(client, auth)
    stop = _first_stop(itinerary["plan"])
    replan = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan",
        headers=auth,
        json={"request_text": f"remove stop {stop['id']} on day 1"},
    )
    assert replan.status_code == 200, replan.text
    assert replan.json()["version"] == 1

    restored = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/versions/restore",
        headers=auth,
        json={"version": 1},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["version"] == 2
    assert _first_stop(restored.json()["plan"])["id"] == stop["id"]

    versions = client.get(f"/api/v1/itineraries/{itinerary['id']}/versions", headers=auth)
    assert [version["version"] for version in versions.json()] == [2, 1]


def test_replan_rejects_budget_overflow(client, auth):
    itinerary = _generated_itinerary(client, auth)
    with SessionLocal() as db:
        stored = db.get(Itinerary, itinerary["id"])
        preferences = dict(stored.preferences)
        preferences["budget"] = 1
        stored.preferences = preferences
        db.commit()
        available = load_catalog(db).pois("lahore")
    planned_ids = {
        item["id"] for day in itinerary["plan"]["days"] for item in day["items"] if item.get("kind") == "stop"
    }
    new_place = next(place for place in available if place["id"] not in planned_ids)
    response = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan",
        headers=auth,
        json={"request_text": f"add place {new_place['id']} on day 1"},
    )

    assert response.status_code == 400
    assert "budget" in response.json()["detail"].lower()


def test_progress_rejects_unknown_stops_and_locks_completed_stops(client, auth):
    itinerary = _generated_itinerary(client, auth)
    stop = _first_stop(itinerary["plan"])
    progress_url = f"/api/v1/itineraries/{itinerary['id']}/progress"

    unknown = client.put(
        progress_url,
        headers=auth,
        json={"day": 1, "completed_stop_ids": ["does-not-exist"]},
    )
    assert unknown.status_code == 400
    assert "Unknown stop" in unknown.json()["detail"]

    updated = client.put(
        progress_url,
        headers=auth,
        json={"day": 1, "completed_stop_ids": [stop["id"]], "current_time": "14:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["completed_stop_ids"] == [stop["id"]]

    blocked = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan",
        headers=auth,
        json={"request_text": f"remove stop {stop['id']} on day 1"},
    )
    assert blocked.status_code == 400
    assert "already completed" in blocked.json()["detail"]


def test_replanning_is_owner_scoped(client, auth):
    itinerary = _generated_itinerary(client, auth)
    other = client.post(
        "/api/v1/auth/register",
        json={"name": "Other User", "email": "replan-other@example.com", "password": "secret123"},
    )
    assert other.status_code == 201
    other_auth = {"Authorization": f"Bearer {other.json()['token']}"}

    response = client.get(f"/api/v1/itineraries/{itinerary['id']}/versions", headers=other_auth)
    assert response.status_code == 404

    response = client.post(
        f"/api/v1/itineraries/{itinerary['id']}/replan/preview",
        headers=other_auth,
        json={"request_text": "start later by 30 minutes on day 1"},
    )
    assert response.status_code == 404
