"""Language model used by the chatbot's preference extractor.

- OllamaLLM: a free open-source model running on your own laptop (https://ollama.com).
- NoLLM: rules only (used when LLM_PROVIDER=none or Ollama is not running).
- FakeLLM: returns fixed answers, used in automated tests.

The chatbot always works without an LLM; the LLM only helps understand messy messages.
"""

from __future__ import annotations

import json
import time
from typing import Protocol

import requests

from app.core.config import get_settings

# JSON shape the model must return (Ollama "structured outputs")
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": ["string", "null"]},
        "start_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "days": {"type": ["integer", "null"]},
        "budget_pkr": {"type": ["integer", "null"]},
        "group_type": {"type": ["string", "null"], "enum": ["solo", "couple", "family", "friends", None]},
        "group_size": {"type": ["integer", "null"]},
        "interests": {"type": "array", "items": {"type": "string"}},
        "avoid": {"type": "array", "items": {"type": "string"}},
        "pace": {"type": ["string", "null"], "enum": ["relaxed", "balanced", "packed", None]},
    },
    "required": ["city", "start_date", "days", "budget_pkr", "group_type", "group_size", "interests", "avoid", "pace"],
}

SYSTEM_PROMPT = """You extract trip details from a traveller's message for a Pakistan travel planner.
Return ONLY JSON matching the schema. Use null or [] when the message does not say it. Never guess.
Today is {today}. Known cities: {cities}. Known interests: {interests}.
Rules:
- city: one of the known city ids, else null.
- start_date: YYYY-MM-DD, resolve words like "tomorrow" or "next Friday" from today.
- days: number of trip days. budget_pkr: total budget in Pakistani rupees (50k = 50000, 1 lakh = 100000).
- group_type: solo, couple, family or friends. group_size: number of people if stated.
- interests: known interest ids the user WANTS. avoid: known interest ids the user does NOT want.
- pace: relaxed, balanced or packed.
The bot's last question was about: {awaiting}."""


class LLM(Protocol):
    def extract(self, message: str, context: dict) -> dict | None: ...


class NoLLM:
    name = "none"

    def extract(self, message: str, context: dict) -> dict | None:
        return None


class FakeLLM:
    """For tests: always returns the dict it was created with."""

    name = "fake"

    def __init__(self, answer: dict | None = None):
        self.answer = answer
        self.calls: list[str] = []

    def extract(self, message: str, context: dict) -> dict | None:
        self.calls.append(message)
        return self.answer


class OllamaLLM:
    name = "ollama"
    _down_until = 0.0  # if Ollama is not running, don't retry for a minute

    def __init__(self, url: str, model: str, timeout: float):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    def extract(self, message: str, context: dict) -> dict | None:
        if time.time() < OllamaLLM._down_until:
            return None
        prompt = SYSTEM_PROMPT.format(
            today=context.get("today", ""),
            cities=", ".join(context.get("cities", [])),
            interests=", ".join(context.get("interests", [])),
            awaiting=context.get("awaiting") or "nothing",
        )
        try:
            r = requests.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": EXTRACT_SCHEMA,
                    "options": {"temperature": 0},
                    "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": message}],
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            return json.loads(r.json()["message"]["content"])
        except requests.ConnectionError:
            OllamaLLM._down_until = time.time() + 60
            return None
        except Exception:
            return None


def get_llm() -> LLM:
    s = get_settings()
    if s.llm_provider.lower() == "ollama":
        return OllamaLLM(s.ollama_url, s.ollama_model, s.llm_timeout_seconds)
    return NoLLM()
