"""Preference extractor: rule layer + LLM layer."""

import datetime as dt

import pytest

from app.agents.intake.extractor import extract, extract_rules
from app.services.llm import FakeLLM, NoLLM

TODAY = dt.date(2026, 10, 13)  # a Tuesday


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3 days in Lahore", {"city": "lahore", "days": 3}),
        ("trip to karachi for a week", {"city": "karachi", "days": 7}),
        ("from Karachi to Islamabad", {"city": "islamabad"}),
        ("lahre", {"city": "lahore"}),
        ("2 nights in isb", {"city": "islamabad", "days": 3}),
    ],
)
def test_city_and_days(catalog, text, expected):
    found = extract_rules(text, catalog, TODAY)
    for k, v in expected.items():
        assert found.get(k) == v, (text, found)


@pytest.mark.parametrize(
    "text,budget",
    [
        ("budget 50k", 50_000),
        ("Rs 40,000", 40_000),
        ("around 1.5 lakh", 150_000),
        ("we have 75000 rupees", 75_000),
        ("PKR 2 lakh", 200_000),
    ],
)
def test_budget(catalog, text, budget):
    assert extract_rules(text, catalog, TODAY)["budget"] == budget


def test_budget_per_person(catalog):
    found = extract_rules("20k per person", catalog, TODAY)
    assert found["budget"] == 20_000 and found["budget_per_person"] is True


def test_bare_number_is_budget_only_when_asked(catalog):
    assert "budget" not in extract_rules("3", catalog, TODAY, awaiting="days")
    assert extract_rules("45000", catalog, TODAY, awaiting="budget")["budget"] == 45_000


@pytest.mark.parametrize(
    "text,date",
    [
        ("tomorrow", dt.date(2026, 10, 14)),
        ("next friday", dt.date(2026, 10, 16)),
        ("this weekend", dt.date(2026, 10, 17)),
        ("20 dec", dt.date(2026, 12, 20)),
        ("December 5th", dt.date(2026, 12, 5)),
        ("25/12", dt.date(2026, 12, 25)),
        ("2027-01-10", dt.date(2027, 1, 10)),
        ("5 jan", dt.date(2027, 1, 5)),  # already passed this year -> next year
        ("in 2 weeks", dt.date(2026, 10, 27)),
    ],
)
def test_dates(catalog, text, date):
    assert extract_rules(text, catalog, TODAY)["start_date"] == date


def test_date_range_sets_days(catalog):
    found = extract_rules("20-22 december", catalog, TODAY)
    assert found["start_date"] == dt.date(2026, 12, 20) and found["days"] == 3


def test_lakh_is_not_a_date(catalog):
    found = extract_rules("1.5 lakh", catalog, TODAY)
    assert "start_date" not in found and found["budget"] == 150_000


@pytest.mark.parametrize(
    "text,gtype,size",
    [
        ("just me", "solo", 1),
        ("with my wife", "couple", 2),
        ("family of 5", "family", 5),
        ("2 adults and 3 kids", "family", 5),
        ("6 friends", "friends", 6),
    ],
)
def test_group(catalog, text, gtype, size):
    found = extract_rules(text, catalog, TODAY)
    assert found.get("group_type") == gtype and found.get("group_size") == size, found


def test_interests_and_negation(catalog):
    found = extract_rules("we love history and food but no shopping", catalog, TODAY)
    assert set(found["interests"]) == {"history", "food"}
    assert found["exclusions"] == ["shopping"]


def test_family_fun_chip_is_not_a_group(catalog):
    found = extract_rules("Family fun", catalog, TODAY, awaiting="interests")
    assert found["interests"] == ["family"] and "group_type" not in found


def test_skip_a_place_does_not_remove_an_interest(catalog):
    found = extract_rules("skip Lahore Zoo", catalog, TODAY, city_hint="lahore")
    assert found["excluded_places"] == ["lhr_zoo"]
    assert "exclusions" not in found


def test_needs_and_pace(catalog):
    found = extract_rules("relaxed trip, my grandparents are coming and we want indoor places", catalog, TODAY)
    assert found["pace"] == "relaxed"
    assert {"elderly", "indoor"} <= set(found["needs"])


def test_llm_fills_gaps_but_rules_win(catalog):
    llm = FakeLLM(
        {
            "city": "Karachi",
            "start_date": None,
            "days": 9,
            "budget_pkr": 60000,
            "group_type": "couple",
            "group_size": None,
            "interests": ["food", "nonsense"],
            "avoid": [],
            "pace": None,
        }
    )
    found = extract("thinking about a seaside break with my better half for 4 days", catalog, TODAY, llm)
    assert found["days"] == 4  # from the rules, not the LLM's 9
    assert found["city"] == "karachi" and found["budget"] == 60000 and found["group_type"] == "couple"
    assert found["interests"] == ["food"]  # invalid values are dropped


def test_works_without_llm(catalog):
    found = extract("Lahore for 2 days", catalog, TODAY, NoLLM())
    assert found["city"] == "lahore" and found["days"] == 2
