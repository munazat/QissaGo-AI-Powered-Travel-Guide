from __future__ import annotations

from app.replanning.contracts import ChangeKind, ChangeRequest
from app.replanning.parser import parse_change
from app.replanning.service import apply_change
from app.services.catalog import Catalog


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
