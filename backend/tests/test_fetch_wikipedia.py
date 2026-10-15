"""The one-time Wikipedia fetch script, with the internet replaced by fake responses."""

import io

from PIL import Image

from scripts import fetch_wikipedia as fw


class FakeResponse:
    def __init__(self, data=None, content=b"", status=200):
        self._data, self.content, self.status_code = data, content, status

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


def fake_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2000, 1000), (46, 139, 87)).save(buf, "JPEG")
    return buf.getvalue()


def fake_get(url, params=None, headers=None, timeout=None):
    if url.startswith("https://upload"):
        return FakeResponse(content=fake_jpeg())
    if params and params.get("prop") == "imageinfo":
        meta = {"Artist": {"value": "<a href='x'>Jane Doe</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"}}
        return FakeResponse({"query": {"pages": [{"imageinfo": [{"extmetadata": meta}]}]}})
    page = {
        "title": params["titles"],
        "fullurl": "https://en.wikipedia.org/wiki/Lahore_Fort",
        "extract": "The Lahore Fort is a citadel. It was rebuilt in the 17th century. More text here.",
        "coordinates": [{"lat": 31.588, "lon": 74.315}],
        "thumbnail": {"source": "https://upload.wikimedia.org/x.jpg"},
        "pageimage": "Lahore_Fort.jpg",
    }
    return FakeResponse({"query": {"pages": [page]}})


def test_fetch_one_saves_resized_photo_with_credit(monkeypatch, tmp_path):
    monkeypatch.setattr(fw.requests, "get", fake_get)
    monkeypatch.setattr(fw, "IMG_DIR", tmp_path)
    row = fw.fetch_one("lhr_fort", "lhr_fort", "pois", "Lahore Fort")
    assert row["image"] == "/static/images/pois/lhr_fort.jpg"
    assert row["image_credit"] == "Jane Doe" and row["image_license"] == "CC BY-SA 4.0"
    assert row["lat"] == "31.588000" and row["description"].startswith("The Lahore Fort")
    saved = Image.open(tmp_path / "pois" / "lhr_fort.jpg")
    assert saved.width == 1280


def test_missing_page_is_skipped(monkeypatch):
    monkeypatch.setattr(fw.requests, "get", lambda *a, **k: FakeResponse({"query": {"pages": [{"missing": True}]}}))
    assert fw.fetch_one("x", "x", "pois", "No Such Page") is None
