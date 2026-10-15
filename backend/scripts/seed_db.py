"""Create the tables and load cities, interests and places from the CSV files.

Run from the backend folder:
    python -m scripts.seed_db

Safe to run again: existing rows are updated, nothing is duplicated.
If `data/seed/media.csv` exists (made by `scripts.fetch_wikipedia`), its Wikipedia
descriptions, coordinates and image paths are applied on top of the CSV values.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import City, Interest, Poi
from app.db.session import SessionLocal, create_tables

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"


def read_csv(name: str) -> list[dict]:
    path = SEED_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_media() -> dict[str, dict]:
    return {row["id"]: row for row in read_csv("media.csv")}


def apply_media(obj, media: dict | None, own_coords: bool = True) -> None:
    if not media:
        return
    if media.get("description"):
        obj.description = media["description"]
    if media.get("image"):
        obj.image = media["image"]
        obj.image_credit = media.get("image_credit", "")
        if hasattr(obj, "image_license"):
            obj.image_license = media.get("image_license", "")
    if media.get("wiki_url") and hasattr(obj, "wiki_url"):
        obj.wiki_url = media["wiki_url"]
    # Wikipedia coordinates replace the hand-entered estimates for places
    # Places that share one article (e.g. several trails in one park) keep their own coordinates.
    if own_coords and media.get("lat") and media.get("lon") and isinstance(obj, Poi):
        obj.lat, obj.lon = float(media["lat"]), float(media["lon"])


def seed(db: Session) -> dict[str, int]:
    media = load_media()
    travel = {row["city_id"]: row for row in read_csv("city_travel.csv")}

    for row in read_csv("interests.csv"):
        db.merge(Interest(id=row["id"], label=row["label"], keywords=row["keywords"]))
    db.flush()
    interests = {i.id: i for i in db.query(Interest).all()}

    for row in read_csv("cities.csv"):
        city = db.get(City, row["id"]) or City(id=row["id"])
        city.name, city.province = row["name"], row["province"]
        city.lat, city.lon = float(row["lat"]), float(row["lon"])
        city.aliases = row["aliases"]
        city.hotel_budget, city.hotel_mid = int(row["hotel_budget"]), int(row["hotel_mid"])
        city.meal_pp_day, city.transport_per_km = int(row["meal_pp_day"]), int(row["transport_per_km"])
        city.jeep_per_day = int(row.get("jeep_per_day") or 0)
        speed = travel.get(row["id"], {})
        city.speed_kmh = float(speed.get("speed_kmh") or 24)
        city.road_factor = float(speed.get("road_factor") or 1.35)
        city.wiki_title, city.description = row["wiki_title"], row["description"]
        apply_media(city, media.get(f"city:{row['id']}"))
        db.add(city)
    db.flush()

    count = 0
    poi_rows = read_csv("pois.csv")
    titles = [r["wiki_title"] for r in poi_rows if r["wiki_title"]]
    shared = {t for t in titles if titles.count(t) > 1}
    for row in poi_rows:
        poi = db.get(Poi, row["id"]) or Poi(id=row["id"])
        poi.city_id, poi.name, poi.category = row["city_id"], row["name"], row["category"]
        poi.cost_pp = int(row["entry_fee_local"])
        poi.cost_foreign = int(row.get("entry_fee_foreign") or row["entry_fee_local"])
        poi.access = row.get("access", "")
        poi.visit_minutes = int(row["visit_minutes"])
        poi.lat, poi.lon = float(row["lat"]), float(row["lon"])
        poi.outdoor = row["outdoor"].strip() == "1"
        poi.best_time = row["best_time"]
        poi.open_time, poi.close_time = row["open_time"], row["close_time"]
        poi.priority = int(row["priority"])
        poi.wiki_title, poi.description = row["wiki_title"], row["description"]
        poi.interests = [interests[t] for t in row["interests"].split("|") if t in interests]
        apply_media(poi, media.get(row["id"]), own_coords=row["wiki_title"] not in shared)
        db.add(poi)
        count += 1
    db.commit()
    return {"cities": db.query(City).count(), "interests": len(interests), "places": count}


def main() -> None:
    create_tables()
    with SessionLocal() as db:
        result = seed(db)
    print(f"Seeded {result['cities']} cities, {result['interests']} interests, {result['places']} places.")


if __name__ == "__main__":
    sys.exit(main())
