"""Conversation manager + clarification handler."""

import datetime as dt

import pytest

from app.agents.intake.conversation import greeting, handle_turn
from app.schemas.preferences import TripPreferences
from app.services.llm import NoLLM

TODAY = dt.date(2026, 10, 13)


def chat(catalog, messages, prefs=None, awaiting="city"):
    prefs = prefs or TripPreferences()
    turn = None
    for m in messages:
        turn = handle_turn(prefs, awaiting, catalog, TODAY, NoLLM(), text=m)
        prefs, awaiting = turn.preferences, turn.awaiting
    return turn


def test_greeting_offers_cities(catalog):
    t = greeting("Dania Khan", catalog)
    assert t.reply.startswith("Hi Dania")
    assert set(t.suggestions) == {c["name"] for c in catalog.cities.values()}
    assert {"Hunza", "Skardu", "Kalam"} <= set(t.suggestions)


def test_asks_for_missing_fields_in_order(catalog):
    t = chat(catalog, ["Lahore"])
    assert t.awaiting == "days"
    t = chat(catalog, ["Lahore", "3 days"])
    assert t.awaiting == "start_date"
    t = chat(catalog, ["Lahore", "3 days", "tomorrow"])
    assert t.awaiting == "group_type"
    t = chat(catalog, ["Lahore", "3 days", "tomorrow", "Family"])
    assert t.awaiting == "group_size"
    t = chat(catalog, ["Lahore", "3 days", "tomorrow", "Family", "5 people"])
    assert t.awaiting == "budget" and len(t.suggestions) == 3
    t = chat(catalog, ["Lahore", "3 days", "tomorrow", "Family", "5 people", "100k"])
    assert t.awaiting == "interests"
    t = chat(catalog, ["Lahore", "3 days", "tomorrow", "Family", "5 people", "100k", "Anything"])
    assert t.ready and t.awaiting == "confirm"


def test_one_long_message_then_confirm(catalog):
    t = chat(catalog, ["3 days in Karachi from 20 dec with my wife, budget 60k, food and nature", "Create plans"])
    assert t.ready and t.action == "generate"
    assert t.preferences.city == "karachi" and t.preferences.group_size == 2


def test_budget_too_low_is_questioned(catalog):
    t = chat(catalog, ["Lahore, 4 days from tomorrow, family of 6, budget 5000"])
    assert t.awaiting == "budget" and "minimum" in t.reply
    assert t.preferences.budget is None


def test_past_date_is_questioned(catalog):
    prefs = TripPreferences(city="lahore", days=2)
    t = handle_turn(prefs, "start_date", catalog, TODAY, NoLLM(), text="2026-01-01")
    assert "already passed" in t.reply and t.preferences.start_date is None


def test_unknown_city(catalog):
    t = chat(catalog, ["I want to go to Quetta"])
    assert "Lahore" in t.reply and t.awaiting == "city"


@pytest.mark.parametrize(
    "text,city",
    [
        ("3 days in Hunza", "hunza"),
        ("trip to karimabad", "hunza"),
        ("going to skardo", "skardu"),
        ("Mingora for the weekend", "swat"),
        ("malam jabba", "swat"),
        ("Kalam valley", "kalam"),
        ("ushu forest and mahodand", "kalam"),
        ("peshawer food", "peshawar"),
        ("multaan shrines", "multan"),
        ("muree in winter", "murree"),
        ("bhawalpur palaces", "bahawalpur"),
    ],
)
def test_new_cities_and_spellings(catalog, text, city):
    assert chat(catalog, [text]).preferences.city == city


def test_home_city_foreign_and_car(catalog):
    t = chat(catalog, ["We are foreigners driving from Lahore to Hunza for 4 days by car"])
    p = t.preferences
    assert p.city == "hunza" and p.home_city == "lahore"
    assert p.traveller_type == "foreign" and p.travel_mode == "car"
    assert "travelling from Lahore" in t.reply


def test_from_city_is_not_the_destination(catalog):
    p = chat(catalog, ["from Karachi to Skardu"]).preferences
    assert p.city == "skardu" and p.home_city == "karachi"


def test_button_patch_and_text_share_one_state(catalog):
    prefs = TripPreferences()
    t = handle_turn(prefs, "city", catalog, TODAY, NoLLM(), patch={"city": "islamabad", "days": 2})
    t = handle_turn(t.preferences, t.awaiting, catalog, TODAY, NoLLM(), text="next saturday, solo, 30k")
    assert t.preferences.city == "islamabad" and t.preferences.group_type == "solo"
    assert t.awaiting == "interests"


def test_change_request(catalog):
    t = chat(catalog, ["3 days in Lahore from tomorrow solo 50k anything", "change budget"])
    assert t.awaiting == "budget" and t.reply.startswith("What is your total budget")


def test_gibberish_gets_the_question_again(catalog):
    t = chat(catalog, ["Lahore", "asdfgh"])
    assert t.reply.startswith("Sorry") and t.awaiting == "days"
