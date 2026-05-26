from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Event, Phenomenon, Place, Subscription
from services.forecast import forecast_from_history, marker_status
from services.icon_map import lucide_icon_for_phenomenon
from services.weather import rain_hint, get_weather_details
import schemas
from pydantic import TypeAdapter, ValidationError, EmailStr
from utils.limiter import limiter

KIND_RU_MAP = {
    "flowering": "Цветение",
    "visual": "Визуальное",
    "harvest": "Урожай",
    "animals": "Животные",
    "activity": "Событие",
}

router = APIRouter(prefix="/api", tags=["api"])


def _serialize_event(e: Event, today: date) -> dict[str, Any]:
    ph = e.phenomenon
    pl = e.place
    fc = forecast_from_history(e.phase_history, today.year)
    
    return {
        "id": e.id,
        "start_date": e.start_date.isoformat(),
        "peak_date": e.peak_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "intensity": e.intensity,
        "marker_status": marker_status(today, e.start_date, e.end_date),
        "phenomenon": {
            "id": ph.id,
            "slug": ph.slug,
            "name": ph.name,
            "kind": ph.kind,
            "kind_ru": KIND_RU_MAP.get(ph.kind, ph.kind),
            "category": ph.category,
            "icon_lucide": lucide_icon_for_phenomenon(ph),
            "main_photo_url": ph.main_photo_url or None,
        },
        "place": {
            "id": pl.id,
            "name": pl.name,
            "region": pl.region,
            "subregion": pl.subregion,
            "latitude": pl.latitude,
            "longitude": pl.longitude,
        },
        "forecast_stats": (
            {
                "start": fc.start.isoformat() if fc and fc.start else None,
                "peak": fc.peak.isoformat() if fc and fc.peak else None,
                "end": fc.end.isoformat() if fc and fc.end else None,
                "years_used": fc.years_used if fc else 0,
                "start_std_days": fc.start_std_days if fc else None,
                "peak_std_days": fc.peak_std_days if fc else None,
                "end_std_days": fc.end_std_days if fc else None,
            }
            if fc
            else None
        ),
        "phase_history": e.phase_history,
    }


def _event_query(
    _db: Session,
    today: date,
    *,
    feed_only: bool,
    region: str | None,
    subregion: str | None,
    kind: str | None,
    phenomenon_id: int | None,
    slug: str | None,
    month: int | None,
    q: str | None,
):
    stmt = select(Event).options(joinedload(Event.phenomenon), joinedload(Event.place))
    stmt = stmt.join(Event.phenomenon).join(Event.place)

    if feed_only:
        soon = today + timedelta(days=7)
        stmt = stmt.where(
            or_(
                and_(Event.start_date <= today, Event.end_date >= today),
                and_(Event.start_date > today, Event.start_date <= soon),
            )
        )
    else:
        past = today - timedelta(days=30)
        future = today + timedelta(days=120)
        stmt = stmt.where(Event.end_date >= past, Event.start_date <= future)

    if region:
        stmt = stmt.where(Place.region == region)
    if subregion:
        stmt = stmt.where(Place.subregion == subregion)
    if kind:
        stmt = stmt.where(Phenomenon.kind == kind)
    if phenomenon_id:
        stmt = stmt.where(Phenomenon.id == phenomenon_id)
    if slug:
        stmt = stmt.where(Phenomenon.slug == slug)
    if month is not None:
        stmt = stmt.where(
            or_(
                (Event.start_date.month == month),
                (Event.peak_date.month == month),
                (Event.end_date.month == month),
            )
        )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Phenomenon.name.ilike(like),
                Phenomenon.description.ilike(like),
                Place.name.ilike(like),
                Phenomenon.slug.ilike(like),
            )
        )
    return stmt


@router.get("/events", response_model=schemas.EventListResponse)
async def list_events(
    db: Session = Depends(get_db),
    feed: bool = Query(True, description="Только «сейчас» и ближайшие 7 дней"),
    sort: str = Query("start"),
    region: str | None = None,
    subregion: str | None = None,
    kind: str | None = None,
    phenomenon_id: int | None = None,
    slug: str | None = None,
    month: int | None = Query(None, ge=1, le=12),
    q: str | None = None,
    limit: int = Query(100, ge=1, le=500, description="Макс. кол-во результатов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
):
    today = date.today()
    if sort not in ("start", "peak", "end", "place", "name"):
        sort = "start"
    stmt = _event_query(
        db,
        today,
        feed_only=feed,
        region=region,
        subregion=subregion,
        kind=kind,
        phenomenon_id=phenomenon_id,
        slug=slug,
        month=month,
        q=q,
    )
    if sort == "start":
        stmt = stmt.order_by(Event.start_date)
    elif sort == "peak":
        stmt = stmt.order_by(Event.peak_date)
    elif sort == "end":
        stmt = stmt.order_by(Event.end_date)
    elif sort == "place":
        stmt = stmt.order_by(Place.name)
    else:
        stmt = stmt.order_by(Phenomenon.name)

    stmt = stmt.offset(offset).limit(limit)
    events = db.scalars(stmt).unique().all()
    return {
        "today": today.isoformat(),
        "items": [_serialize_event(e, today) for e in events],
        "limit": limit,
        "offset": offset,
    }


@router.get("/events/map", response_model=schemas.MapEventsResponse)
async def map_events(db: Session = Depends(get_db)):
    today = date.today()
    stmt = (
        select(Event)
        .options(joinedload(Event.phenomenon), joinedload(Event.place))
        .where(Event.end_date >= today - timedelta(days=45))
    )
    events = db.scalars(stmt).unique().all()
    return {"today": today.isoformat(), "items": [_serialize_event(e, today) for e in events]}


@router.get("/phenomena/{slug}", response_model=schemas.PhenomenonDetailResponse)
async def get_phenomenon(slug: str, db: Session = Depends(get_db)):
    ph = db.scalars(select(Phenomenon).where(Phenomenon.slug == slug)).first()
    if not ph:
        raise HTTPException(404, "Явление не найдено")
    today = date.today()
    stmt = (
        select(Event)
        .options(joinedload(Event.place))
        .where(Event.phenomenon_id == ph.id)
        .order_by(Event.start_date.desc())
    )
    events = db.scalars(stmt).unique().all()
    fc = None
    if events and events[0].phase_history:
        fc = forecast_from_history(events[0].phase_history, today.year)
    return {
        "phenomenon": {
            "id": ph.id,
            "slug": ph.slug,
            "name": ph.name,
            "kind": ph.kind,
            "kind_ru": KIND_RU_MAP.get(ph.kind, ph.kind),
            "category": ph.category,
            "description": ph.description,
            "typical_season": ph.typical_season,
            "icon_lucide": lucide_icon_for_phenomenon(ph),
            "main_photo_url": ph.main_photo_url or None,
            "website_url": ph.website_url or None,
            "water_temp_c": ph.water_temp_c,
        },
        "forecast": (
            {
                "start": fc.start.isoformat() if fc and fc.start else None,
                "peak": fc.peak.isoformat() if fc and fc.peak else None,
                "end": fc.end.isoformat() if fc and fc.end else None,
                "years_used": fc.years_used if fc else 0,
                "start_std_days": fc.start_std_days if fc else None,
                "peak_std_days": fc.peak_std_days if fc else None,
                "end_std_days": fc.end_std_days if fc else None,
            }
            if fc
            else None
        ),
        "events": [_serialize_event(e, today) for e in events],
    }


@router.get("/filters/meta", response_model=schemas.FiltersMetaResponse)
async def filters_meta(db: Session = Depends(get_db)):
    regions = db.scalars(select(Place.region).distinct().where(Place.region.isnot(None))).all()
    kinds = db.scalars(select(Phenomenon.kind).distinct()).all()
    subregions = db.scalars(
        select(Place.subregion).distinct().where(Place.subregion.isnot(None))
    ).all()
    return {
        "regions": sorted([r for r in regions if r]),
        "subregions": sorted([s for s in subregions if s]),
        "kinds": sorted(set(kinds)),
    }


@router.get("/filters/subregions", response_model=schemas.SubregionsResponse)
async def subregions_by_region(region: str | None = None, db: Session = Depends(get_db)):
    """Возвращает подрегионы для выбранного региона (или все, если регион не указан)."""
    stmt = select(Place.subregion).distinct().where(Place.subregion.isnot(None))
    if region:
        stmt = stmt.where(Place.region == region)
    subs = db.scalars(stmt).all()
    return {"subregions": sorted([s for s in subs if s])}


@router.get("/weather/hint", response_model=schemas.WeatherHintResponse)
async def weather_hint(lat: float, lon: float):
    hint = await rain_hint(lat, lon)
    details = await get_weather_details(lat, lon)
    
    weather_text = ""
    if details:
        parts = []
        if details.temp_c is not None:
            parts.append(f"{details.temp_c:.0f}°C")
        if details.feels_like_c is not None and abs(details.feels_like_c - details.temp_c) > 1:
            parts.append(f"ощущается как {details.feels_like_c:.0f}°C")
        if details.humidity is not None:
            parts.append(f"влажность {details.humidity}%")
        if details.wind_speed_ms is not None:
            parts.append(f"ветер {details.wind_speed_ms:.1f} м/с")
        if details.weather_desc_ru:
            parts.append(details.weather_desc_ru)
        weather_text = " · ".join(parts)
    
    return {
        "message": hint.message or weather_text,
        "detail": hint.raw_summary,
        "weather_details": {
            "temp_c": details.temp_c if details else None,
            "feels_like_c": details.feels_like_c if details else None,
            "humidity": details.humidity if details else None,
            "wind_speed_ms": details.wind_speed_ms if details else None,
            "weather_desc_ru": details.weather_desc_ru if details else None,
        } if details else None,
    }


@router.get("/sun-times", response_model=schemas.SunTimesResponse)
async def get_sun_times(lat: float, lon: float):
    """Get sunrise and sunset times from OpenWeather API"""
    import os
    import httpx
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(500, "OpenWeather API key not configured")
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            return {
                "sunrise": data["sys"]["sunrise"],
                "sunset": data["sys"]["sunset"],
                "timezone": data["timezone"],
            }
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch sun times: {str(e)}")


@router.post("/subscribe", response_model=schemas.SubscribeResponse)
@limiter.limit("5/minute")
async def subscribe(
    request: Request,
    email: str,
    phenomenon_id: int,
    db: Session = Depends(get_db),
):
    try:
        email = TypeAdapter(EmailStr).validate_python(email.strip().lower())
    except ValidationError:
        raise HTTPException(400, "Некорректный email")
    ph = db.get(Phenomenon, phenomenon_id)
    if not ph:
        raise HTTPException(404, "Явление не найдено")
    # Check for existing subscription
    existing = db.scalars(
        select(Subscription).where(
            Subscription.email == email,
            Subscription.phenomenon_id == phenomenon_id,
        )
    ).first()
    if existing:
        return {"ok": True, "message": "Вы уже подписаны на это явление."}
    sub = Subscription(email=email, phenomenon_id=phenomenon_id, active=True)
    db.add(sub)
    db.commit()
    return {"ok": True, "message": "Подписка сохранена."}
