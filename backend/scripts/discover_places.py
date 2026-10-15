"""Find attractions for a city from Wikidata and OpenStreetMap, for a person to review.

Run from the backend folder (needs internet):
    python -m scripts.discover_places --city hunza          # writes data/review/review_hunza.csv
    python -m scripts.discover_places --all                 # every city in AREAS
    python -m scripts.discover_places --merge               # add accepted rows to data/seed/pois.csv

What it does
  1. Finds each town centre on Wikidata (coordinates come from Wikidata, not typed by hand).
  2. Asks the Wikidata SPARQL endpoint for items with coordinates around that centre and keeps
     the kinds a visitor would go to (museums, mosques, shrines, forts, parks, lakes, valleys...).
  3. Adds named OpenStreetMap tourism/historic features from the Overpass API that Wikidata missed.
  4. Proposes a category, interests, priority and an `accept` value; writes a review CSV.
  5. --merge copies rows with accept=yes into pois.csv with default visit times and hours
     (verified=no until someone checks an official source).

Be polite: one request at a time with pauses. Both services are free and need no key.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import math
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND / "data" / "seed"
REVIEW_DIR = BACKEND / "data" / "review"
HEADERS = {"User-Agent": "QissaGo/0.1 (university final-year project; contact via GitHub)"}
WD_API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Search centres per city: (Wikidata search text, radius km). Several centres cover spread-out areas.
AREAS: dict[str, list[tuple[str, float]]] = {
    "multan": [("Multan", 12)],
    "peshawar": [("Peshawar", 12)],
    "murree": [("Murree", 25)],
    "hunza": [("Karimabad", 14), ("Gulmit", 16)],
    "skardu": [("Skardu", 32), ("Deosai National Park", 6)],
    "swat": [("Mingora", 14), ("Malam Jabba", 8)],
    "kalam": [("Kalam", 24), ("Mahodand Lake", 4), ("Ushu", 4)],
    "bahawalpur": [("Bahawalpur", 14), ("Derawar Fort", 3), ("Uch Sharif", 4), ("Lal Suhanra National Park", 5)],
}
ID_PREFIX = {
    "multan": "mux",
    "peshawar": "pew",
    "murree": "mur",
    "hunza": "hun",
    "skardu": "skd",
    "swat": "swt",
    "kalam": "klm",
    "bahawalpur": "bwp",
}

# (words found in the Wikidata/OSM type, category, interests). First match wins.
CATEGORY_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("museum", "gallery"), "museum", "history|art"),
    (("mosque", "masjid"), "mosque", "spiritual|history|art"),
    (("shrine", "dargah", "mausoleum", "tomb", "sufi"), "shrine", "spiritual|history"),
    (("fort", "castle", "citadel", "fortress"), "fort", "history|art"),
    (("palace", "haveli", "mahal"), "palace", "history|art"),
    (
        (
            "stupa",
            "monastery",
            "buddhist",
            "archaeological",
            "ruins",
            "rock relief",
            "petroglyph",
            "rock art",
            "historic site",
            "heritage site",
            "rock carving",
        ),
        "heritage site",
        "history",
    ),
    (("national park", "wildlife", "sanctuary", "protected area"), "national park", "nature|adventure"),
    (("zoo",), "zoo", "family|nature"),
    (("botanical", "garden"), "garden", "nature|family"),
    (("park",), "park", "nature|family"),
    (("lake", "reservoir"), "lake", "nature|adventure"),
    (("waterfall",), "waterfall", "nature|adventure"),
    (("glacier",), "glacier", "nature|adventure"),
    (("valley", "meadow", "plateau", "pass"), "valley", "nature|adventure"),
    (("viewpoint", "scenic viewpoint", "lookout"), "viewpoint", "nature"),
    (("ski", "chairlift", "cable car", "aerial tramway", "resort"), "adventure", "adventure|family"),
    (("market", "bazaar", "bazar"), "market", "shopping|food"),
    (("church", "cathedral", "temple", "gurdwara"), "church", "spiritual|history|art"),
    (("library",), "landmark", "history|art"),
    (("clock tower", "monument", "memorial", "gate"), "monument", "history"),
    (("bridge",), "landmark", "adventure"),
    (("attraction",), "landmark", "history"),
]
SKIP_WORDS = (
    "school",
    "college",
    "university",
    "hospital",
    "village",
    "union council",
    "tehsil",
    "district",
    "railway",
    "airport",
    "station",
    "stadium",
    "hotel",
    "bank",
    "company",
    "office",
    "cemetery",
    "graveyard",
    "human settlement",
    "neighbourhood",
    "neighborhood",
    "residential",
    "road",
    "street",
    "dam",
    "power",
    "factory",
    "cantonment",
    "polling",
    "constituency",
    "river",
    "stream",
    "mountain",
)

# Defaults for merged rows: minutes, outdoor, best time, open, close, local fee, foreign fee.
DEFAULTS: dict[str, tuple[int, int, str, str, str, int, int]] = {
    "museum": (90, 0, "midday", "09:00", "16:30", 50, 500),
    "mosque": (45, 1, "any", "06:00", "21:00", 0, 0),
    "shrine": (45, 1, "evening", "06:00", "22:00", 0, 0),
    "fort": (90, 1, "morning", "09:00", "17:00", 100, 500),
    "palace": (75, 0, "morning", "09:00", "17:00", 100, 500),
    "heritage site": (60, 1, "morning", "08:00", "17:00", 50, 400),
    "national park": (180, 1, "morning", "07:00", "17:00", 100, 500),
    "zoo": (120, 1, "morning", "08:00", "17:00", 50, 50),
    "garden": (60, 1, "evening", "07:00", "20:00", 30, 30),
    "park": (60, 1, "evening", "07:00", "21:00", 30, 30),
    "lake": (90, 1, "morning", "07:00", "18:00", 0, 0),
    "waterfall": (60, 1, "midday", "07:00", "18:00", 0, 0),
    "glacier": (120, 1, "morning", "07:00", "16:00", 0, 0),
    "valley": (120, 1, "morning", "07:00", "18:00", 0, 0),
    "viewpoint": (45, 1, "evening", "06:00", "19:00", 0, 0),
    "adventure": (120, 1, "morning", "09:00", "17:00", 500, 500),
    "market": (90, 1, "evening", "11:00", "21:00", 0, 0),
    "church": (40, 0, "morning", "09:00", "17:00", 0, 0),
    "landmark": (45, 1, "any", "08:00", "20:00", 0, 0),
    "monument": (45, 1, "any", "08:00", "20:00", 0, 0),
}
REVIEW_FIELDS = [
    "accept",
    "city_id",
    "source",
    "qid",
    "osm_id",
    "name",
    "types",
    "description",
    "lat",
    "lon",
    "dist_km",
    "enwiki",
    "sitelinks",
    "image",
    "category",
    "interests",
    "priority",
    "reason",
]
POI_FIELDS = [
    "id",
    "city_id",
    "name",
    "category",
    "interests",
    "entry_fee_local",
    "entry_fee_foreign",
    "visit_minutes",
    "lat",
    "lon",
    "outdoor",
    "best_time",
    "open_time",
    "close_time",
    "priority",
    "access",
    "wiki_title",
    "description",
    "fee_source_url",
    "hours_source_url",
    "checked_on",
    "verified",
]
MAX_PER_CITY = 35


# ----------------------------------------------------------------------------- pure helpers (tested)


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:28]


def categorize(types: str, name: str = "") -> tuple[str, str] | None:
    """(category, interests) from type labels and the name, or None for things visitors skip."""
    text = f"{types} {name}".lower()
    hay = types.lower()

    def has(words: tuple[str, ...], where: str) -> bool:
        return any(re.search(rf"\b{re.escape(w)}s?\b", where) for w in words)

    if has(SKIP_WORDS, hay) and not has(("fort", "museum", "mosque", "shrine", "lake", "park"), text):
        return None
    # Viewpoints first: "Passu Cones Viewpoint" is a viewpoint, not a valley.
    rules = sorted(CATEGORY_RULES, key=lambda r: r[1] != "viewpoint")
    for where in (hay, name.lower()):
        for words, category, interests in rules:
            if has(words, where):
                return category, interests
    return None


GENERIC = re.compile(
    r"^(view ?point|zero point|gate ?house|park|garden|lake|mosque|masjid|museum|shrine|bazaar|market|point)$"
    r"|\b(blocked|beautiful|closed|under construction|parking|toilet|washroom)\b",
    re.I,
)


def is_generic(name: str) -> bool:
    """Map labels like "View point" or "Rockfalls 2023 - road blocked" that are not a named place."""
    return bool(GENERIC.search(name.strip()))


def priority_for(sitelinks: int, enwiki: bool) -> int:
    if sitelinks >= 12:
        return 3
    if sitelinks >= 4 or enwiki:
        return 2
    return 1


def km_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def same_place(a: dict, b: dict) -> bool:
    """Same name (ignoring case/punctuation) or nearly the same spot with overlapping names."""
    na, nb = slug(a["name"]), slug(b["name"])
    close = km_between(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"])) < 0.25
    return na == nb or (close and (na in nb or nb in na))


# Names that are map labels, shops or road junctions rather than places to visit.
JUNK_NAME = re.compile(
    r"\b(chowk|hotel|office|mills?|factory|shooting|attack|graveyard|grave|auditorium|van|chase up|paved road|"
    r"plaza|store|shop|bank|school|hostel|inn|cafe|restaurant|petrol|pump|stop|adda|stand|hw|chungi)\b",
    re.I,
)
SKIP_TYPES = re.compile(r"\b(shooting|attack|event|massacre|bombing|battle|destroyed)\b", re.I)
# At most this many of one kind per city, so mountain cities are not all glaciers or lakes.
CATEGORY_CAP = {"glacier": 3, "lake": 6, "viewpoint": 5, "valley": 5, "landmark": 5, "monument": 4, "shrine": 8}
OSM_SPECIFIC = re.compile(
    r"\b(museum|viewpoint|zoo|theme park|gallery|fort|castle|monument|memorial|archaeological|ruins|palace|tomb|"
    r"park|garden|glacier|waterfall|lake)\b"
)


def similar_names(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, slug(a), slug(b)).ratio() >= 0.85


def same_place_fuzzy(a: dict, b: dict) -> bool:
    near = km_between(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"])) < 1.0
    return same_place(a, b) or (near and similar_names(a["name"], b["name"]))


def reject_reason(r: dict) -> str:
    """Why a candidate is not a place to visit, or "" when it is."""
    if not categorize(r["types"], r["name"]):
        return "not a visitor attraction"
    if not re.search(r"[A-Za-z]", r["name"]) or re.fullmatch(r"Q\d+", r["name"]):
        return "no English name"
    if is_generic(r["name"]) or JUNK_NAME.search(r["name"]):
        return "generic name"
    if SKIP_TYPES.search(r["types"]) and not re.search(r"\bfort", r["types"], re.I):
        return "event or lost building"
    if r["source"] == "osm" and not (r["qid"] or r["enwiki"]) and not OSM_SPECIFIC.search(r["types"].lower()):
        return "unspecific map label"
    return ""


def choose(rows: list[dict], limit: int = MAX_PER_CITY) -> list[dict]:
    """Drop duplicates and non-attractions, mark the best `limit` rows accept=yes."""
    kept: list[dict] = []
    per_cat: dict[str, int] = {}
    order = sorted(rows, key=lambda r: (-int(r["sitelinks"] or 0), r["source"] != "wikidata", r["name"]))
    for r in order:
        r["category"] = r["interests"] = r["priority"] = ""
        reason = reject_reason(r)
        if not reason and any(same_place_fuzzy(r, k) for k in kept):
            reason = "duplicate"
        if reason:
            r.update(accept="no", reason=reason)
            continue
        cat, interests = categorize(r["types"], r["name"])
        r["category"], r["interests"] = cat, interests
        r["priority"] = str(priority_for(int(r["sitelinks"] or 0), bool(r["enwiki"])))
        kept.append(r)
    accepted = 0
    for r in kept:
        cat = r["category"]
        if accepted >= limit:
            r.update(accept="no", reason="below the cut")
        elif per_cat.get(cat, 0) >= CATEGORY_CAP.get(cat, 99):
            r.update(accept="no", reason=f"enough {cat}s")
        else:
            r.update(accept="yes", reason="")
            per_cat[cat] = per_cat.get(cat, 0) + 1
            accepted += 1
    return rows


def union_candidates(old: list[dict], new: list[dict]) -> list[dict]:
    """New candidates plus earlier ones they do not already contain (same Wikidata item, OSM object or name+spot)."""

    def key(r: dict) -> str:
        return r.get("qid") or r.get("osm_id") or f"{slug(r['name'])}@{float(r['lat']):.3f},{float(r['lon']):.3f}"

    seen = {key(r) for r in new}
    return new + [r for r in old if key(r) not in seen]


def rechoose() -> None:
    """Apply the rules again to the review files already downloaded (no network)."""
    for path in sorted(REVIEW_DIR.glob("review_*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        rows = choose(rows)
        write_review(path, rows)
        print(f"{path.name}: {sum(r['accept'] == 'yes' for r in rows)} proposed")


def write_review(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["accept"] != "yes", -int(r["sitelinks"] or 0))):
            w.writerow({k: r.get(k, "") for k in REVIEW_FIELDS})


def merge_rows(existing: list[dict], review: list[dict], checked_on: str) -> list[dict]:
    """New pois.csv rows for accepted review rows that are not in pois.csv yet."""
    taken = {r["id"] for r in existing}
    names = {(r["city_id"], slug(r["name"])) for r in existing}
    out = []
    for r in review:
        if r.get("accept", "").strip().lower() != "yes":
            continue
        city = r["city_id"]
        if (city, slug(r["name"])) in names:
            continue
        pid = f"{ID_PREFIX.get(city, city[:3])}_{slug(r['name'])}"
        base, n = pid, 2
        while pid in taken:
            pid, n = f"{base}_{n}", n + 1
        taken.add(pid)
        names.add((city, slug(r["name"])))
        minutes, outdoor, best, opens, closes, fee_local, fee_foreign = DEFAULTS.get(
            r["category"], DEFAULTS["landmark"]
        )
        desc = (r.get("description") or "").strip()
        out.append(
            {
                "id": pid,
                "city_id": city,
                "name": r["name"],
                "category": r["category"],
                "interests": r["interests"],
                "entry_fee_local": fee_local,
                "entry_fee_foreign": fee_foreign,
                "visit_minutes": minutes,
                "lat": f"{float(r['lat']):.6f}",
                "lon": f"{float(r['lon']):.6f}",
                "outdoor": outdoor,
                "best_time": best,
                "open_time": opens,
                "close_time": closes,
                "priority": r["priority"] or 1,
                "access": "",
                "wiki_title": r.get("enwiki", ""),
                "description": desc[:1].upper() + desc[1:] + ("." if desc and not desc.endswith(".") else ""),
                "fee_source_url": "",
                "hours_source_url": "",
                "checked_on": checked_on,
                "verified": "no",
            }
        )
    return out


# ----------------------------------------------------------------------------- network


def _get(url: str, params: dict, tries: int = 4) -> requests.Response:
    for i in range(tries):
        r = requests.get(url, params=params, headers=HEADERS, timeout=90)
        if r.status_code == 200:
            return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()
    return r


def find_centre(name: str) -> tuple[str, float, float]:
    """Wikidata item and coordinates of a town (first Pakistani match)."""
    res = _get(WD_API, {"action": "wbsearchentities", "search": name, "language": "en", "limit": 7, "format": "json"})
    for e in res.json().get("search", []):
        q = e["id"]
        time.sleep(1)
        rows = sparql(f"SELECT ?c ?country WHERE {{ wd:{q} wdt:P625 ?c . OPTIONAL {{ wd:{q} wdt:P17 ?country }} }}")
        if rows and rows[0].get("country", {}).get("value", "").endswith("/Q843"):
            lon, lat = map(float, re.findall(r"[-\d.]+", rows[0]["c"]["value"]))
            return q, lat, lon
    # The search box ranks other countries first for short names like "Kalam": ask by exact label.
    rows = sparql(f'SELECT ?item ?c WHERE {{ ?item rdfs:label "{name}"@en ; wdt:P17 wd:Q843 ; wdt:P625 ?c . }} LIMIT 1')
    if rows:
        lon, lat = map(float, re.findall(r"[-\d.]+", rows[0]["c"]["value"])[:2])
        return rows[0]["item"]["value"].rsplit("/", 1)[-1], lat, lon
    raise SystemExit(f"No Pakistani Wikidata item with coordinates for '{name}'")


def sparql(query: str) -> list[dict]:
    r = _get(SPARQL, {"query": query, "format": "json"})
    return r.json()["results"]["bindings"]


def wikidata_around(lat: float, lon: float, radius: float) -> list[dict]:
    q = f"""
SELECT ?item ?itemLabel ?itemDescription ?coord ?dist ?article ?image ?links
       (GROUP_CONCAT(DISTINCT ?typeLabel; separator="|") AS ?types) WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "{radius}" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  ?item wdt:P31 ?type ; wikibase:sitelinks ?links .
  OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?item wdt:P18 ?image }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "en" .
    ?item rdfs:label ?itemLabel . ?item schema:description ?itemDescription . ?type rdfs:label ?typeLabel .
  }}
}} GROUP BY ?item ?itemLabel ?itemDescription ?coord ?dist ?article ?image ?links
"""
    out = []
    for b in sparql(q):
        lon_, lat_ = map(float, re.findall(r"[-\d.]+", b["coord"]["value"])[:2])
        article = b.get("article", {}).get("value", "")
        out.append(
            {
                "source": "wikidata",
                "qid": b["item"]["value"].rsplit("/", 1)[-1],
                "osm_id": "",
                "name": b.get("itemLabel", {}).get("value", ""),
                "types": b.get("types", {}).get("value", ""),
                "description": b.get("itemDescription", {}).get("value", ""),
                "lat": f"{lat_:.6f}",
                "lon": f"{lon_:.6f}",
                "dist_km": f"{float(b['dist']['value']):.1f}",
                "enwiki": requests.utils.unquote(article.rsplit("/", 1)[-1]).replace("_", " ") if article else "",
                "sitelinks": b.get("links", {}).get("value", "0"),
                "image": b.get("image", {}).get("value", ""),
            }
        )
    return out


OSM_FILTERS = [
    '["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"]',
    '["historic"~"fort|castle|monument|memorial|archaeological_site|ruins|palace|tomb"]',
    '["leisure"~"park|garden"]["name:en"]',
    '["natural"~"glacier|waterfall"]["name"]',
    '["water"="lake"]["name"]',
]


def osm_around(lat: float, lon: float, radius: float) -> list[dict]:
    parts = "".join(f"nwr{f}[name](around:{int(radius * 1000)},{lat},{lon});" for f in OSM_FILTERS)
    q = f"[out:json][timeout:90];({parts});out center tags;"
    r = None
    for url in OVERPASS_MIRRORS:
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=150)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(5)
    if r is None or r.status_code != 200:
        raise requests.RequestException("all Overpass mirrors failed")
    out = []
    for e in r.json().get("elements", []):
        t = e.get("tags", {})
        name = t.get("name:en") or t.get("name", "")
        c = e.get("center") or e
        if "lat" not in c:
            continue
        kind = " ".join(
            v for k, v in t.items() if k in ("tourism", "historic", "leisure", "natural", "water", "amenity")
        )
        kind += " " + t.get("religion", "")
        out.append(
            {
                "source": "osm",
                "qid": t.get("wikidata", ""),
                "osm_id": f"{e['type']}/{e['id']}",
                "name": name,
                "types": kind.replace("_", " ").strip(),
                "description": "",
                "lat": f"{c['lat']:.6f}",
                "lon": f"{c['lon']:.6f}",
                "dist_km": f"{km_between(lat, lon, c['lat'], c['lon']):.1f}",
                "enwiki": (
                    t.get("wikipedia", "").split(":", 1)[-1] if t.get("wikipedia", "").startswith("en:") else ""
                ),
                "sitelinks": "0",
                "image": "",
            }
        )
    return out


def discover(city: str) -> Path:
    rows: list[dict] = []
    for name, radius in AREAS[city]:
        qid, lat, lon = find_centre(name)
        print(f"  {name}: {qid} at {lat:.4f}, {lon:.4f}, radius {radius} km")
        time.sleep(2)
        rows += wikidata_around(lat, lon, radius)
        time.sleep(2)
        try:
            osm = osm_around(lat, lon, radius)
        except requests.RequestException as exc:
            print(f"  ! Overpass failed: {exc}")
            osm = []
        known = {r["qid"] for r in rows if r["qid"]}
        rows += [o for o in osm if not o["qid"] or o["qid"] not in known]
        time.sleep(2)
    for r in rows:
        r["city_id"] = city
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = REVIEW_DIR / f"review_{city}.csv"
    if path.exists():  # a source can time out: keep what earlier runs found
        with path.open(encoding="utf-8", newline="") as f:
            rows = union_candidates(list(csv.DictReader(f)), rows)
    rows = choose(rows)
    write_review(path, rows)
    accepted = sum(1 for r in rows if r["accept"] == "yes")
    print(f"  -> {path.relative_to(BACKEND)}: {len(rows)} candidates, {accepted} proposed")
    return path


def merge() -> None:
    pois_path = SEED_DIR / "pois.csv"
    with pois_path.open(encoding="utf-8", newline="") as f:
        existing = list(csv.DictReader(f))
    review = []
    for p in sorted(REVIEW_DIR.glob("review_*.csv")):
        with p.open(encoding="utf-8", newline="") as f:
            review += list(csv.DictReader(f))
    new = merge_rows(existing, review, dt.date.today().isoformat())
    with pois_path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=POI_FIELDS, extrasaction="ignore")
        for r in new:
            w.writerow(r)
    print(f"Added {len(new)} places to pois.csv. Next: python -m scripts.fetch_wikipedia")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=sorted(AREAS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--rechoose", action="store_true", help="re-apply the rules to existing review files")
    a = ap.parse_args()
    if a.merge:
        merge()
        return
    if a.rechoose:
        rechoose()
        return
    cities = sorted(AREAS) if a.all else [a.city] if a.city else []
    if not cities:
        ap.error("give --city, --all or --merge")
    for c in cities:
        print(f"Discovering {c}")
        discover(c)


if __name__ == "__main__":
    sys.exit(main())
