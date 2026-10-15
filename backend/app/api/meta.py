"""Options for the quick-select form: cities, interests, paces, group types."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.catalog import Catalog

from .deps import catalog

router = APIRouter(tags=["meta"])


@router.get("/meta")
def meta(cat: Catalog = Depends(catalog)) -> dict:
    return {
        "cities": [
            {
                "id": c["id"],
                "name": c["name"],
                "province": c["province"],
                "image": c["image"],
                "image_credit": c["image_credit"],
                "description": c["description"],
                "places": len(cat.pois(c["id"])),
            }
            for c in cat.cities.values()
        ],
        "interests": [{"id": i["id"], "label": i["label"]} for i in cat.interests.values()],
        "paces": [
            {"id": "relaxed", "label": "Relaxed"},
            {"id": "balanced", "label": "Balanced"},
            {"id": "packed", "label": "Packed"},
        ],
        "groups": [
            {"id": "solo", "label": "Solo", "size": 1},
            {"id": "couple", "label": "Couple", "size": 2},
            {"id": "family", "label": "Family", "size": 4},
            {"id": "friends", "label": "Friends", "size": 4},
        ],
        "needs": [
            {"id": "kids", "label": "With kids"},
            {"id": "elderly", "label": "Elderly"},
            {"id": "indoor", "label": "Prefer indoors"},
            {"id": "late_start", "label": "Late start"},
            {"id": "no_stay", "label": "No hotel needed"},
        ],
    }


@router.get("/cities/{city_id}/places")
def places(city_id: str, cat: Catalog = Depends(catalog)) -> list[dict]:
    return [
        {k: p[k] for k in ("id", "name", "category", "tags", "lat", "lon", "image", "description")}
        for p in cat.pois(city_id)
    ]
