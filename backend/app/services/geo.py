"""Distance and travel-time estimates (no external service needed)."""

from __future__ import annotations

import math

ROAD_FACTOR = 1.35  # straight-line distance -> rough road distance
AVG_SPEED_KMH = 24  # city traffic
MIN_LEG_MINUTES = 8


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def leg(
    a: dict,
    b: dict,
    cost_per_km: int,
    cars: int = 1,
    speed_kmh: float = AVG_SPEED_KMH,
    road_factor: float = ROAD_FACTOR,
) -> dict:
    """Travel estimate between two places: road km, minutes and cost for the group.
    Mountain cities pass their own (slower) speed and (more winding) road factor."""
    km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * road_factor
    minutes = max(MIN_LEG_MINUTES, round(km / speed_kmh * 60))
    cost = int(round(km * cost_per_km * cars, -1))
    return {"km": round(km, 1), "minutes": minutes, "cost": cost}


def osm_link(lat: float, lon: float) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map=17/{lat:.5f}/{lon:.5f}"


def google_maps_link(lat: float, lon: float) -> str:
    """Plain link (no API key, no cost): opens the location in Google Maps."""
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"


def directions_link(points: list[tuple[float, float]]) -> str:
    """Google Maps directions through several stops (plain link, no API key)."""
    if len(points) < 2:
        return google_maps_link(*points[0]) if points else ""
    fmt = [f"{la:.6f},{lo:.6f}" for la, lo in points]
    url = f"https://www.google.com/maps/dir/?api=1&origin={fmt[0]}&destination={fmt[-1]}"
    if len(fmt) > 2:
        url += "&waypoints=" + "%7C".join(fmt[1:-1])
    return url
