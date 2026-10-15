"""Preference extractor: pulls trip details out of a chat message.

Layer 1 - rules (always on, fast, testable): dates, numbers, money, keywords.
Layer 2 - LLM (optional, Ollama): fills in anything the rules missed.
The result is a dict of only the fields found in THIS message.
"""

from __future__ import annotations

import datetime as dt
import difflib
import re

from app.schemas.preferences import MAX_DAYS
from app.services.catalog import Catalog
from app.services.llm import LLM

NUM_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "couple of": 2,
}
NUM = r"(\d{1,2}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
MONTH_RE = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ORD = r"(?:st|nd|rd|th)?"
NEGATION = re.compile(
    r"\b(no|not|avoid|skip|don'?t|do not|without|hate|dislike|except|exclude|nothing|never|remove)\b[^.!?,;]{0,25}$"
)
ANYTHING = re.compile(
    r"\b(anything|everything|no preference|no preferences|doesn'?t matter|don'?t mind|surprise me|all of them|any is fine|whatever|not sure|no specific)\b"
)

GROUP_PATTERNS = [
    ("solo", re.compile(r"\b(solo|alone|by myself|just me|only me|myself only|single traveller)\b")),
    (
        "couple",
        re.compile(
            r"\b(couple|my wife|my husband|my partner|my spouse|honeymoon|with wife|with husband|me and my (wife|husband|fiance|fiancee))\b"
        ),
    ),
    (
        "family",
        re.compile(
            r"\b(family(?!\s+(fun|friendly))|families|with my (kids|children|parents)|with kids|with children)\b"
        ),
    ),
    ("friends", re.compile(r"\b(friends|buddies|colleagues|classmates|cousins|group)\b")),
]
PACE_PATTERNS = [
    (
        "relaxed",
        re.compile(r"\b(relaxed|relaxing|slow|chill|easy going|easy-going|laid[- ]back|leisurely|not rushed|calm)\b"),
    ),
    (
        "packed",
        re.compile(
            r"\b(packed|fast|busy|hectic|as much as possible|see everything|lots of places|many places|full days?)\b"
        ),
    ),
    ("balanced", re.compile(r"\b(balanced|moderate|normal|medium|average)\b")),
]
NEED_PATTERNS = [
    ("indoor", re.compile(r"\b(indoors?|avoid (the )?(heat|sun)|air[- ]?conditioned|too hot)\b")),
    ("late_start", re.compile(r"\b(late start|start late|sleep in|not early|wake up late|late mornings?)\b")),
    ("kids", re.compile(r"\b(kids?|child|children|toddlers?|baby|babies)\b")),
    (
        "elderly",
        re.compile(
            r"\b(elderly|seniors?|grandparents?|grandma|grandpa|old parents|aged parents|can'?t walk much|cannot walk much|wheelchair)\b"
        ),
    ),
    (
        "no_stay",
        re.compile(
            r"\b(no hotel|don'?t need (a )?hotel|without hotel|staying with (relatives|family|friends)|we live (in|here|there)|i live (in|here|there)|already have (a )?(hotel|stay|accommodation)|accommodation (is )?sorted|locals?)\b"
        ),
    ),
]
CHANGE_RE = re.compile(
    r"\b(change|update|edit|modify|different)\b\s*(the|my)?\s*(budget|dates?|start|days?|duration|city|destination|group|people|interests?|pace)\b"
)
CHANGE_FIELD = {
    "budget": "budget",
    "date": "start_date",
    "dates": "start_date",
    "start": "start_date",
    "day": "days",
    "days": "days",
    "duration": "days",
    "city": "city",
    "destination": "city",
    "group": "group_type",
    "people": "group_type",
    "interest": "interests",
    "interests": "interests",
    "pace": "pace",
}
AFFIRM_RE = re.compile(
    r"\b(yes|yeah|yep|sure|ok|okay|go ahead|create( my)? plans?|generate|make( the| my)? plans?|let'?s go|sounds good|looks good|perfect|done|confirm)\b"
)


def to_int(word: str) -> int:
    return int(word) if word.isdigit() else NUM_WORDS.get(word, 0)


def normalise(text: str) -> str:
    t = text.lower().replace("’", "'").replace("–", "-")
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)  # 50,000 -> 50000
    t = re.sub(r"(\d),(?=\d{2},\d{3}\b)", r"\1", t)  # 1,50,000 -> 150000 (lakh style)
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)
    return t


class Text:
    """Message text where matched parts are blanked out so they aren't parsed twice."""

    def __init__(self, text: str):
        self.s = normalise(text)

    def take(self, m: re.Match) -> None:
        self.s = self.s[: m.start()] + " " * (m.end() - m.start()) + self.s[m.end() :]


def safe_date(year: int, month: int, day: int) -> dt.date | None:
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def future_date(month: int, day: int, today: dt.date, year: int | None = None) -> dt.date | None:
    if year:
        return safe_date(year if year > 100 else 2000 + year, month, day)
    d = safe_date(today.year, month, day)
    if d and d < today:
        d = safe_date(today.year + 1, month, day)
    return d


def next_weekday(today: dt.date, weekday: int, strictly_after: bool = True) -> dt.date:
    delta = (weekday - today.weekday()) % 7
    if delta == 0 and strictly_after:
        delta = 7
    return today + dt.timedelta(days=delta)


# ----------------------------------------------------------------------------- rule parsers
def parse_dates(t: Text, today: dt.date) -> dict:
    out: dict = {}
    s = t.s
    # "in 5 days" / "in 2 weeks" -> start date (must run before the "N days" duration rule)
    m = re.search(rf"\b(?:in|after)\s+{NUM}\s+(days?|weeks?)\b", s)
    if m:
        n = to_int(m.group(1))
        out["start_date"] = today + dt.timedelta(days=n * (7 if m.group(2).startswith("week") else 1))
        t.take(m)
        return out
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", t.s)
    if m:
        d = safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            out["start_date"] = d
            t.take(m)
            return out
    # range: "20-22 dec", "20 to 22 december"
    m = re.search(rf"\b(\d{{1,2}}){ORD}\s*(?:-|to|till|until)\s*(\d{{1,2}}){ORD}\s*(?:of\s+)?{MONTH_RE}\b", t.s)
    if m:
        d = future_date(MONTHS[m.group(3)], int(m.group(1)), today)
        end = int(m.group(2))
        if d and end >= d.day:
            out["start_date"], out["days"] = d, min(MAX_DAYS, end - d.day + 1)
            t.take(m)
            return out
    m = re.search(rf"\b(\d{{1,2}}){ORD}\s*(?:of\s+)?{MONTH_RE}\b(?:\s*,?\s*(20\d\d))?", t.s)
    if m:
        d = future_date(MONTHS[m.group(2)], int(m.group(1)), today, int(m.group(3)) if m.group(3) else None)
        if d:
            out["start_date"] = d
            t.take(m)
            return out
    m = re.search(rf"\b{MONTH_RE}\s+(\d{{1,2}}){ORD}\b(?:\s*,?\s*(20\d\d))?", t.s)
    if m:
        d = future_date(MONTHS[m.group(1)], int(m.group(2)), today, int(m.group(3)) if m.group(3) else None)
        if d:
            out["start_date"] = d
            t.take(m)
            return out
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t.s)  # day/month as used in Pakistan
    if m:
        d = future_date(int(m.group(2)), int(m.group(1)), today, int(m.group(3)) if m.group(3) else None)
        if d:
            out["start_date"] = d
            t.take(m)
            return out
    for pattern, delta in ((r"\bday after tomorrow\b", 2), (r"\btomorrow\b", 1), (r"\b(today|tonight)\b", 0)):
        m = re.search(pattern, t.s)
        if m:
            out["start_date"] = today + dt.timedelta(days=delta)
            t.take(m)
            return out
    m = re.search(r"\b(this |next |coming )?weekend\b", t.s)
    if m:
        out["start_date"] = next_weekday(today, 5, strictly_after=False)
        out["weekend"] = True
        t.take(m)
        return out
    m = re.search(r"\bnext week\b", t.s)
    if m:
        out["start_date"] = next_weekday(today, 0)
        t.take(m)
        return out
    m = re.search(r"\b(?:on |this |next |coming )?(" + "|".join(WEEKDAYS) + r")\b", t.s)
    if m:
        out["start_date"] = next_weekday(today, WEEKDAYS.index(m.group(1)), strictly_after=True)
        t.take(m)
    return out


def parse_days(t: Text, awaiting: str) -> dict:
    m = re.search(rf"\b{NUM}\s*(?:-|\s)?\s*(days?|nights?)\b", t.s)
    if m:
        n = to_int(m.group(1)) + (1 if m.group(2).startswith("night") else 0)
        t.take(m)
        return {"days": n}
    m = re.search(r"\b(a|one|1)\s*week\b", t.s)
    if m:
        t.take(m)
        return {"days": 7}
    m = re.search(r"\bday trip\b", t.s)
    if m:
        t.take(m)
        return {"days": 1}
    if awaiting == "days":
        m = re.search(rf"^\s*{NUM}\s*$", t.s)
        if m:
            t.take(m)
            return {"days": to_int(m.group(1))}
    return {}


MONEY_UNIT = {
    "k": 1_000,
    "thousand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "lacs": 100_000,
    "m": 1_000_000,
    "million": 1_000_000,
}


def parse_budget(t: Text, awaiting: str, weak: bool = True) -> dict:
    """Strong = has a currency or unit (50k, Rs 40000). Weak = a bare number."""
    s = t.s
    patterns = [
        r"(?:rs\.?|pkr|rupees?)\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|million|m)?\b",
        r"\b(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|million)\b(?:\s*(?:rs|pkr|rupees?))?",
        r"\b(\d+(?:\.\d+)?)\s*(?:rs|pkr|rupees?)\b()",
        r"\bbudget\s*(?:is|of|around|about|:|=|max|maximum|upto|up to)?\s*(?:rs\.?|pkr)?\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?)?\b",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            value = float(m.group(1)) * MONEY_UNIT.get((m.group(2) or "").strip(), 1)
            if value >= 100:
                tail = s[m.end() : m.end() + 25]
                per_person = bool(re.search(r"\b(per person|each|per head|pp|a head)\b", tail))
                t.take(m)
                return {"budget": int(value), "budget_per_person": per_person}
    if not weak:
        return {}
    if awaiting == "budget":
        m = re.search(r"\b(\d{3,7})\b", s)
        if m:
            t.take(m)
            return {"budget": int(m.group(1)), "budget_per_person": False}
    m = re.search(r"\b(\d{4,7})\b", s)
    if m and not 2020 <= int(m.group(1)) <= 2040:
        t.take(m)
        return {"budget": int(m.group(1)), "budget_per_person": False}
    return {}


def parse_group(t: Text, awaiting: str) -> dict:
    out: dict = {}
    s = t.s
    for gtype, rx in GROUP_PATTERNS:
        if rx.search(s):
            out["group_type"] = gtype
            break
    adults = re.search(
        rf"\b{NUM}\s*(people|persons|person|adults|members|travell?ers|pax|of us|guys|girls|friends|family members)\b",
        s,
    )
    kids = re.search(rf"\b{NUM}\s*(kids|children|child)\b", s)
    fam = re.search(rf"\bfamily of\s*{NUM}\b", s)
    we_are = re.search(rf"\bwe are\s*{NUM}\b", s)
    size = 0
    if fam:
        size = to_int(fam.group(1))
        t.take(fam)
    elif we_are:
        size = to_int(we_are.group(1))
        t.take(we_are)
    else:
        if adults:
            size += to_int(adults.group(1))
            if adults.group(2) == "friends" and "group_type" not in out:
                out["group_type"] = "friends"
        if kids:
            size += to_int(kids.group(1))
            out.setdefault("group_type", "family")
    if not size and awaiting in ("group_type", "group_size"):
        m = re.search(rf"^\s*{NUM}\s*$", t.s)
        if m:
            size = to_int(m.group(1))
    for m in (adults, kids):
        if m:
            t.take(m)
    if size:
        out["group_size"] = size
        if size == 1:
            out.setdefault("group_type", "solo")
    if out.get("group_type") == "couple":
        out.setdefault("group_size", 2)
    if out.get("group_type") == "solo":
        out.setdefault("group_size", 1)
    return out


def find_city(t: Text, cat: Catalog) -> str | None:
    s = t.s
    names: dict[str, str] = {}
    for cid, c in cat.cities.items():
        names[c["name"].lower()] = cid
        for a in c["aliases"]:
            names[a.lower()] = cid
    hits: list[tuple[int, str, bool]] = []  # (position, city, is_destination)
    for name, cid in names.items():
        for m in re.finditer(rf"\b{re.escape(name)}\b", s):
            before = s[max(0, m.start() - 12) : m.start()]
            dest = bool(re.search(r"\b(to|in|visit|visiting|explore|see|around)\s*$", before))
            src = bool(re.search(r"\bfrom\s*$", before))
            if not src:
                hits.append((m.start(), cid, dest))
    if not hits:  # small typos: "lahre", "karachii"
        for word in re.findall(r"[a-z]{5,}", s):
            close = difflib.get_close_matches(word, list(names), n=1, cutoff=0.8)
            if close:
                hits.append((s.find(word), names[close[0]], False))
    if not hits:
        return None
    dest = [h for h in hits if h[2]]
    return (dest or sorted(hits))[-1 if not dest else 0][1]


FOREIGN_RE = re.compile(
    r"\b(foreigners?|foreign (national|tourist|visitor|passport|citizen)s?|from abroad|overseas (visitor|tourist)s?"
    r"|international (tourist|visitor)s?|not pakistani|non[- ]pakistani)\b"
)
LOCAL_RE = re.compile(
    r"\b(pakistani (citizens?|nationals?|passport)|(i am|i'm|we are|we're) pakistanis?|local tourists?)\b"
)
CAR_RE = re.compile(r"\b(by car|own car|our car|my car|drive|driving|self[- ]drive)\b")
BUS_RE = re.compile(r"\b(by bus|bus|daewoo|coach)\b")


def find_home_city(t: Text, cat: Catalog) -> str | None:
    """City the travellers start from: "from Karachi", "coming from lhr"."""
    for cid, c in cat.cities.items():
        for name in {c["name"].lower(), *(a.lower() for a in c["aliases"])}:
            if re.search(rf"\b(from|coming from|starting from|leaving from)\s+{re.escape(name)}\b", t.s):
                return cid
    return None


def find_interests(t: Text, cat: Catalog) -> tuple[list[str], list[str]]:
    want, avoid = [], []
    s = t.s
    for iid, info in cat.interests.items():
        words = sorted({info["label"].lower(), *info["keywords"]}, key=len, reverse=True)
        for w in words:
            m = re.search(rf"\b{re.escape(w)}\b", s)
            if m:
                (avoid if NEGATION.search(s[: m.start()]) else want).append(iid)
                break
    return want, avoid


def find_excluded_places(t: Text, cat: Catalog, city: str | None) -> list[str]:
    s = t.s
    if not re.search(r"\b(no|not|avoid|skip|don'?t|without|exclude|remove)\b", s):
        return []
    pools = [cat.pois(city)] if city else list(cat.pois_by_city.values())
    out = []
    for pool in pools:
        for p in pool:
            name = re.sub(r"^the ", "", p["name"].lower())
            m = re.search(rf"\b{re.escape(name)}\b", s)
            if m and NEGATION.search(s[: m.start()]):
                out.append(p["id"])
                t.take(m)  # so "skip Lahore Zoo" doesn't also exclude the zoo interest
    return out


def extract_rules(message: str, cat: Catalog, today: dt.date, awaiting: str = "", city_hint: str | None = None) -> dict:
    t = Text(message)
    out: dict = {}
    m = CHANGE_RE.search(t.s)
    if m:
        out["change"] = CHANGE_FIELD[m.group(3)]
    out.update(parse_budget(t, awaiting, weak=False))
    out.update(parse_dates(t, today))
    days = parse_days(t, awaiting)
    if days and "days" not in out:
        out.update(days)
    out.update(parse_group(t, awaiting))
    if "budget" not in out:
        out.update(parse_budget(t, awaiting, weak=True))
    city = find_city(t, cat)
    if city:
        out["city"] = city
    excluded = find_excluded_places(t, cat, city or city_hint)
    if excluded:
        out["excluded_places"] = excluded
    want, avoid = find_interests(t, cat)
    if want:
        out["interests"] = want
    if avoid:
        out["exclusions"] = avoid
    if want or avoid or (awaiting == "interests" and ANYTHING.search(t.s)):
        out["interests_answered"] = True
    for pace, rx in PACE_PATTERNS:
        if rx.search(t.s):
            out["pace"] = pace
            break
    needs = [n for n, rx in NEED_PATTERNS if rx.search(t.s)]
    if needs:
        out["needs"] = needs
    home = find_home_city(t, cat)
    if home and home != out.get("city"):
        out["home_city"] = home
    if FOREIGN_RE.search(t.s):
        out["traveller_type"] = "foreign"
    elif LOCAL_RE.search(t.s):
        out["traveller_type"] = "local"
    if CAR_RE.search(t.s):
        out["travel_mode"] = "car"
    elif BUS_RE.search(t.s):
        out["travel_mode"] = "bus"
    if AFFIRM_RE.search(t.s):
        out["affirm"] = True
        if awaiting == "interests":
            out["interests_answered"] = True
    return out


# ----------------------------------------------------------------------------- LLM layer
def clean_llm(raw: dict | None, cat: Catalog, today: dt.date) -> dict:
    """Keep only valid values from the model's answer."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    city = str(raw.get("city") or "").strip().lower()
    for cid, c in cat.cities.items():
        if city and (city == cid or city == c["name"].lower() or city in c["aliases"]):
            out["city"] = cid
    try:
        d = dt.date.fromisoformat(str(raw.get("start_date")))
        if d >= today:
            out["start_date"] = d
    except ValueError:
        pass
    if isinstance(raw.get("days"), int) and 1 <= raw["days"] <= 30:
        out["days"] = raw["days"]
    if isinstance(raw.get("budget_pkr"), int) and raw["budget_pkr"] >= 100:
        out["budget"] = raw["budget_pkr"]
        out["budget_per_person"] = False
    if raw.get("group_type") in ("solo", "couple", "family", "friends"):
        out["group_type"] = raw["group_type"]
    if isinstance(raw.get("group_size"), int) and 1 <= raw["group_size"] <= 30:
        out["group_size"] = raw["group_size"]
    want = [i for i in raw.get("interests") or [] if i in cat.interests]
    avoid = [i for i in raw.get("avoid") or [] if i in cat.interests]
    if want:
        out["interests"] = want
    if avoid:
        out["exclusions"] = avoid
    if want or avoid:
        out["interests_answered"] = True
    if raw.get("pace") in ("relaxed", "balanced", "packed"):
        out["pace"] = raw["pace"]
    return out


def should_ask_llm(message: str, found: dict) -> bool:
    words = len(message.split())
    useful = {k for k in found if k not in ("affirm", "change", "budget_per_person")}
    return words >= 6 or (words >= 2 and not useful)


def extract(
    message: str, cat: Catalog, today: dt.date, llm: LLM, awaiting: str = "", city_hint: str | None = None
) -> dict:
    found = extract_rules(message, cat, today, awaiting, city_hint)
    if should_ask_llm(message, found):
        ctx = {
            "today": today.isoformat(),
            "cities": list(cat.cities),
            "interests": list(cat.interests),
            "awaiting": awaiting,
        }
        for key, value in clean_llm(llm.extract(message, ctx), cat, today).items():
            found.setdefault(key, value)  # rules win; the LLM only fills gaps
    return found
