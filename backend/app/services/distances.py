"""Road distances between cities, from data/seed/road_distances.csv (made once by
scripts/fetch_distances.py with the free OSRM router on OpenStreetMap data). No network at run time."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DISTANCES_CSV = Path(__file__).resolve().parents[2] / "data" / "seed" / "road_distances.csv"


@lru_cache(maxsize=1)
def _table() -> dict[tuple[str, str], tuple[float, float]]:
    out: dict[tuple[str, str], tuple[float, float]] = {}
    if not DISTANCES_CSV.exists():
        return out
    with DISTANCES_CSV.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            km, hours = float(r["km"]), float(r["hours"])
            out[(r["from_id"], r["to_id"])] = (km, hours)
            out.setdefault((r["to_id"], r["from_id"]), (km, hours))
    return out


def road_km(a: str, b: str) -> float | None:
    if a == b:
        return 0.0
    hit = _table().get((a, b))
    return hit[0] if hit else None


def road_hours(a: str, b: str) -> float | None:
    if a == b:
        return 0.0
    hit = _table().get((a, b))
    return hit[1] if hit else None
