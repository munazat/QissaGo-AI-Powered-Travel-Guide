"""Orchestrator agent: runs the specialist agents in order, then scores and ranks
the three finished plans (match score out of 100)."""

from __future__ import annotations

import time

from app.schemas.preferences import TripPreferences
from app.services.catalog import Catalog

from .base import Agent
from .budget import BudgetAgent
from .destination import VARIANTS, DestinationAgent
from .enrichment import EnrichmentAgent
from .intake.agent import IntakeAgent
from .scheduling import SchedulingAgent
from .validator import ValidatorAgent
from .weather import WeatherAgent

PIPELINE = (IntakeAgent, WeatherAgent, DestinationAgent, BudgetAgent, SchedulingAgent, ValidatorAgent, EnrichmentAgent)


def plan_stats(days: list[dict], prefs: dict, totals: dict, all_pois: list[dict]) -> tuple[dict, int]:
    """Stats shown on each plan + the match score (0-100)."""
    stops = [s for d in days for s in d["items"] if s["kind"] == "stop"]
    interests = prefs["interests"]
    covered = [i for i in interests if any(i in s["tags"] for s in stops)]
    coverage = 1.0 if not interests else len(covered) / len(interests)
    matching = (sum(1 for s in stops if set(s["tags"]) & set(interests)) / len(stops)) if (stops and interests) else 1.0
    interest_part = 0.5 * coverage + 0.5 * matching

    over = max(0, -totals["left"]) / max(1, totals["budget"])
    budget_fit = 1.0 if totals["within"] else max(0.0, 1 - over * 3)

    outdoor = [s for s in stops if s["outdoor"]]
    bad = [s for s in outdoor if s.get("weather_note", "").startswith("Rain")]
    weather_fit = 1.0 if not outdoor else 1 - len(bad) / len(outdoor)

    legs = [s["leg"]["km"] for s in stops if s.get("leg")]
    avg_km = sum(legs) / len(legs) if legs else 0
    travel_fit = max(0.0, min(1.0, (15 - avg_km) / 12))

    must = [p for p in all_pois if p["priority"] == 3]
    must_fit = (sum(1 for s in stops if s["priority"] == 3) / min(len(must), len(stops))) if (must and stops) else 1.0
    must_fit = min(1.0, must_fit)

    target = prefs["days"] * prefs["stops_per_day"]
    fullness = min(1.0, len(stops) / target) if target else 1.0

    score = round(
        35 * interest_part + 20 * budget_fit + 15 * fullness + 10 * weather_fit + 10 * travel_fit + 10 * must_fit
    )
    stats = {
        "stops": len(stops),
        "km": round(sum(legs), 1),
        "interest_coverage": round(coverage * 100),
        "covered": covered,
        "weather_fit": round(weather_fit * 100),
        "must_see": sum(1 for s in stops if s["priority"] == 3),
    }
    return stats, score


class Orchestrator:
    name = "Orchestrator Agent"

    def run(self, prefs: TripPreferences, catalog: Catalog) -> dict:
        t0 = time.perf_counter()
        state: dict = {"request": prefs, "catalog": catalog, "trace": []}
        agent: Agent
        for agent_cls in PIPELINE:
            agent = agent_cls()
            agent(state)

        p = state["prefs"]
        plans = []
        for v in VARIANTS:
            sch = state["schedules"][v["id"]]
            stats, score = plan_stats(sch["days"], p, sch["totals"], catalog.pois(p["city_id"]))
            first_img = next(
                (s["image"] for d in sch["days"] for s in d["items"] if s["kind"] == "stop" and s.get("image")),
                p["city"]["image"],
            )
            plans.append(
                {
                    "variant": v["id"],
                    "title": v["title"],
                    "label": v["label"],
                    "match_score": score,
                    "image": first_img or "",
                    "plan": {
                        "days": sch["days"],
                        "totals": sch["totals"],
                        "stats": stats,
                        "dropped": sch["dropped"],
                        "weather_source": state["weather"]["source"],
                    },
                }
            )
        plans.sort(key=lambda x: -x["match_score"])
        plans[0]["label"] = "Best match"
        state["trace"].append(
            {
                "agent": self.name,
                "role": "Coordinates the agents and ranks the plans",
                "ms": round((time.perf_counter() - t0) * 1000),
                "message": f"Ranked 3 plans. Best: {plans[0]['title']} ({plans[0]['match_score']}/100).",
            }
        )
        return {"prefs": p, "plans": plans, "trace": state["trace"], "weather_source": state["weather"]["source"]}
