"""Typical monthly weather for every city from Open-Meteo's free historical archive - ONCE.

Run from the backend folder (needs internet):
    python -m scripts.fetch_climate

For each city in data/seed/cities.csv it downloads daily max/min temperature and rain for
2015-2024 (ERA5 reanalysis via https://archive-api.open-meteo.com) and averages them per month:
  tmax, tmin  = mean daily high / low (C)
  rain_pct    = share of days with at least 1 mm of rain
Writes data/seed/climate.csv, which the weather service uses when no forecast exists.
"""

from __future__ import annotations

import csv
import datetime as dt
import sys
import time
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND / "data" / "seed"
CLIMATE_CSV = SEED_DIR / "climate.csv"
API = "https://archive-api.open-meteo.com/v1/archive"
HEADERS = {"User-Agent": "QissaGo/0.1 (university final-year project; contact via GitHub)"}
FIRST_YEAR, LAST_YEAR = 2015, 2024
RAIN_DAY_MM = 1.0
FIELDS = ["city_id", "month", "tmax", "tmin", "rain_pct", "years", "source_url", "checked_on"]


def monthly_climate(days: list[str], tmax: list, tmin: list, rain: list) -> list[dict]:
    """Average daily values per calendar month. Days with missing values are skipped."""
    sums = {m: {"hi": 0.0, "lo": 0.0, "n": 0, "wet": 0, "rn": 0} for m in range(1, 13)}
    for d, hi, lo, r in zip(days, tmax, tmin, rain, strict=True):
        m = int(d[5:7])
        if hi is not None and lo is not None:
            sums[m]["hi"] += hi
            sums[m]["lo"] += lo
            sums[m]["n"] += 1
        if r is not None:
            sums[m]["rn"] += 1
            sums[m]["wet"] += r >= RAIN_DAY_MM
    out = []
    for m in range(1, 13):
        s = sums[m]
        out.append(
            {
                "month": m,
                "tmax": round(s["hi"] / s["n"]) if s["n"] else None,
                "tmin": round(s["lo"] / s["n"]) if s["n"] else None,
                "rain_pct": round(100 * s["wet"] / s["rn"]) if s["rn"] else None,
            }
        )
    return out


def fetch_city(lat: float, lon: float) -> tuple[str, dict]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{FIRST_YEAR}-01-01",
        "end_date": f"{LAST_YEAR}-12-31",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "Asia/Karachi",
    }
    for attempt in range(4):
        r = requests.get(API, params=params, headers=HEADERS, timeout=120)
        if r.status_code == 200:
            return r.url, r.json()["daily"]
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    raise RuntimeError("unreachable")


def main() -> None:
    with (SEED_DIR / "cities.csv").open(encoding="utf-8", newline="") as f:
        cities = list(csv.DictReader(f))
    today = dt.date.today().isoformat()
    rows = []
    for c in cities:
        print(f"Climate for {c['id']}")
        url, daily = fetch_city(float(c["lat"]), float(c["lon"]))
        for m in monthly_climate(
            daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["precipitation_sum"]
        ):
            rows.append(
                {
                    "city_id": c["id"],
                    **m,
                    "years": f"{FIRST_YEAR}-{LAST_YEAR}",
                    "source_url": url,
                    "checked_on": today,
                }
            )
        time.sleep(3)
    with CLIMATE_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {CLIMATE_CSV.relative_to(BACKEND)}")


if __name__ == "__main__":
    sys.exit(main())
