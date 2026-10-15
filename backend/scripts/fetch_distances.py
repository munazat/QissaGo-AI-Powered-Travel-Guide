"""Road distances between all cities and local travel speeds per city - ONCE.

Run from the backend folder (needs internet):
    python -m scripts.fetch_distances

Uses the free public OSRM router (https://router.project-osrm.org, OpenStreetMap data):
  1. city-to-city driving distance and time  -> data/seed/road_distances.csv
  2. for each city, routes between pairs of its places -> median road/straight-line factor and
     median speed, written to data/seed/city_travel.csv. OSRM assumes empty roads, so the speed is
     multiplied by TRAFFIC (stops, traffic, narrow lanes) before the planner uses it.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import math
import statistics
import sys
import time
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND / "data" / "seed"
OSRM = "https://router.project-osrm.org"
HEADERS = {"User-Agent": "QissaGo/0.1 (university final-year project; contact via GitHub)"}
TRAFFIC = 0.7
# Mountain roads: single lane, landslide patches, jeep tracks and photo stops. OSRM still uses
# paved-road speeds there, so these cities get a stronger slowdown.
MOUNTAIN_TRAFFIC = 0.45
MOUNTAIN_CITIES = {"murree", "hunza", "skardu", "swat", "kalam"}
PAIRS_PER_CITY = 14


def straight_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def travel_stats(samples: list[tuple[float, float, float]], traffic: float = TRAFFIC) -> tuple[float, float]:
    """(road factor, speed km/h) from (straight km, road km, hours) samples, using medians."""
    usable = [(s, r, h) for s, r, h in samples if s > 0.5 and r > 0 and h > 0]
    if not usable:
        return 1.35, 24.0
    factor = statistics.median(r / s for s, r, _ in usable)
    speed = statistics.median(r / h for _, r, h in usable) * traffic
    return round(min(max(factor, 1.1), 2.5), 2), round(speed, 1)


def route(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
    url = f"{OSRM}/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}"
    for attempt in range(3):
        try:
            r = requests.get(url, params={"overview": "false"}, headers=HEADERS, timeout=30)
            if r.status_code == 200 and r.json().get("code") == "Ok":
                best = r.json()["routes"][0]
                return best["distance"] / 1000, best["duration"] / 3600
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def main() -> None:
    with (SEED_DIR / "cities.csv").open(encoding="utf-8", newline="") as f:
        cities = list(csv.DictReader(f))
    with (SEED_DIR / "pois.csv").open(encoding="utf-8", newline="") as f:
        pois = list(csv.DictReader(f))
    today = dt.date.today().isoformat()

    rows = []
    for a, b in itertools.combinations(cities, 2):
        hit = route((float(a["lat"]), float(a["lon"])), (float(b["lat"]), float(b["lon"])))
        if hit:
            rows.append(
                {
                    "from_id": a["id"],
                    "to_id": b["id"],
                    "km": round(hit[0]),
                    "hours": round(hit[1], 1),
                    "source": "OSRM / OpenStreetMap",
                    "checked_on": today,
                }
            )
            print(f"{a['id']} - {b['id']}: {hit[0]:.0f} km")
        time.sleep(1)
    with (SEED_DIR / "road_distances.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["from_id", "to_id", "km", "hours", "source", "checked_on"])
        w.writeheader()
        w.writerows(rows)

    travel = []
    for c in cities:
        places = [(float(p["lat"]), float(p["lon"])) for p in pois if p["city_id"] == c["id"]]
        pairs = list(itertools.combinations(places, 2))
        step = max(1, len(pairs) // PAIRS_PER_CITY)
        samples = []
        for a, b in pairs[::step][:PAIRS_PER_CITY]:
            hit = route(a, b)
            if hit:
                samples.append((straight_km(*a, *b), hit[0], hit[1]))
            time.sleep(1)
        factor, speed = travel_stats(samples, MOUNTAIN_TRAFFIC if c["id"] in MOUNTAIN_CITIES else TRAFFIC)
        travel.append(
            {
                "city_id": c["id"],
                "road_factor": factor,
                "speed_kmh": speed,
                "samples": len(samples),
                "source": "OSRM / OpenStreetMap",
                "checked_on": today,
            }
        )
        print(f"{c['id']}: factor {factor}, {speed} km/h from {len(samples)} routes")
    with (SEED_DIR / "city_travel.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["city_id", "road_factor", "speed_kmh", "samples", "source", "checked_on"])
        w.writeheader()
        w.writerows(travel)


if __name__ == "__main__":
    sys.exit(main())
