"""Shared base for the itinerary agents.

Every agent reads the shared `state` dict, adds its own results, and returns a short
message. The base class times it and adds one trace entry (shown in the app while
plans are being made and stored in the agent_runs table).
"""

from __future__ import annotations

import time


class Agent:
    name = "Agent"
    role = ""

    def run(self, state: dict) -> str:  # pragma: no cover - each agent overrides this
        raise NotImplementedError

    def __call__(self, state: dict) -> dict:
        t0 = time.perf_counter()
        message = self.run(state)
        state.setdefault("trace", []).append(
            {"agent": self.name, "role": self.role, "ms": round((time.perf_counter() - t0) * 1000), "message": message}
        )
        return state


def hm_to_min(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def min_to_hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"
