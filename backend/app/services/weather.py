"""Weather per trip day: live Open-Meteo forecast (free, no key) or a seasonal estimate.

Forecasts only exist ~16 days ahead; further away we use typical monthly weather.
Results are cached in memory for an hour so repeated plans don't call the API again.
"""

from __future__ import annotations

import csv
import datetime as dt
import time
from pathlib import Path

import requests

from app.core.config import get_settings

_CACHE: dict[tuple, tuple[float, dict]] = {}
CACHE_SECONDS = 3600


def describe(code: int) -> tuple[str, str]:
    """WMO weather code -> (icon name used by the app, text)."""
    if code == 0:
        return "sunny", "Clear"
    if code in (1, 2):
        return "partly", "Partly cloudy"
    if code == 3:
        return "cloudy", "Overcast"
    if code in (45, 48):
        return "fog", "Fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain", "Rain"
    if 71 <= code <= 77:
        return "snow", "Snow"
    if code >= 95:
        return "storm", "Thunderstorm"
    return "partly", "Mixed"


CLIMATE_CSV = Path(__file__).resolve().parents[2] / "data" / "seed" / "climate.csv"


def load_climate(path: Path = CLIMATE_CSV) -> dict[str, list[tuple[int, int, int]]]:
    """Typical monthly climate per city: (avg high C, avg low C, rain chance %) for Jan..Dec.
    Made by scripts/fetch_climate.py from Open-Meteo's historical archive (2015-2024)."""
    out: dict[str, list[tuple[int, int, int]]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: (r["city_id"], int(r["month"])))
    for r in rows:
        out.setdefault(r["city_id"], []).append((int(r["tmax"]), int(r["tmin"]), int(r["rain_pct"])))
    return {c: months for c, months in out.items() if len(months) == 12}


SEASONAL = load_climate()
DEFAULT_SEASONAL = [(28, 16, 15)] * 12


def _day(date: dt.date, tmax: float, tmin: float, rain: int, code: int, source: str) -> dict:
    icon, text = describe(code)
    tmax, tmin = round(tmax), round(tmin)
    return {
        "date": date.isoformat(),
        "tmax": tmax,
        "tmin": tmin,
        "rain_pct": rain,
        "code": code,
        "icon": icon,
        "text": text,
        "source": source,
        "rainy": rain >= 50,
        "hot": tmax >= 36,
    }


def seasonal_day(city_id: str, date: dt.date) -> dict:
    hi, lo, rain = SEASONAL.get(city_id, DEFAULT_SEASONAL)[date.month - 1]
    code = 80 if rain >= 45 else 2 if rain >= 20 else 0
    return _day(date, hi, lo, rain, code, "seasonal")


def get_forecast(city_id: str, lat: float, lon: float, start: dt.date, days: int) -> dict:
    """Return {'days': [...], 'source': 'forecast' | 'seasonal'}."""
    dates = [start + dt.timedelta(days=i) for i in range(days)]
    key = (city_id, start.isoformat(), days)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]

    today = dt.date.today()
    in_range = dates[0] >= today and (dates[-1] - today).days <= 15
    if in_range and get_settings().live_weather:
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": "auto",
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "start_date": dates[0].isoformat(),
                    "end_date": dates[-1].isoformat(),
                },
                timeout=6,
            )
            r.raise_for_status()
            d = r.json()["daily"]
            out = [
                _day(
                    day,
                    d["temperature_2m_max"][i],
                    d["temperature_2m_min"][i],
                    int(d["precipitation_probability_max"][i] or 0),
                    int(d["weathercode"][i] or 0),
                    "forecast",
                )
                for i, day in enumerate(dates)
            ]
            result = {"days": out, "source": "forecast"}
            _CACHE[key] = (time.time(), result)
            return result
        except Exception:
            pass  # offline or blocked: fall back to typical weather
    return {"days": [seasonal_day(city_id, d) for d in dates], "source": "seasonal"}
