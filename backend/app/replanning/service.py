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
    execution = copy.deepcopy(execution or {})
    execution.update(copy.deepcopy(plan.get("execution", {})))
    completed = set(execution.get("completed_stop_ids", [])) | set(execution.get("skipped_stop_ids", []))
    affected: set[int] = set()
    added: list[str] = []
    removed: list[str] = []
    visited: list[str] = []
    moved: list[str] = []
    budget_amount: int | None = None
    context: dict[str, str | int | float | bool] = {}
    if change.context:
        context = change.context
        execution.setdefault("context", {}).update(context)

    if change.kind == ChangeKind.UPDATE_BUDGET:
        budget_amount = change.budget_amount
        execution["remaining_budget"] = budget_amount
    elif change.kind == ChangeKind.UPDATE_CONTEXT:
        day_index = _index(change.day, days) if change.day else None
        target_days = [days[day_index]] if day_index is not None else days
        for target_day in target_days:
            if context.get("weather") == "rainy":
                target_day.setdefault("weather", {}).update({"rainy": True, "rain_pct": 100})
            elif context.get("weather") == "clear":
                target_day.setdefault("weather", {}).update({"rainy": False, "rain_pct": 0})
            affected.add(target_day.get("day", days.index(target_day) + 1))
        if context.get("current_time"):
            execution["current_time"] = context["current_time"]
            if change.day:
                execution["day"] = change.day
        if context.get("time_status") == "late":
            execution["time_status"] = "late"
        if context.get("fatigue") == "high":
            execution["fatigue"] = "high"
    elif change.kind == ChangeKind.START_LATER:
        day_index = _index(change.day or 1, days)
        _shift_day(days[day_index], change.minutes)
        affected.add(change.day or 1)
    elif change.kind == ChangeKind.MARK_VISITED:
        source_index, item = _find_stop(days, change.place_id or "", change.day)
        if item is None:
            raise ValueError(f"Stop '{change.place_id}' was not found in this itinerary.")
        completed_ids = set(execution.get("completed_stop_ids", []))
        completed_ids.add(item["id"])
        execution["completed_stop_ids"] = sorted(completed_ids)
        affected.add(source_index + 1)
        visited.append(item["name"])
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
        if context.get("weather") == "rainy":
            days[target_index].setdefault("weather", {}).update({"rainy": True, "rain_pct": 100})
        elif context.get("weather") == "clear":
            days[target_index].setdefault("weather", {}).update({"rainy": False, "rain_pct": 0})
        poi = _find_poi(catalog.pois(prefs["city_id"]), change.place_id or "", days)
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
        visited=visited,
        moved=moved,
        budget_amount=budget_amount,
        context=context,
        reason=change.kind.value,
    )
    updated["days"] = days
    if change.kind in (ChangeKind.MARK_VISITED, ChangeKind.UPDATE_BUDGET, ChangeKind.UPDATE_CONTEXT) or context:
        updated["execution"] = execution
    return updated, diff


def apply_changes(
    plan: dict, prefs: dict, changes: list[ChangeRequest], catalog: Catalog, execution: dict | None = None
) -> tuple[dict, ReplanDiff]:
    current = copy.deepcopy(plan)
    combined = ReplanDiff(
        affected_days=[], added=[], removed=[], visited=[], moved=[], budget_amount=None, context={}, reason="multiple"
    )
    for change in changes:
        current, diff = apply_change(current, prefs, change, catalog, current.get("execution", execution))
        combined.affected_days = sorted(set(combined.affected_days) | set(diff.affected_days))
        combined.added.extend(diff.added)
        combined.removed.extend(diff.removed)
        combined.visited.extend(diff.visited)
        combined.moved.extend(diff.moved)
        if diff.budget_amount is not None:
            combined.budget_amount = diff.budget_amount
        combined.context.update(diff.context)
        if current.get("execution"):
            combined_context = current["execution"].get("context", {})
            combined.context.update(combined_context)
    return current, combined


def _index(day: int, days: list[dict]) -> int:
    if day < 1 or day > len(days):
        raise ValueError(f"Day {day} is outside this itinerary.")
    return day - 1


def _find_stop(days: list[dict], place_id: str, requested_day: int | None) -> tuple[int, dict | None]:
    indexes = range(len(days)) if requested_day is None else [_index(requested_day, days)]
    query = _clean_place(place_id)
    ordinal = {"first": 0, "second": 1, "third": 2}.get(query)
    candidates: list[tuple[int, dict]] = []
    for index in indexes:
        for item in days[index].get("items", []):
            if item.get("kind") != "stop":
                continue
            candidates.append((index, item))
            name = _clean_place(item.get("name", ""))
            if item.get("id") == place_id or name == query or query in name or name in query:
                return index, item
    if ordinal is not None and ordinal < len(candidates):
        return candidates[ordinal]
    return -1, None


def _clean_place(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").split()).removeprefix("the ")


def _find_poi(pois: list[dict], query: str, days: list[dict]) -> dict | None:
    cleaned = _clean_place(query)
    existing = {item.get("id") for day in days for item in day.get("items", []) if item.get("kind") == "stop"}
    for poi in pois:
        name = _clean_place(poi.get("name", ""))
        if poi.get("id") == query or name == cleaned or cleaned in name or name in cleaned:
            return poi
    topics = {
        "cultural": {"history", "art", "spiritual"},
        "culture": {"history", "art", "spiritual"},
        "historical": {"history"},
        "history": {"history"},
        "museum": {"history", "art"},
        "indoor": {"history", "art", "spiritual"},
        "nature": {"nature"},
        "food": {"food"},
        "shopping": {"shopping"},
    }
    wanted = topics.get(cleaned, set())
    if wanted:
        return next(
            (poi for poi in pois if poi.get("id") not in existing and wanted.intersection(poi.get("tags", []))),
            None,
        )
    return None


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
    origin = _current_location(execution) if execution.get("day") == day.get("day") else None
    ordered = order_day(remaining, weather, origin)
    day_start = prefs.get("day_start", "09:00")
    if execution.get("day") == day.get("day") and execution.get("current_time"):
        day_start = max(day_start, execution["current_time"])
    if execution.get("fatigue") == "high":
        day_start = min_to_hm(min(hm_to_min(day_start) + 60, DAY_LIMIT - 60))
    items, dropped = layout_day(
        ordered,
        weather,
        day_start,
        city["transport_per_km"],
        max(1, (prefs.get("group_size") or prefs.get("size") or 1 + 3) // 4),
        city,
        origin,
    )
    if dropped:
        raise ValueError(f"These stops no longer fit the day: {', '.join(dropped)}")
    for item in items:
        if item.get("kind") != "stop":
            continue
        old = previous.get(item.get("id"), {})
        for key in ("cost_group", "weather_note", "image", "image_credit", "image_license", "description", "wiki_url"):
            if key in old:
                item[key] = old[key]
        item["map_url"] = google_maps_link(item["lat"], item["lon"])
        item["osm_url"] = osm_link(item["lat"], item["lon"])
    day["items"] = locked + items
    points = [(item["lat"], item["lon"]) for item in items if item.get("kind") == "stop"]
    route_points = ([(origin["lat"], origin["lon"])] if origin else []) + points
    day["route_url"] = directions_link(route_points)
    day["km"] = round(sum((item.get("leg") or {}).get("km", 0) for item in items), 1)
    day["travel_minutes"] = sum((item.get("leg") or {}).get("minutes", 0) for item in items)
    day["stops"] = len(items)
    date = dt.date.fromisoformat(day["date"])
    day["weekday"] = date.strftime("%a")


def _current_location(execution: dict) -> dict | None:
    latitude = execution.get("current_lat")
    longitude = execution.get("current_lon")
    if latitude is None or longitude is None:
        return None
    return {"lat": float(latitude), "lon": float(longitude)}
