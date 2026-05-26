"""Pydantic-схемы для API (response_model / валидация)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Request schemas ---


class SubscribeRequest(BaseModel):
    email: EmailStr
    phenomenon_id: int = Field(gt=0)


# --- Response schemas ---


class PlaceOut(BaseModel):
    id: int
    name: str
    region: str | None = None
    subregion: str | None = None
    latitude: float
    longitude: float

    model_config = ConfigDict(from_attributes=True)


class PhenomenonOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: str
    kind_ru: str | None = None
    category: str | None = None
    icon_lucide: str | None = None
    main_photo_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PhenomenonDetailOut(PhenomenonOut):
    description: str | None = None
    typical_season: str | None = None
    website_url: str | None = None
    water_temp_c: float | None = None


class ForecastOut(BaseModel):
    start: str | None = None
    peak: str | None = None
    end: str | None = None
    years_used: int = 0
    start_std_days: float | None = None
    peak_std_days: float | None = None
    end_std_days: float | None = None


class EventOut(BaseModel):
    id: int
    start_date: str
    peak_date: str
    end_date: str
    intensity: int
    marker_status: str
    phenomenon: PhenomenonOut
    place: PlaceOut
    forecast_stats: ForecastOut | None = None
    phase_history: list[dict[str, Any]] | None = None


class EventListResponse(BaseModel):
    today: str
    items: list[EventOut]
    limit: int = 100
    offset: int = 0


class MapEventsResponse(BaseModel):
    today: str
    items: list[EventOut]


class PhenomenonDetailResponse(BaseModel):
    phenomenon: PhenomenonDetailOut
    forecast: ForecastOut | None = None
    events: list[EventOut]


class FiltersMetaResponse(BaseModel):
    regions: list[str]
    subregions: list[str]
    kinds: list[str]


class SubregionsResponse(BaseModel):
    subregions: list[str]


class WeatherDetailsOut(BaseModel):
    temp_c: float | None = None
    feels_like_c: float | None = None
    humidity: int | None = None
    wind_speed_ms: float | None = None
    weather_desc_ru: str | None = None


class WeatherHintResponse(BaseModel):
    message: str
    detail: str | None = None
    weather_details: WeatherDetailsOut | None = None


class SunTimesResponse(BaseModel):
    sunrise: int
    sunset: int
    timezone: int


class SubscribeResponse(BaseModel):
    ok: bool
    message: str


class HealthResponse(BaseModel):
    status: str
