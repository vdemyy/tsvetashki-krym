from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from database import get_db
from models import Event, Phenomenon, Place, Subscription, TelegramWatch

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "dreamteam")


def _check(request: Request) -> RedirectResponse | None:
    if not request.session.get("admin"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        request, "admin/login.html", {"title": "Вход"}
    )


@router.post("/login")
async def login_post(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"title": "Вход", "error": "Неверный пароль"},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    np = db.scalar(select(func.count()).select_from(Phenomenon)) or 0
    nl = db.scalar(select(func.count()).select_from(Place)) or 0
    ne = db.scalar(select(func.count()).select_from(Event)) or 0
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"title": "Админка", "n_phenomena": np, "n_places": nl, "n_events": ne},
    )


# --- phenomena ---


@router.get("/phenomena", response_class=HTMLResponse)
async def list_phenomena(request: Request, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    rows = db.scalars(select(Phenomenon).order_by(Phenomenon.id)).all()
    return templates.TemplateResponse(
        request, "admin/phenomena_list.html", {"title": "Явления", "rows": rows}
    )


@router.get("/phenomena/new", response_class=HTMLResponse)
async def new_phenomenon_form(request: Request):
    redir = _check(request)
    if redir:
        return redir
    return templates.TemplateResponse(
        request,
        "admin/phenomenon_edit.html",
        {"title": "Новое явление", "row": None},
    )


@router.post("/phenomena/new")
async def new_phenomenon_post(
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(...),
    name: str = Form(...),
    kind: str = Form(...),
    category: str = Form(""),
    description: str = Form(""),
    typical_season: str = Form(""),
    icon_lucide: str = Form(""),
    icon_emoji: str = Form(""),
    main_photo_url: str = Form(""),
    website_url: str = Form(""),
    water_temp_c: str = Form(""),
):
    redir = _check(request)
    if redir:
        return redir
    wt: float | None = None
    if water_temp_c.strip():
        try:
            wt = float(water_temp_c.replace(",", "."))
        except ValueError:
            wt = None
    db.add(
        Phenomenon(
            slug=slug.strip(),
            name=name.strip(),
            kind=kind.strip(),
            category=category.strip() or None,
            description=description.strip() or None,
            typical_season=typical_season.strip() or None,
            icon_emoji=icon_emoji.strip() or "",
            icon_lucide=icon_lucide.strip() or None,
            main_photo_url=main_photo_url.strip() or None,
            website_url=website_url.strip() or None,
            water_temp_c=wt,
        )
    )
    db.commit()
    return RedirectResponse(url="/admin/phenomena", status_code=303)


@router.get("/phenomena/{pid}/edit", response_class=HTMLResponse)
async def edit_phenomenon_form(request: Request, pid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Phenomenon, pid)
    if not row:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request,
        "admin/phenomenon_edit.html",
        {"title": "Редактирование", "row": row},
    )


@router.post("/phenomena/{pid}/edit")
async def edit_phenomenon_post(
    request: Request,
    pid: int,
    db: Session = Depends(get_db),
    slug: str = Form(...),
    name: str = Form(...),
    kind: str = Form(...),
    category: str = Form(""),
    description: str = Form(""),
    typical_season: str = Form(""),
    icon_lucide: str = Form(""),
    icon_emoji: str = Form(""),
    main_photo_url: str = Form(""),
    website_url: str = Form(""),
    water_temp_c: str = Form(""),
):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Phenomenon, pid)
    if not row:
        raise HTTPException(404)
    wt: float | None = None
    if water_temp_c.strip():
        try:
            wt = float(water_temp_c.replace(",", "."))
        except ValueError:
            wt = None
    row.slug = slug.strip()
    row.name = name.strip()
    row.kind = kind.strip()
    row.category = category.strip() or None
    row.description = description.strip() or None
    row.typical_season = typical_season.strip() or None
    row.icon_emoji = icon_emoji.strip() or ""
    row.icon_lucide = icon_lucide.strip() or None
    row.main_photo_url = main_photo_url.strip() or None
    row.website_url = website_url.strip() or None
    row.water_temp_c = wt
    db.commit()
    return RedirectResponse(url="/admin/phenomena", status_code=303)


@router.post("/phenomena/{pid}/delete")
async def delete_phenomenon(request: Request, pid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    db.execute(delete(TelegramWatch).where(TelegramWatch.phenomenon_id == pid))
    db.execute(delete(Subscription).where(Subscription.phenomenon_id == pid))
    db.execute(delete(Event).where(Event.phenomenon_id == pid))
    db.execute(delete(Phenomenon).where(Phenomenon.id == pid))
    db.commit()
    return RedirectResponse(url="/admin/phenomena", status_code=303)


# --- places ---


@router.get("/places", response_class=HTMLResponse)
async def list_places(request: Request, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    rows = db.scalars(select(Place).order_by(Place.id)).all()
    return templates.TemplateResponse(
        request, "admin/places_list.html", {"title": "Места", "rows": rows}
    )


@router.get("/places/new", response_class=HTMLResponse)
async def new_place_form(request: Request):
    redir = _check(request)
    if redir:
        return redir
    return templates.TemplateResponse(
        request, "admin/place_edit.html", {"title": "Новое место", "row": None},
    )


@router.post("/places/new")
async def new_place_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    region: str = Form(""),
    subregion: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    redir = _check(request)
    if redir:
        return redir
    db.add(
        Place(
            name=name.strip(),
            region=region.strip() or None,
            subregion=subregion.strip() or None,
            latitude=latitude,
            longitude=longitude,
        )
    )
    db.commit()
    return RedirectResponse(url="/admin/places", status_code=303)


@router.get("/places/{lid}/edit", response_class=HTMLResponse)
async def edit_place_form(request: Request, lid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Place, lid)
    if not row:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "admin/place_edit.html", {"title": "Место", "row": row},
    )


@router.post("/places/{lid}/edit")
async def edit_place_post(
    request: Request,
    lid: int,
    db: Session = Depends(get_db),
    name: str = Form(...),
    region: str = Form(""),
    subregion: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Place, lid)
    if not row:
        raise HTTPException(404)
    row.name = name.strip()
    row.region = region.strip() or None
    row.subregion = subregion.strip() or None
    row.latitude = latitude
    row.longitude = longitude
    db.commit()
    return RedirectResponse(url="/admin/places", status_code=303)


@router.post("/places/{lid}/delete")
async def delete_place(request: Request, lid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    db.execute(delete(Event).where(Event.place_id == lid))
    db.execute(delete(Place).where(Place.id == lid))
    db.commit()
    return RedirectResponse(url="/admin/places", status_code=303)


# --- events ---


def _parse_json_list(raw: str) -> list[dict[str, Any]] | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return data


@router.get("/events", response_class=HTMLResponse)
async def list_events_admin(request: Request, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    from sqlalchemy.orm import joinedload

    stmt = (
        select(Event)
        .options(joinedload(Event.phenomenon), joinedload(Event.place))
        .order_by(Event.start_date.desc())
    )
    rows = db.scalars(stmt).unique().all()
    phenomena = db.scalars(select(Phenomenon).order_by(Phenomenon.name)).all()
    places = db.scalars(select(Place).order_by(Place.name)).all()
    return templates.TemplateResponse(
        request,
        "admin/events_list.html",
        {
            "title": "События",
            "rows": rows,
            "phenomena": phenomena,
            "places": places,
        },
    )


@router.post("/events/new")
async def new_event_post(
    request: Request,
    db: Session = Depends(get_db),
    phenomenon_id: int = Form(...),
    place_id: int = Form(...),
    start_date: date = Form(...),
    peak_date: date = Form(...),
    end_date: date = Form(...),
    intensity: int = Form(3),
    phase_history_json: str = Form(""),
    notes: str = Form(""),
):
    redir = _check(request)
    if redir:
        return redir
    phist = _parse_json_list(phase_history_json)
    db.add(
        Event(
            phenomenon_id=phenomenon_id,
            place_id=place_id,
            start_date=start_date,
            peak_date=peak_date,
            end_date=end_date,
            intensity=intensity,
            phase_history=phist,
            notes=notes.strip() or None,
        )
    )
    db.commit()
    return RedirectResponse(url="/admin/events", status_code=303)


@router.get("/events/{eid}/edit", response_class=HTMLResponse)
async def edit_event_form(request: Request, eid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Event, eid)
    if not row:
        raise HTTPException(404)
    phenomena = db.scalars(select(Phenomenon).order_by(Phenomenon.name)).all()
    places = db.scalars(select(Place).order_by(Place.name)).all()
    hist = json.dumps(row.phase_history or [], ensure_ascii=False, indent=2)
    return templates.TemplateResponse(
        request,
        "admin/event_edit.html",
        {
            "title": "Событие",
            "row": row,
            "phenomena": phenomena,
            "places": places,
            "phase_history_json": hist,
        },
    )


@router.post("/events/{eid}/edit")
async def edit_event_post(
    request: Request,
    eid: int,
    db: Session = Depends(get_db),
    phenomenon_id: int = Form(...),
    place_id: int = Form(...),
    start_date: date = Form(...),
    peak_date: date = Form(...),
    end_date: date = Form(...),
    intensity: int = Form(3),
    phase_history_json: str = Form(""),
    notes: str = Form(""),
):
    redir = _check(request)
    if redir:
        return redir
    row = db.get(Event, eid)
    if not row:
        raise HTTPException(404)
    row.phenomenon_id = phenomenon_id
    row.place_id = place_id
    row.start_date = start_date
    row.peak_date = peak_date
    row.end_date = end_date
    row.intensity = intensity
    row.phase_history = _parse_json_list(phase_history_json)
    row.notes = notes.strip() or None
    db.commit()
    return RedirectResponse(url="/admin/events", status_code=303)


@router.post("/events/{eid}/delete")
async def delete_event(request: Request, eid: int, db: Session = Depends(get_db)):
    redir = _check(request)
    if redir:
        return redir
    db.execute(delete(Event).where(Event.id == eid))
    db.commit()
    return RedirectResponse(url="/admin/events", status_code=303)
