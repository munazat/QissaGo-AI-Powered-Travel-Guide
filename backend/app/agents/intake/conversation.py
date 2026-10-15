"""Conversation manager: one chat turn = extract -> merge -> check -> reply.

It is a pure function (no database), so it is easy to test. The API stores the
returned preferences and messages in PostgreSQL.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from app.schemas.preferences import MAX_DAYS, TripPreferences
from app.services.catalog import Catalog
from app.services.llm import LLM

from .clarifier import ask, money, next_question, summary
from .extractor import extract

FEWER_DAYS = re.compile(r"\b(fewer days|less days|shorter( trip)?|reduce (the )?days)\b")


@dataclass
class Turn:
    preferences: TripPreferences
    reply: str
    suggestions: list[str] = field(default_factory=list)
    awaiting: str = ""
    ready: bool = False
    action: str = ""  # "generate" when the user confirmed
    extracted: dict = field(default_factory=dict)


def greeting(name: str, cat: Catalog) -> Turn:
    first = (name or "").split(" ")[0]
    q = ask("city", TripPreferences(), cat)
    hello = f"Hi {first}. " if first else "Hi. "
    return Turn(TripPreferences(), hello + "Tell me about your trip, or start with the city.", q.suggestions, "city")


def apply_patch(prefs: TripPreferences, patch: dict) -> list[str]:
    changed = []
    for key, value in patch.items():
        if value is None:
            continue
        setattr(prefs, key, value)
        changed.append(key)
        if key == "interests":
            prefs.interests_answered = True
        if key == "group_type" and value in ("solo", "couple"):
            prefs.group_size = 1 if value == "solo" else 2
        if key == "city":
            prefs.excluded_places = []
    return changed


def merge(prefs: TripPreferences, found: dict) -> list[str]:
    """Apply what the extractor found. Returns the names of fields that changed."""
    changed = []
    if "city" in found and found["city"] != prefs.city:
        prefs.city, prefs.excluded_places = found["city"], []
        changed.append("city")
    if "start_date" in found:
        prefs.start_date = found["start_date"]
        changed.append("start_date")
    if "days" in found:
        prefs.days = max(1, min(MAX_DAYS, found["days"]))
        changed.append("days")
    elif found.get("weekend") and prefs.days is None:
        prefs.days = 2
        changed.append("days")
    if "group_type" in found:
        gt = found["group_type"]
        if gt in ("family", "friends") and prefs.group_type in ("solo", "couple") and "group_size" not in found:
            prefs.group_size = None  # old size belonged to the old group type
        prefs.group_type = gt
        if gt == "solo":
            prefs.group_size = found.get("group_size", 1)
        if gt == "couple":
            prefs.group_size = found.get("group_size", 2)
        changed.append("group_type")
    if "group_size" in found:
        prefs.group_size = found["group_size"]
        changed.append("group_size")
    if "budget" in found:
        budget = found["budget"]
        if found.get("budget_per_person"):
            budget *= prefs.size()
        prefs.budget = budget
        changed.append("budget")
    if found.get("exclusions"):
        prefs.exclusions = sorted(set(prefs.exclusions) | set(found["exclusions"]))
        prefs.interests = [i for i in prefs.interests if i not in prefs.exclusions]
        changed.append("exclusions")
    if found.get("interests"):
        new = [i for i in found["interests"] if i not in found.get("exclusions", [])]
        prefs.exclusions = [e for e in prefs.exclusions if e not in new]
        prefs.interests = list(dict.fromkeys(prefs.interests + new))
        changed.append("interests")
    if found.get("interests_answered"):
        prefs.interests_answered = True
    if found.get("excluded_places"):
        prefs.excluded_places = sorted(set(prefs.excluded_places) | set(found["excluded_places"]))
        changed.append("excluded_places")
    if found.get("needs"):
        prefs.needs = sorted(set(prefs.needs) | set(found["needs"]))
        changed.append("needs")
        if "elderly" in found["needs"] and "pace" not in found:
            prefs.pace = "relaxed"
    if "pace" in found:
        prefs.pace = found["pace"]
        changed.append("pace")
    for key in ("home_city", "traveller_type", "travel_mode"):
        if key in found and getattr(prefs, key) != found[key]:
            setattr(prefs, key, found[key])
            changed.append(key)
    return changed


def acknowledge(prefs: TripPreferences, changed: list[str], cat: Catalog) -> str:
    bits = []
    if "city" in changed and prefs.city in cat.cities:
        bits.append(cat.cities[prefs.city]["name"])
    if "days" in changed and prefs.days:
        bits.append(f"{prefs.days} {'day' if prefs.days == 1 else 'days'}")
    if "start_date" in changed and prefs.start_date:
        bits.append(f"from {prefs.start_date:%a %d %b}")
    if "home_city" in changed and prefs.home_city in cat.cities:
        bits.append(f"travelling from {cat.cities[prefs.home_city]['name']}")
    if "traveller_type" in changed:
        bits.append("foreign visitor" if prefs.traveller_type == "foreign" else "Pakistani visitor")
    if "travel_mode" in changed:
        bits.append("by car" if prefs.travel_mode == "car" else "by bus")
    if ("group_size" in changed or "group_type" in changed) and (prefs.group_size or prefs.group_type):
        n = prefs.group_size
        if prefs.group_type == "solo" or not n:
            bits.append(prefs.group_type or "")
        else:
            bits.append(f"{n} {'person' if n == 1 else 'people'}")
    if "budget" in changed and prefs.budget:
        bits.append(money(prefs.budget))
    if "interests" in changed and prefs.interests:
        bits.append(", ".join(cat.interests[i]["label"].lower() for i in prefs.interests if i in cat.interests))
    if "exclusions" in changed and prefs.exclusions:
        bits.append(
            "no " + ", ".join(cat.interests[i]["label"].lower() for i in prefs.exclusions if i in cat.interests)
        )
    if "excluded_places" in changed and prefs.excluded_places:
        bits.append(f"skipping {len(prefs.excluded_places)} {'place' if len(prefs.excluded_places) == 1 else 'places'}")
    if "pace" in changed:
        bits.append(f"{prefs.pace} pace")
    return ("Got it: " + ", ".join(bits) + ". ") if bits else ""


def handle_turn(
    prefs: TripPreferences,
    awaiting: str,
    cat: Catalog,
    today: dt.date,
    llm: LLM,
    text: str | None = None,
    patch: dict | None = None,
) -> Turn:
    prefs = prefs.model_copy(deep=True)
    was_ready = awaiting == "confirm"
    changed: list[str] = []
    found: dict = {}

    if patch:
        changed += apply_patch(prefs, patch)
    if text and text.strip():
        found = extract(text, cat, today, llm, awaiting, prefs.city)
        if FEWER_DAYS.search(text.lower()):
            found["change"] = "days"
        changed += merge(prefs, found)

    # "change budget" -> ask about that field directly
    if found.get("change") and found["change"] not in changed:
        q = ask(found["change"], prefs, cat)
        return Turn(prefs, q.text, q.suggestions, q.field, False, "", found)

    q = next_question(prefs, cat, today)
    ack = acknowledge(prefs, changed, cat)
    if q:
        if not changed and text:
            if awaiting == "city" and not prefs.city:
                names = ", ".join(c["name"] for c in cat.cities.values())
                return Turn(
                    prefs,
                    f"For now I can plan trips to {names}. Which one would you like?",
                    q.suggestions,
                    q.field,
                    False,
                    "",
                    found,
                )
            return Turn(prefs, "Sorry, I did not catch that. " + q.text, q.suggestions, q.field, False, "", found)
        return Turn(prefs, ack + q.text, q.suggestions, q.field, False, "", found)

    # Everything needed is known
    if was_ready and found.get("affirm") and not changed:
        return Turn(prefs, "Creating your plans now.", [], "confirm", True, "generate", found)
    reply = ack + "Here is your trip: " + summary(prefs, cat) + " Shall I create your plans?"
    return Turn(prefs, reply, ["Create plans", "Change budget", "Change dates"], "confirm", True, "", found)
