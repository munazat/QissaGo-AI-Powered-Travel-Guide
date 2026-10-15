"""Scheduling agent: splits places into days, orders each day, and sets times with travel,
lunch and opening hours. Outdoor places move away from rain and midday heat."""

from __future__ import annotations

import datetime as dt

from app.services.geo import haversine_km, leg

from . import costs
from .base import Agent, hm_to_min, min_to_hm
from .budget import trip_totals

BUCKET = {"morning": 0, "any": 1, "midday": 2, "evening": 3}
LUNCH_AT, LUNCH_MIN = 12 * 60 + 30, 45
DAY_LIMIT = 21 * 60 + 30


def effective_bucket(poi: dict, day_w: dict) -> str:
    if day_w["hot"] and poi["outdoor"] and poi["best_time"] in ("midday", "any"):
        return "evening"
    return poi["best_time"]


def fit_cost(p: dict, group: list[dict], day_w: dict) -> float:
    """Lower = better fit for this day: close by, not outdoors in rain, different time of day."""
    near = min(haversine_km(p["lat"], p["lon"], g["lat"], g["lon"]) for g in group)
    same = sum(1 for g in group if effective_bucket(g, day_w) == effective_bucket(p, day_w))
    return near + (4 if day_w["rainy"] and p["outdoor"] else 0) + 3 * same


def assign_days(selected: list[dict], days: int, wdays: list[dict]) -> list[list[dict]]:
    n = len(selected)
    base, extra = divmod(n, days)
    counts = [base + (1 if i < extra else 0) for i in range(days)]
    order = sorted(range(days), key=lambda i: -wdays[i]["rain_pct"])  # wettest day chooses first
    pool, result = list(selected), [[] for _ in range(days)]
    for di in order:
        if not counts[di] or not pool:
            continue
        rainy = wdays[di]["rainy"]
        anchor = max(pool, key=lambda p: p["score"] - (0.35 if rainy and p["outdoor"] else 0))
        group = [anchor]
        pool.remove(anchor)
        while len(group) < counts[di] and pool:
            nxt = min(pool, key=lambda p, g=group, w=wdays[di]: fit_cost(p, g, w))
            group.append(nxt)
            pool.remove(nxt)
        result[di] = group
    return result


def order_day(group: list[dict], day_w: dict) -> list[dict]:
    buckets: dict[int, list[dict]] = {}
    for p in group:
        buckets.setdefault(BUCKET[effective_bucket(p, day_w)], []).append(p)
    ordered, cur = [], None
    for b in sorted(buckets):
        cands = list(buckets[b])
        while cands:
            nxt = (
                max(cands, key=lambda p: p["score"])
                if cur is None
                else min(cands, key=lambda p: haversine_km(p["lat"], p["lon"], cur["lat"], cur["lon"]))
            )
            cands.remove(nxt)
            ordered.append(nxt)
            cur = nxt
    return ordered


def brk(kind: str, title: str, start: int, end: int) -> dict:
    return {"kind": "break", "type": kind, "title": title, "start": min_to_hm(start), "end": min_to_hm(end)}


def layout_day(
    ordered: list[dict], day_w: dict, start: str, rate: int, cars: int, city: dict | None = None
) -> tuple[list[dict], list[str]]:
    speed = {"speed_kmh": city["speed_kmh"], "road_factor": city["road_factor"]} if city and "speed_kmh" in city else {}
    items: list[dict] = []
    dropped: list[str] = []
    t, prev, lunch_done = hm_to_min(start), None, False
    for poi in ordered:
        travel = leg(prev, poi, rate, cars, **speed) if prev else None
        tmin = travel["minutes"] if travel else 0
        arrive = t + tmin
        opens, closes = hm_to_min(poi["open"]), min(hm_to_min(poi["close"]), DAY_LIMIT)
        bucket = effective_bucket(poi, day_w)
        if bucket == "evening":
            earliest = 16 * 60 + 30 if day_w["hot"] else 15 * 60
            earliest = max(opens, min(earliest, closes - poi["minutes"]))
            if arrive < earliest:
                gap_start = t
                if items and not lunch_done and t < LUNCH_AT + 60:
                    ls = max(t, LUNCH_AT)
                    items.append(brk("lunch", "Lunch", ls, ls + LUNCH_MIN))
                    lunch_done, gap_start = True, ls + LUNCH_MIN
                if items and earliest - tmin - gap_start >= 60:
                    items.append(brk("rest", "Free time", gap_start, earliest - tmin))
                arrive = earliest
        elif not lunch_done and arrive >= LUNCH_AT and items:
            ls = max(t, LUNCH_AT)
            items.append(brk("lunch", "Lunch", ls, ls + LUNCH_MIN))
            lunch_done = True
            arrive = ls + LUNCH_MIN + tmin
        arrive = max(arrive, opens)
        end = arrive + poi["minutes"]
        if end > closes:
            dropped.append(poi["name"])
            continue
        items.append(
            {"kind": "stop", **poi, "start": min_to_hm(arrive), "end": min_to_hm(end), "leg": travel, "bucket": bucket}
        )
        t, prev = end, poi
    return items, dropped


class SchedulingAgent(Agent):
    name = "Scheduling Agent"
    role = "Orders each day by location, time and weather"

    def build_days(self, chosen: list[dict], p: dict, wdays: list[dict]) -> tuple[list[dict], list[str]]:
        rate, cars = p["city"]["transport_per_km"], costs.cars(p["size"])
        groups = assign_days(chosen, p["days"], wdays)
        days_out, dropped = [], []
        for i, group in enumerate(groups):
            items, drop = layout_day(order_day(group, wdays[i]), wdays[i], p["day_start"], rate, cars, p["city"])
            dropped += drop
            date = p["start_date"] + dt.timedelta(days=i)
            days_out.append(
                {
                    "day": i + 1,
                    "date": date.isoformat(),
                    "weekday": date.strftime("%a"),
                    "weather": wdays[i],
                    "items": items,
                }
            )
        return days_out, dropped

    def run(self, state: dict) -> str:
        p, wdays = state["prefs"], state["weather"]["days"]
        state["schedules"], notes = {}, []
        for vid, sel in state["selected"].items():
            chosen, trimmed = list(sel["pois"]), 0
            for _ in range(8):
                days_out, dropped = self.build_days(chosen, p, wdays)
                totals = trip_totals(days_out, p, sel["hotel"])
                if totals["within"] or len(chosen) <= p["days"]:
                    break
                chosen = sorted(chosen, key=lambda x: x["score"])[1:]  # drop the weakest place
                trimmed += 1
            state["schedules"][vid] = {"days": days_out, "totals": totals, "dropped": dropped, "hotel": sel["hotel"]}
            if trimmed or dropped:
                notes.append(f"{vid}: {trimmed + len(dropped)} removed")
        extra = (" " + "; ".join(notes) + ".") if notes else ""
        return f"Days grouped by area, timed around opening hours, lunch and weather.{extra}"
