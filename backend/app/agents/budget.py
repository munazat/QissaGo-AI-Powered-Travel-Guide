"""Budget agent: reserves food and hotel money first, then picks the best places that still fit."""

from __future__ import annotations

from . import costs
from .base import Agent
from .destination import VARIANTS

AVG_LEG_KM = 5  # rough travel per stop before the real route is known


def jeep_days(days_out: list[dict]) -> set[int]:
    """Days (1-based) that visit at least one place only reachable by hired jeep."""
    return {d["day"] for d in days_out if any(s["kind"] == "stop" and costs.needs_jeep(s) for s in d["items"])}


def trip_totals(days_out: list[dict], prefs: dict, hotel: str) -> dict:
    """Final cost of a scheduled plan. On jeep days the hired jeep replaces the per-km taxi fares."""
    city, size, days = prefs["city"], prefs["size"], prefs["days"]
    traveller = prefs.get("traveller_type", "local")
    jeep = jeep_days(days_out)
    stops = [s for d in days_out for s in d["items"] if s["kind"] == "stop"]
    entries = sum(costs.entry_pp(s, traveller) * size for s in stops)
    transport = sum(
        (s.get("leg") or {}).get("cost", 0)
        for d in days_out
        if d["day"] not in jeep
        for s in d["items"]
        if s["kind"] == "stop"
    )
    jeep_hire = costs.jeep_cost(city, len(jeep), size)
    meals = costs.meals(city, days, size)
    stay = costs.stay(city, days, size, hotel, "no_stay" in prefs["needs"])
    travel = costs.travel_to_city(prefs.get("home_city"), prefs["city_id"], size, prefs.get("travel_mode", "bus"))
    total = entries + transport + jeep_hire + meals + stay + travel
    return {
        "entries": entries,
        "transport": transport,
        "jeep": jeep_hire,
        "jeep_days": len(jeep),
        "meals": meals,
        "stay": stay,
        "hotel": hotel,
        "travel_to_city": travel,
        "home_city": prefs.get("home_city") or "",
        "travel_mode": prefs.get("travel_mode", "bus"),
        "traveller_type": traveller,
        "total": total,
        "budget": prefs["budget"],
        "left": prefs["budget"] - total,
        "within": total <= prefs["budget"],
        "per_person": round(total / size),
    }


def _travel(prefs: dict) -> int:
    return costs.travel_to_city(
        prefs.get("home_city"), prefs["city_id"], prefs["size"], prefs.get("travel_mode", "bus")
    )


class BudgetAgent(Agent):
    name = "Budget Agent"
    role = "Keeps every plan inside your budget"

    @staticmethod
    def choose_hotel(prefs: dict, preferred: str) -> str:
        if "no_stay" in prefs["needs"] or preferred == "budget":
            return "budget"
        c = prefs["city"]
        fixed_mid = (
            costs.meals(c, prefs["days"], prefs["size"])
            + costs.stay(c, prefs["days"], prefs["size"], "mid")
            + _travel(prefs)
        )
        return "mid" if fixed_mid <= prefs["budget"] * 0.7 else "budget"

    def select(self, ranked: list[dict], prefs: dict, taken: frozenset, hotel: str) -> tuple[list[dict], int]:
        # Places the earlier options didn't use get a small bonus, so the 3 plans differ.
        ranked = sorted(ranked, key=lambda x: -(x["score"] + (0.10 if x["id"] not in taken else 0)))
        size, days, per_day = prefs["size"], prefs["days"], prefs["stops_per_day"]
        target = min(days * per_day, max(days, int(len(ranked) * 0.75)))
        c = prefs["city"]
        spend = (
            costs.meals(c, days, size) + costs.stay(c, days, size, hotel, "no_stay" in prefs["needs"]) + _travel(prefs)
        )
        traveller = prefs.get("traveller_type", "local")
        jeep_paid = False
        leg_cost = AVG_LEG_KM * c["transport_per_km"] * costs.cars(size)
        chosen, skipped = [], 0
        for poi in ranked:
            if len(chosen) >= target:
                break
            cost = costs.entry_pp(poi, traveller) * size + leg_cost
            if costs.needs_jeep(poi) and not jeep_paid:
                cost += costs.jeep_cost(c, 1, size)  # at least one jeep day
            if spend + cost <= prefs["budget"]:
                chosen.append(poi)
                spend += cost
                jeep_paid = jeep_paid or costs.needs_jeep(poi)
            else:
                skipped += 1
        if len(chosen) < days:  # at least one place a day: add the cheapest
            rest = sorted((x for x in ranked if x not in chosen), key=lambda x: costs.entry_pp(x, traveller))
            chosen += rest[: days - len(chosen)]
        return chosen, skipped

    def run(self, state: dict) -> str:
        p = state["prefs"]
        state["selected"], taken, notes = {}, set(), []
        for v in VARIANTS:
            hotel = self.choose_hotel(p, v["hotel"])
            chosen, skipped = self.select(state["ranked"][v["id"]], p, frozenset(taken), hotel)
            state["selected"][v["id"]] = {"pois": chosen, "hotel": hotel}
            taken |= {c["id"] for c in chosen}
            if skipped:
                notes.append(f"{v['label']}: {skipped} over budget")
        extra = (" " + "; ".join(notes) + ".") if notes else ""
        return f"Food and stay reserved first, places chosen within Rs {p['budget']:,}.{extra}"
