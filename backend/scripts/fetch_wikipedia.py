"""Fetch Wikipedia text, coordinates and one photo for every city and place - ONCE.

Run from the backend folder (needs internet):
    python -m scripts.fetch_wikipedia            # only places not fetched yet
    python -m scripts.fetch_wikipedia --force    # fetch everything again

What it does
  1. Reads data/seed/cities.csv and pois.csv (the `wiki_title` column).
  2. Asks the free Wikipedia API for a short summary, coordinates and the page photo.
  3. Downloads the photo, resizes it to max 1280 px wide and saves it in
     static/images/cities/<id>.jpg or static/images/pois/<id>.jpg
  4. Records the photo's author and licence (Wikimedia Commons requires credit).
  5. Writes everything to data/seed/media.csv.

Then run `python -m scripts.seed_db` to put it in the database.
Commit media.csv and the images to GitHub so teammates never need to fetch again.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import time
from pathlib import Path

import requests
from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND / "data" / "seed"
IMG_DIR = BACKEND / "static" / "images"
MEDIA_CSV = SEED_DIR / "media.csv"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "QissaGo/0.1 (university final-year project; contact via GitHub)"}
FIELDS = ["id", "wiki_url", "description", "lat", "lon", "image", "image_credit", "image_license"]


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def short_text(text: str, max_chars: int = 420) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    out = ""
    for s in sentences:
        if out and len(out) + len(s) > max_chars:
            break
        out = f"{out} {s}".strip()
    return out


def get(url: str, params: dict | None = None, timeout: int = 20) -> requests.Response:
    """GET that waits and retries when Wikipedia says "too many requests"."""
    for attempt in range(5):
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        if r.status_code != 429:
            return r
        wait = min(int(r.headers.get("Retry-After", 0) or 0) or 5 * (attempt + 1), 60)
        print(f"  ... rate limited, waiting {wait} s")
        time.sleep(wait)
    return r


def page_info(title: str) -> dict | None:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
        "titles": title,
        "prop": "extracts|coordinates|pageimages|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "piprop": "thumbnail|name",
        "pithumbsize": 1280,
    }
    r = get(API, params)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    return pages[0]


def image_credit(file_name: str) -> tuple[str, str]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "titles": f"File:{file_name}",
        "prop": "imageinfo",
        "iiprop": "extmetadata",
    }
    try:
        r = get(API, params)
        meta = r.json()["query"]["pages"][0]["imageinfo"][0]["extmetadata"]
        artist = clean_html(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons"
        licence = clean_html(meta.get("LicenseShortName", {}).get("value", ""))
        return artist[:200], licence[:100]
    except Exception:
        return "Wikimedia Commons", ""


def save_image(url: str, dest: Path) -> bool:
    r = get(url, timeout=40)
    if r.status_code != 200:
        return False
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    if img.width > 1280:
        img = img.resize((1280, round(img.height * 1280 / img.width)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True)
    return True


def fetch_one(key: str, file_id: str, folder: str, title: str) -> dict | None:
    page = page_info(title)
    if not page:
        print(f"  ! no Wikipedia page for '{title}'")
        return None
    row = {k: "" for k in FIELDS}
    row["id"] = key
    row["wiki_url"] = page.get("fullurl", "")
    row["description"] = short_text(page.get("extract", ""))
    coords = (page.get("coordinates") or [{}])[0]
    if coords.get("lat") is not None and folder == "pois":
        row["lat"], row["lon"] = f"{coords['lat']:.6f}", f"{coords['lon']:.6f}"
    thumb = (page.get("thumbnail") or {}).get("source")
    if thumb:
        dest = IMG_DIR / folder / f"{file_id}.jpg"
        if save_image(thumb, dest):
            row["image"] = f"/static/images/{folder}/{file_id}.jpg"
            row["image_credit"], row["image_license"] = image_credit(page.get("pageimage", ""))
    return row


def write_media(results: dict[str, dict]) -> None:
    with MEDIA_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for key in sorted(results):
            writer.writerow({k: results[key].get(k, "") for k in FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="fetch again even if already fetched")
    args = parser.parse_args()

    existing: dict[str, dict] = {}
    if MEDIA_CSV.exists() and not args.force:
        with MEDIA_CSV.open(encoding="utf-8", newline="") as f:
            existing = {r["id"]: r for r in csv.DictReader(f)}

    jobs = []
    with (SEED_DIR / "cities.csv").open(encoding="utf-8", newline="") as f:
        for c in csv.DictReader(f):
            jobs.append((f"city:{c['id']}", c["id"], "cities", c["wiki_title"]))
    with (SEED_DIR / "pois.csv").open(encoding="utf-8", newline="") as f:
        for p in csv.DictReader(f):
            jobs.append((p["id"], p["id"], "pois", p["wiki_title"]))

    results = dict(existing)
    done = 0
    for key, file_id, folder, title in jobs:
        if not title or key in existing:
            continue
        print(f"Fetching {key}  <-  {title}")
        try:
            row = fetch_one(key, file_id, folder, title)
        except Exception as exc:  # network problems: skip and keep going
            print(f"  ! failed: {exc}")
            row = None
        if row:
            results[key] = row
        done += 1
        if done % 10 == 0:
            write_media(results)  # keep progress if the run is stopped
        time.sleep(1.0)  # be polite to Wikipedia

    write_media(results)
    with_img = sum(1 for r in results.values() if r.get("image"))
    print(f"\nDone: {len(results)} entries in media.csv, {with_img} with photos.")
    print("Next: python -m scripts.seed_db")


if __name__ == "__main__":
    main()
