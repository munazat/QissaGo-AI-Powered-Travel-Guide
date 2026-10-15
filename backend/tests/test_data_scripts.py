"""One-time data scripts: the parts that do not need the internet."""

import csv
from pathlib import Path

from scripts.discover_places import categorize, choose, is_generic, merge_rows, priority_for, slug
from scripts.fetch_climate import monthly_climate
from scripts.fetch_distances import travel_stats

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"


def cand(name, types, source="wikidata", sitelinks=0, enwiki="", lat=36.3, lon=74.6, qid=""):
    return {
        "city_id": "hunza",
        "source": source,
        "qid": qid,
        "osm_id": "",
        "name": name,
        "types": types,
        "description": "fort in Hunza",
        "lat": str(lat),
        "lon": str(lon),
        "dist_km": "1",
        "enwiki": enwiki,
        "sitelinks": str(sitelinks),
        "image": "",
    }


def test_categorize():
    assert categorize("fortification", "Altit Fort") == ("fort", "history|art")
    assert categorize("landslide-dammed lake|lake", "Attabad Lake")[0] == "lake"  # "dammed" is not "dam"
    assert categorize("scenic viewpoint", "Passu Cones Viewpoint")[0] == "viewpoint"  # not a "pass"
    assert categorize("mausoleum", "Tomb of Shah Rukn-e-Alam")[0] == "shrine"
    assert categorize("village", "Ganish") is None
    assert categorize("mountain", "Ultar") is None
    assert categorize("school", "Gulmit School") is None


def test_generic_names_and_priority():
    assert is_generic("View point") and is_generic("Rockfalls 2023 - road blocked")
    assert not is_generic("Eagle's Nest")
    assert priority_for(20, True) == 3 and priority_for(5, False) == 2 and priority_for(0, True) == 2
    assert priority_for(0, False) == 1
    assert slug("Ghulkīn Glacier") == "ghulkin_glacier"


def test_choose_drops_junk_and_duplicates():
    rows = [
        cand("Baltit Fort", "fort", sitelinks=13, enwiki="Baltit Fort"),
        cand("Baltit Fort", "castle", source="osm", lat=36.3001),
        cand("Hussaini Suspension Bridge", "footbridge|bridge", sitelinks=4, enwiki="x", lat=36.42),
        cand("Husseini Suspension Bridge", "attraction bridge", source="osm", lat=36.4205),
        cand("Aziz Hotel Chowk", "viewpoint", source="osm", lat=36.1),
        cand("Some label", "attraction", source="osm", lat=36.2),
        cand("Bahawalpur church shooting", "mass shooting|church", sitelinks=4),
        cand("Karimabad", "town", sitelinks=18),
    ]
    out = {(r["name"], r["source"]): r for r in choose(rows)}
    assert out[("Baltit Fort", "wikidata")]["accept"] == "yes"
    assert out[("Baltit Fort", "osm")]["reason"] == "duplicate"
    assert out[("Husseini Suspension Bridge", "osm")]["accept"] == "no"
    assert out[("Aziz Hotel Chowk", "osm")]["accept"] == "no"
    assert out[("Some label", "osm")]["reason"] == "unspecific map label"
    assert out[("Bahawalpur church shooting", "wikidata")]["accept"] == "no"
    assert out[("Karimabad", "wikidata")]["reason"] == "not a visitor attraction"


def test_choose_caps_glaciers():
    rows = [cand(f"Glacier {chr(65 + i)}", "glacier", sitelinks=5 - i, lat=36 + i / 10) for i in range(6)]
    accepted = [r for r in choose(rows) if r["accept"] == "yes"]
    assert len(accepted) == 3


def test_merge_adds_accepted_rows_once_with_defaults():
    review = [
        {
            **cand("Altit Fort", "fort", enwiki="Altit Fort"),
            "accept": "yes",
            "category": "fort",
            "interests": "history|art",
            "priority": "2",
        },
        {**cand("Ganish", "village"), "accept": "no", "category": "", "interests": "", "priority": ""},
    ]
    existing = [{"id": "hun_x", "city_id": "hunza", "name": "Baltit Fort"}]
    new = merge_rows(existing, review, "2026-10-15")
    assert [r["id"] for r in new] == ["hun_altit_fort"]
    row = new[0]
    assert row["verified"] == "no" and row["checked_on"] == "2026-10-15"
    assert row["fee_source_url"] == "" and row["wiki_title"] == "Altit Fort"
    assert row["open_time"] < row["close_time"]
    assert merge_rows(existing + new, review, "2026-10-15") == []


def test_monthly_climate():
    days = ["2020-01-01", "2020-01-02", "2020-07-01", "2020-07-02"]
    out = monthly_climate(days, [10, 12, 30, None], [0, 2, 20, 22], [0, 5, 0.5, None])
    jan, jul = out[0], out[6]
    assert (jan["tmax"], jan["tmin"], jan["rain_pct"]) == (11, 1, 50)
    assert (jul["tmax"], jul["tmin"], jul["rain_pct"]) == (30, 20, 0)
    assert out[2]["tmax"] is None


def test_travel_stats():
    factor, speed = travel_stats([(2.0, 3.0, 0.1), (4.0, 5.6, 0.2), (0.1, 5.0, 1.0)])
    assert factor == 1.45  # median of 1.5 and 1.4; the 0.1 km pair is ignored
    assert speed == round(29.0 * 0.7, 1)
    assert travel_stats([]) == (1.35, 24.0)


def read(name):
    with (SEED / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_seed_data_is_complete():
    cities = {c["id"]: c for c in read("cities.csv")}
    assert len(cities) == 11
    for c in cities.values():
        assert c["prices_source_url"].startswith("https://"), c["id"]
        assert c["prices_verified"] in ("yes", "no")
    climate = read("climate.csv")
    assert {r["city_id"] for r in climate} == set(cities)
    assert all(len([r for r in climate if r["city_id"] == c]) == 12 for c in cities)
    pois = read("pois.csv")
    for p in pois:
        assert p["city_id"] in cities, p["id"]
        assert p["verified"] in ("yes", "no"), p["id"]
        assert int(p["entry_fee_foreign"]) >= int(p["entry_fee_local"]) >= 0, p["id"]
        if p["verified"] == "yes":
            assert p["fee_source_url"].startswith("http"), p["id"]
    ids = [p["id"] for p in pois]
    assert len(ids) == len(set(ids))


def test_rerun_keeps_earlier_candidates():
    from scripts.discover_places import union_candidates

    old = [cand("Kundol Lake", "lake", source="osm") | {"osm_id": "way/1"}, cand("Baltit Fort", "fort", qid="Q1")]
    new = [cand("Baltit Fort", "fort", qid="Q1", sitelinks=13)]
    merged = union_candidates(old, new)
    assert [r["name"] for r in merged] == ["Baltit Fort", "Kundol Lake"]
    assert merged[0]["sitelinks"] == "13"  # the fresh copy wins


def test_mountain_roads_are_slower():
    samples = [(2.0, 3.0, 0.1), (4.0, 5.6, 0.2)]
    _, plain = travel_stats(samples)
    _, mountain = travel_stats(samples, 0.45)
    assert mountain < plain


def test_shared_article_keeps_place_coordinates():
    from app.db.models import Poi
    from scripts.seed_db import apply_media

    media = {"lat": "33.75", "lon": "73.05", "description": "Park"}
    trail = Poi(lat=33.70, lon=73.10)
    apply_media(trail, media, own_coords=False)
    assert (trail.lat, trail.lon) == (33.70, 73.10)
    fort = Poi(lat=31.0, lon=74.0)
    apply_media(fort, media)
    assert (fort.lat, fort.lon) == (33.75, 73.05)
