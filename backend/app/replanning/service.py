from __future__ import annotations

import copy
import datetime as dt

from app.agents.base import hm_to_min, min_to_hm
from app.agents.scheduling import DAY_LIMIT, layout_day, order_day
from app.services.catalog import Catalog
from app.services.geo import directions_link, google_maps_link, osm_link

from .contracts import ChangeKind, ChangeRequest, ReplanDiff


def apply_change(
    plan: dict, prefs: dict, change: ChangeRequest, catalog: Catalog, execution: dict | None = None
) -> tuple[dict, ReplanDiff]:
    updated = copy.deepcopy(plan)
    days = updated.get("days", [])
    execution = execution or {}
    completed = set(execution.get("completed_stop_ids", [])) | set(execution.get("skipped_stop_ids", []))
    affected: set[int] = set()
    added: list[str] = []
    removed: list[str] = []
    moved: list[str] = []

    if change.kind == ChangeKind.START_LATER:
        day_index = _index(change.day or 1, days)
        _shift_day(days[day_index], change.minutes)
        affected.add(change.day or 1)
    elif change.kind in (ChangeKind.REMOVE, ChangeKind.MOVE, ChangeKind.CHANGE_DAY):
        source_index, item = _find_stop(days, change.place_id or "", change.day)
        if item is None:
            raise ValueError(f"Stop '{change.place_id}' was not found in this itinerary.")
        if item.get("id") in completed:
            raise ValueError("That stop is already completed and cannot be changed.")
        days[source_index]["items"].remove(item)
        affected.add(source_index + 1)
        if change.kind == ChangeKind.REMOVE:
            removed.append(item["name"])
        else:
            target_index = _index(change.target_day or 1, days)
            days[target_index]["items"].append(item)
            affected.add(target_index + 1)
            moved.append(item["name"])
    elif change.kind == ChangeKind.ADD:
        target_index = _index(change.day or 1, days)
        poi = next((p for p in catalog.pois(prefs["city_id"]) if p["id"] == change.place_id), None)
        if poi is None:
            raise ValueError(f"Place '{change.place_id}' is not available in this city.")
        if any(item.get("id") == poi["id"] for day in days for item in day.get("items", [])):
            raise ValueError("That place is already in the itinerary.")
        new_item = copy.deepcopy(poi)
        new_item["kind"] = "stop"
        new_item.setdefault("score", new_item.get("priority", 0))
        days[target_index]["items"].append(new_item)
        affected.add(target_index + 1)
        added.append(poi["name"])

    for day_number in sorted(affected):
        _reschedule(days[day_number - 1], prefs, catalog, execution)

    diff = ReplanDiff(
        affected_days=sorted(affected),
        added=added,
        removed=removed,
        moved=moved,
        reason=change.kind.value,
    )
    updated["days"] = days
    return updated, diff


def _index(day: int, days: list[dict]) -> int:
    if day < 1 or day > len(days):
        raise ValueError(f"Day {day} is outside this itinerary.")
    return day - 1


def _find_stop(days: list[dict], place_id: str, requested_day: int | None) -> tuple[int, dict | None]:
    indexes = range(len(days)) if requested_day is None else [_index(requested_day, days)]
    for index in indexes:
        for item in days[index].get("items", []):
            if item.get("kind") == "stop" and (item.get("id") == place_id or item.get("name", "").lower() == place_id):
                return index, item
    return -1, None


def _shift_day(day: dict, minutes: int) -> None:
    for item in day.get("items", []):
        if "start" not in item or "end" not in item:
            continue
        start = hm_to_min(item["start"]) + minutes
        end = hm_to_min(item["end"]) + minutes
        if end > DAY_LIMIT:
            raise ValueError("That change would push the day past the allowed end time.")
        item["start"], item["end"] = min_to_hm(start), min_to_hm(end)


def _reschedule(day: dict, prefs: dict, catalog: Catalog, execution: dict | None = None) -> None:
    execution = execution or {}
    completed = set(execution.get("completed_stop_ids", [])) | set(execution.get("skipped_stop_ids", []))
    locked = [item for item in day.get("items", []) if item.get("kind") == "stop" and item.get("id") in completed]
    stops = [item for item in day.get("items", []) if item.get("kind") == "stop"]
    for stop in stops:
        stop.setdefault("score", stop.get("priority", 0))
    previous = {item.get("id"): item for item in stops}
    weather = day.get("weather", {})
    city = catalog.cities[prefs["city"]]
    remaining = [stop for stop in stops if stop.get("id") not in completed]
    ordered = order_day(remaining, weather)
    day_start = prefs.get("day_start", "09:00")
    if execution.get("day") == day.get("day") and execution.get("current_time"):
        day_start = max(day_start, execution["current_time"])
    items, dropped = layout_day(
        ordered,
        weather,
        day_start,
        city["transport_per_km"],
        max(1, (prefs.get("group_size") or prefs.get("size") or 1 + 3) // 4),
        city,
    )
    if dropped:
        raise ValueError(f"These stops no longer fit the day: {', '.join(dropped)}")
    for item in items:
        old = previous.get(item.get("id"), {})
        for key in ("cost_group", "weather_note", "image", "image_credit", "image_license", "description", "wiki_url"):
            if key in old:
                item[key] = old[key]
        item["map_url"] = google_maps_link(item["lat"], item["lon"])
        item["osm_url"] = osm_link(item["lat"], item["lon"])
    day["items"] = locked + items
    points = [(item["lat"], item["lon"]) for item in items if item.get("kind") == "stop"]
    day["route_url"] = directions_link(points)
    day["km"] = round(sum((item.get("leg") or {}).get("km", 0) for item in items), 1)
    day["travel_minutes"] = sum((item.get("leg") or {}).get("minutes", 0) for item in items)
    day["stops"] = len(items)
    date = dt.date.fromisoformat(day["date"])
    day["weekday"] = date.strftime("%a")
