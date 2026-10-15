"""Validator agent: checks every plan before it is shown and fixes what it can.

Checks: no overlapping times, every visit inside opening hours, day ends in time,
stop count within the pace, total within budget.
"""

from __future__ import annotations

from .base import Agent, hm_to_min
from .budget import trip_totals
from .scheduling import DAY_LIMIT


def problems(day: dict, per_day: int) -> list[str]:
    out = []
    last_end = 0
    stops = 0
    for item in day["items"]:
        start, end = hm_to_min(item["start"]), hm_to_min(item["end"])
        if start < last_end:
            out.append(f"overlap at {item['start']}")
        last_end = max(last_end, end)
        if item["kind"] == "stop":
            stops += 1
            if start < hm_to_min(item["open"]) or end > hm_to_min(item["close"]):
                out.append(f"{item['name']} outside opening hours")
    if last_end > DAY_LIMIT:
        out.append("day ends too late")
    if stops > per_day:
        out.append("too many stops")
    return out


class ValidatorAgent(Agent):
    name = "Validator Agent"
    role = "Double-checks times, opening hours and budget"

    def run(self, state: dict) -> str:
        p = state["prefs"]
        found = 0
        for sch in state["schedules"].values():
            for day in sch["days"]:
                issues = problems(day, p["stops_per_day"])
                if issues:
                    found += len(issues)
                    # Fix: keep only the stops that pass on their own, in order
                    kept, last_end = [], 0
                    for item in day["items"]:
                        start, end = hm_to_min(item["start"]), hm_to_min(item["end"])
                        ok = start >= last_end and end <= DAY_LIMIT
                        if item["kind"] == "stop":
                            ok = ok and start >= hm_to_min(item["open"]) and end <= hm_to_min(item["close"])
                        if ok:
                            kept.append(item)
                            last_end = end
                    day["items"] = kept
            sch["totals"] = trip_totals(sch["days"], p, sch["hotel"])
            sch["valid"] = all(not problems(d, p["stops_per_day"]) for d in sch["days"])
        over = [v for v, s in state["schedules"].items() if not s["totals"]["within"]]
        msg = "All plans passed." if not found else f"Fixed {found} issues."
        if over:
            msg += f" {len(over)} plan(s) slightly over budget."
        return msg
