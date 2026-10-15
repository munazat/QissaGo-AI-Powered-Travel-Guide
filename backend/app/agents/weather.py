"""Weather agent: forecast (or typical weather) for every day of the trip."""

from __future__ import annotations

from app.services.weather import get_forecast

from .base import Agent


class WeatherAgent(Agent):
    name = "Weather Agent"
    role = "Gets the weather for each day"

    def run(self, state: dict) -> str:
        p = state["prefs"]
        c = p["city"]
        fc = get_forecast(p["city_id"], c["lat"], c["lon"], p["start_date"], p["days"])
        state["weather"] = fc
        rainy = sum(d["rainy"] for d in fc["days"])
        hot = sum(d["hot"] for d in fc["days"])
        source = "Live forecast" if fc["source"] == "forecast" else "Typical weather for the season"
        return f"{source}: {rainy} rainy and {hot} hot days."
