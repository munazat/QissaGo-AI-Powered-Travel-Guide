"""Reads cities, interests and places from the database into plain dictionaries.

Agents work on these dictionaries, so they can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, selectinload

from app.db.models import City, Interest, Poi


@dataclass
class Catalog:
    cities: dict[str, dict] = field(default_factory=dict)
    interests: dict[str, dict] = field(default_factory=dict)
    pois_by_city: dict[str, list[dict]] = field(default_factory=dict)

    def pois(self, city_id: str) -> list[dict]:
        return self.pois_by_city.get(city_id, [])


def city_dict(c: City) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "province": c.province,
        "lat": c.lat,
        "lon": c.lon,
        "aliases": [a for a in c.aliases.split("|") if a],
        "hotel_budget": c.hotel_budget,
        "hotel_mid": c.hotel_mid,
        "meal_pp_day": c.meal_pp_day,
        "transport_per_km": c.transport_per_km,
        "jeep_per_day": c.jeep_per_day or 0,
        "speed_kmh": c.speed_kmh or 24.0,
        "road_factor": c.road_factor or 1.35,
        "description": c.description,
        "image": c.image,
        "image_credit": c.image_credit,
    }


def poi_dict(p: Poi) -> dict:
    return {
        "id": p.id,
        "city_id": p.city_id,
        "name": p.name,
        "category": p.category,
        "tags": sorted(i.id for i in p.interests),
        "cost_pp": p.cost_pp,
        "cost_foreign": p.cost_foreign or p.cost_pp,
        "access": p.access or "",
        "minutes": p.visit_minutes,
        "lat": p.lat,
        "lon": p.lon,
        "outdoor": p.outdoor,
        "best_time": p.best_time,
        "open": p.open_time,
        "close": p.close_time,
        "priority": p.priority,
        "description": p.description,
        "wiki_url": p.wiki_url,
        "image": p.image,
        "image_credit": p.image_credit,
        "image_license": p.image_license,
    }


def load_catalog(db: Session) -> Catalog:
    cat = Catalog()
    for c in db.query(City).order_by(City.name):
        cat.cities[c.id] = city_dict(c)
    for i in db.query(Interest).order_by(Interest.label):
        cat.interests[i.id] = {
            "id": i.id,
            "label": i.label,
            "keywords": [k for k in i.keywords.split("|") if k],
        }
    for p in db.query(Poi).options(selectinload(Poi.interests)).order_by(Poi.id):
        cat.pois_by_city.setdefault(p.city_id, []).append(poi_dict(p))
    return cat
