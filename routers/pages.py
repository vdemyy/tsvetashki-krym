from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Event, Phenomenon, Place, Subscription
from routers.api import _event_query, _serialize_event
from services.forecast import forecast_from_history
from services.icon_map import lucide_icon_for_phenomenon
from utils.dates import timers_for_phases

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def feed_page(
    request: Request,
    db: Session = Depends(get_db),
    region: str | None = None,
    subregion: str | None = None,
    kind: str | None = None,
    phenomenon_id: str | None = None,
    month: str | None = None,
    q: str | None = None,
    sort: str = Query("start"),
    extended: bool = Query(
        False,
        description="Показать окно до ~4 мес. вперёд (для планирования, не только 7 дней)",
    ),
):
    today = date.today()
    if sort not in ("start", "peak", "end", "place", "name"):
        sort = "start"
    
    # Convert string params to proper types, handle empty strings
    phenomenon_id_int = None
    if phenomenon_id and phenomenon_id.strip():
        try:
            phenomenon_id_int = int(phenomenon_id)
        except ValueError:
            pass
    
    month_int = None
    if month and month.strip():
        try:
            month_int = int(month)
            if not (1 <= month_int <= 12):
                month_int = None
        except ValueError:
            pass
    
    stmt = _event_query(
        db,
        today,
        feed_only=not extended,
        region=region,
        subregion=subregion,
        kind=kind,
        phenomenon_id=phenomenon_id_int,
        slug=None,
        month=month_int,
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

    events = db.scalars(stmt).unique().all()
    items = []
    for e in events:
        raw = _serialize_event(e, today)
        raw["timers"] = timers_for_phases(today, e.start_date, e.peak_date, e.end_date)
        items.append(raw)

    regions = db.scalars(select(Place.region).distinct().where(Place.region.isnot(None))).all()
    kinds = db.scalars(select(Phenomenon.kind).distinct()).all()
    subregions = db.scalars(
        select(Place.subregion).distinct().where(Place.subregion.isnot(None))
    ).all()

    return templates.TemplateResponse(
        request,
        "feed.html",
        {
            "title": "Лента",
            "events": items,
            "today": today,
            "filters": {
                "region": region,
                "subregion": subregion,
                "kind": kind,
                "phenomenon_id": phenomenon_id_int,
                "month": month_int,
                "q": q or "",
                "sort": sort,
                "extended": extended,
            },
            "meta_regions": sorted([r for r in regions if r]),
            "meta_subregions": sorted([s for s in subregions if s]),
            "meta_kinds": sorted(set(kinds)),
            "phenomena_options": db.scalars(select(Phenomenon).order_by(Phenomenon.name)).all(),
        },
    )


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse(
        request,
        "map.html",
        {"title": "Карта"},
    )


@router.get("/p/{slug}", response_class=HTMLResponse)
async def phenomenon_page(slug: str, request: Request, db: Session = Depends(get_db)):
    ph = db.scalars(select(Phenomenon).where(Phenomenon.slug == slug)).first()
    if not ph:
        return HTMLResponse("Не найдено", status_code=404)
    today = date.today()
    stmt = (
        select(Event)
        .options(joinedload(Event.place), joinedload(Event.phenomenon))
        .where(Event.phenomenon_id == ph.id)
        .order_by(Event.start_date.desc())
    )
    events = db.scalars(stmt).unique().all()
    items = []
    for e in events:
        raw = _serialize_event(e, today)
        raw["timers"] = timers_for_phases(today, e.start_date, e.peak_date, e.end_date)
        items.append(raw)
    history = events[0].phase_history if events else None
    fc = forecast_from_history(history, today.year) if history else None
    return templates.TemplateResponse(
        request,
        "phenomenon.html",
        {
            "title": ph.name,
            "p": ph,
            "events": items,
            "phase_history_json": history or [],
            "forecast": fc,
            "today": today,
            "lucide_icon": lucide_icon_for_phenomenon(ph),
        },
    )


@router.post("/subscribe")
async def subscribe_form(
    request: Request,
    email: str = Form(...),
    phenomenon_id: int = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    ph = db.get(Phenomenon, phenomenon_id)
    if ph and "@" in email:
        db.add(Subscription(email=email, phenomenon_id=phenomenon_id, active=True))
        db.commit()
    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=303)
