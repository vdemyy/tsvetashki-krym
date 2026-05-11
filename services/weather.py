"""Опционально: осадки по OpenWeather (3ч прогноз)."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

OW_KEY = os.getenv("OPENWEATHER_API_KEY", "")


@dataclass
class WeatherHint:
    message: str | None
    raw_summary: str | None = None


async def rain_hint(lat: float, lon: float, hours_ahead: int = 12) -> WeatherHint:
    if not OW_KEY:
        return WeatherHint(None)
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OW_KEY, "units": "metric", "lang": "ru"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return WeatherHint("Погода временно недоступна.")

    items = data.get("list") or []
    rainy = []
    for it in items[: max(1, hours_ahead // 3)]:
        w = (it.get("weather") or [{}])[0]
        main = (it.get("rain") or {}).get("3h", 0) or 0
        if w.get("main") in ("Rain", "Drizzle", "Thunderstorm") or main > 0:
            rainy.append(it.get("dt_txt", ""))

    if not rainy:
        return WeatherHint(None, "без существенных осадков в ближайшие часы")

    return WeatherHint(
        "Возможны осадки в этом районе в ближайшие часы — проверьте прогноз перед выездом.",
        ", ".join(rainy[:3]),
    )
