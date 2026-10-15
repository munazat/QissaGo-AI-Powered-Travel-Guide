"""Shared cost rules used by the chatbot (budget checks) and the Budget agent.

All money is computed here in code, never by the LLM. City prices come from cities.csv
(each with a source URL); the national figures below are documented where they are defined.
"""

from __future__ import annotations

import math

from app.services import distances

KM_PER_DAY_FLOOR = 12  # minimum local travel assumed per day

# Intercity bus fare per km per person. Press reports, Aug 2026: Lahore-Islamabad Rs 4,000 (~375 km),
# Lahore-Karachi Rs 12,000 (~1,210 km), both about Rs 10 per km.
# https://thepakistanconnect.com/?p=106662
BUS_PKR_PER_KM = 10

# Own car: petrol Rs 398.30/litre (OGRA notification of 9 Oct 2026, reported by ARY News,
# https://arynews.tv/ogra-raises-petrol-price-cuts-diesel-rate-for-one-day) at 12 km per litre.
PETROL_PKR_PER_LITRE = 398.30
CAR_KM_PER_LITRE = 12

JEEP_SEATS = 5  # people per hired jeep
TRAVEL_MODES = ("bus", "car")


def cars(size: int) -> int:
    return max(1, math.ceil(size / 4))


def jeeps(size: int) -> int:
    return max(1, math.ceil(size / JEEP_SEATS))


def rooms(size: int) -> int:
    return max(1, math.ceil(size / 2))


def nights(days: int) -> int:
    return max(days - 1, 0)


def meals(city: dict, days: int, size: int) -> int:
    return city["meal_pp_day"] * days * size


def stay(city: dict, days: int, size: int, tier: str = "budget", no_stay: bool = False) -> int:
    if no_stay:
        return 0
    rate = city["hotel_mid"] if tier == "mid" else city["hotel_budget"]
    return rate * nights(days) * rooms(size)


def entry_pp(poi: dict, traveller_type: str = "local") -> int:
    """Per-person cost at a place: the foreign fee for foreign visitors when one is set."""
    if traveller_type == "foreign":
        return poi.get("cost_foreign") or poi["cost_pp"]
    return poi["cost_pp"]


def needs_jeep(poi: dict) -> bool:
    return poi.get("access") == "jeep"


def jeep_cost(city: dict, jeep_days: int, size: int) -> int:
    """Hired jeep with driver (fuel included) for each day that visits a jeep-only place."""
    return city.get("jeep_per_day", 0) * jeep_days * jeeps(size)


def car_pkr_per_km() -> float:
    return PETROL_PKR_PER_LITRE / CAR_KM_PER_LITRE


def travel_to_city(home_id: str | None, city_id: str, size: int, mode: str = "bus") -> int:
    """Return trip by road from the home city: bus seats for everyone, or fuel for the group's cars."""
    if not home_id or home_id == city_id:
        return 0
    km = distances.road_km(home_id, city_id)
    if km is None:
        return 0
    if mode == "car":
        return int(round(2 * km * car_pkr_per_km() * cars(size), -2))
    return int(round(2 * km * BUS_PKR_PER_KM * size, -2))


def minimum_trip_cost(
    city: dict,
    days: int,
    size: int,
    no_stay: bool = False,
    home_id: str | None = None,
    mode: str = "bus",
) -> int:
    transport = KM_PER_DAY_FLOOR * days * city["transport_per_km"] * cars(size)
    travel = travel_to_city(home_id, city.get("id", ""), size, mode)
    return meals(city, days, size) + stay(city, days, size, "budget", no_stay) + transport + travel


def round_up(value: int, step: int = 5000) -> int:
    return int(math.ceil(value / step) * step)
