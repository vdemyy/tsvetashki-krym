"""Идемпотентное наполнение БД: явления, места, события."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from database import SessionLocal
from models import Event, Phenomenon, Place
from services.icon_map import DEFAULT_BY_KIND


def _get_or_create_place(
    db,
    name: str,
    *,
    region: str | None,
    subregion: str | None,
    latitude: float,
    longitude: float,
) -> Place:
    pl = db.scalars(select(Place).where(Place.name == name)).first()
    if pl:
        return pl
    pl = Place(
        name=name,
        region=region,
        subregion=subregion,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(pl)
    db.flush()
    return pl


def _get_or_create_phenomenon(
    db,
    slug: str,
    *,
    name: str,
    kind: str,
    category: str | None,
    description: str | None,
    typical_season: str | None,
    icon_lucide: str | None,
    main_photo_url: str = "",
    website_url: str | None = None,
    water_temp_c: float | None = None,
) -> Phenomenon:
    ph = db.scalars(select(Phenomenon).where(Phenomenon.slug == slug)).first()
    if ph:
        return ph
    ph = Phenomenon(
        slug=slug,
        name=name,
        kind=kind,
        category=category,
        description=description,
        typical_season=typical_season,
        icon_emoji="",
        icon_lucide=icon_lucide or DEFAULT_BY_KIND.get(kind, "sparkles"),
        main_photo_url=main_photo_url or "",
        website_url=website_url or "",
        water_temp_c=water_temp_c,
    )
    db.add(ph)
    db.flush()
    return ph


def _ensure_event(
    db,
    phenomenon: Phenomenon,
    place: Place,
    *,
    start_date: date,
    peak_date: date,
    end_date: date,
    intensity: int = 3,
    phase_history: list | None = None,
    notes: str | None = None,
) -> None:
    ex = db.scalars(
        select(Event).where(
            Event.phenomenon_id == phenomenon.id,
            Event.place_id == place.id,
            Event.start_date == start_date,
        )
    ).first()
    if ex:
        return
    db.add(
        Event(
            phenomenon_id=phenomenon.id,
            place_id=place.id,
            start_date=start_date,
            peak_date=peak_date,
            end_date=end_date,
            intensity=intensity,
            phase_history=phase_history,
            notes=notes,
        )
    )


def _backfill_icons(db) -> None:
    for ph in db.scalars(select(Phenomenon)).all():
        if not ph.icon_lucide:
            ph.icon_lucide = DEFAULT_BY_KIND.get(ph.kind or "", "sparkles")
    db.commit()


def ensure_seed() -> None:
    import json
    import os
    from datetime import datetime

    db = SessionLocal()
    try:
        json_path = os.path.join(os.path.dirname(__file__), "seed.json")
        if not os.path.exists(json_path):
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Places
        places_dict = {}
        for p_data in data.get("places", []):
            pl = _get_or_create_place(
                db,
                p_data["name"],
                region=p_data.get("region"),
                subregion=p_data.get("subregion"),
                latitude=p_data["latitude"],
                longitude=p_data["longitude"],
            )
            places_dict[p_data["name"]] = pl

        # 2. Phenomena
        phenomena_dict = {}
        for ph_data in data.get("phenomena", []):
            ph = _get_or_create_phenomenon(
                db,
                ph_data["slug"],
                name=ph_data["name"],
                kind=ph_data["kind"],
                category=ph_data.get("category"),
                description=ph_data.get("description"),
                typical_season=ph_data.get("typical_season"),
                icon_lucide=ph_data.get("icon_lucide"),
                main_photo_url=ph_data.get("main_photo_url", ""),
                website_url=ph_data.get("website_url"),
                water_temp_c=ph_data.get("water_temp_c"),
            )
            phenomena_dict[ph_data["slug"]] = ph

        # 3. Events
        for ev_data in data.get("events", []):
            ph = phenomena_dict.get(ev_data["phenomenon_slug"])
            pl = places_dict.get(ev_data["place_name"])
            if not ph or not pl:
                continue

            start_dt = datetime.strptime(ev_data["start_date"], "%Y-%m-%d").date()
            peak_dt = datetime.strptime(ev_data["peak_date"], "%Y-%m-%d").date()
            end_dt = datetime.strptime(ev_data["end_date"], "%Y-%m-%d").date()

            _ensure_event(
                db,
                ph,
                pl,
                start_date=start_dt,
                peak_date=peak_dt,
                end_date=end_dt,
                intensity=ev_data.get("intensity", 3),
                phase_history=ev_data.get("phase_history"),
                notes=ev_data.get("notes"),
            )

        db.commit()
        _backfill_icons(db)
    finally:
        db.close()
