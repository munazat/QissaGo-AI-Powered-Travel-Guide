"""Enrichment agent: adds what each stop shows in the app - group price, weather note,
map links, photo and description - plus a route link and totals for each day."""

from __future__ import annotations

from app.services.geo import directions_link, google_maps_link, osm_link

from . import costs
from .base import Agent, hm_to_min


def weather_note(stop: dict, day_w: dict) -> str:
    if stop["outdoor"] and day_w["rainy"]:
        return f"Rain likely ({day_w['rain_pct']}%)"
    if stop["outdoor"] and day_w["hot"]:
        start = hm_to_min(stop["start"])
        if start >= 16 * 60 + 30:
            return f"{day_w['tmax']}°C, cooler in the evening"
        if 11 * 60 <= start < 16 * 60 + 30:
            return f"{day_w['tmax']}°C, carry water"
    if not stop["outdoor"] and day_w["rainy"]:
        return "Indoors"
    return ""


class EnrichmentAgent(Agent):
    name = "Enrichment Agent"
    role = "Adds prices, distances, weather and maps"

    def run(self, state: dict) -> str:
        p = state["prefs"]
        count = 0
        for sch in state["schedules"].values():
            for day in sch["days"]:
                stops = [s for s in day["items"] if s["kind"] == "stop"]
                jeep_day = any(costs.needs_jeep(s) for s in stops)
                for s in stops:
                    s["cost_group"] = costs.entry_pp(s, p.get("traveller_type", "local")) * p["size"]
                    if jeep_day and s.get("leg"):
                        # The hired jeep covers all driving on this day.
                        s["leg"] = {**s["leg"], "cost": 0, "mode": "jeep"}
                    s["weather_note"] = weather_note(s, day["weather"])
                    s["map_url"] = google_maps_link(s["lat"], s["lon"])
                    s["osm_url"] = osm_link(s["lat"], s["lon"])
                    s.pop("score", None)
                    count += 1
                day["route_url"] = directions_link([(s["lat"], s["lon"]) for s in stops])
                day["km"] = round(sum((s.get("leg") or {}).get("km", 0) for s in stops), 1)
                day["travel_minutes"] = sum((s.get("leg") or {}).get("minutes", 0) for s in stops)
                day["jeep"] = jeep_day
                day["cost"] = sum(s["cost_group"] + (s.get("leg") or {}).get("cost", 0) for s in stops) + (
                    costs.jeep_cost(p["city"], 1, p["size"]) if jeep_day else 0
                )
                day["stops"] = len(stops)
        return f"Details added to {count} stops."
