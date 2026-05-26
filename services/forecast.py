"""Прогноз фаз по историческим годам (среднее ± разброс по дню года)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any


def _parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m-%d", "%d.%m"):
        try:
            if fmt == "%m-%d":
                y = date.today().year
                return datetime.strptime(f"{y}-{s}", "%Y-%m-%d").date()
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _doy(d: date) -> float:
    return float(d.timetuple().tm_yday)


def _date_from_doy(year: int, doy: float) -> date:
    d0 = date(year, 1, 1)
    return d0 + timedelta(days=int(round(doy)) - 1)


@dataclass
class PhaseForecast:
    start: date | None
    peak: date | None
    end: date | None
    start_std_days: float | None
    peak_std_days: float | None
    end_std_days: float | None
    years_used: int


def forecast_from_history(
    phase_history: list[dict[str, Any]] | None,
    target_year: int | None = None,
) -> PhaseForecast | None:
    if not phase_history:
        return None
    target_year = target_year or date.today().year
    starts: list[float] = []
    peaks: list[float] = []
    ends: list[float] = []

    for row in phase_history:
        if not isinstance(row, dict):
            continue
        y = row.get("year") or row.get("y")
        start = _parse_date(row.get("start") or row.get("s"))
        peak = _parse_date(row.get("peak") or row.get("p"))
        end = _parse_date(row.get("end") or row.get("e"))
        if y and isinstance(y, int):
            if start and start.year != y:
                start = start.replace(year=y)
            if peak and peak.year != y:
                peak = peak.replace(year=y)
            if end and end.year != y:
                end = end.replace(year=y)
        if start:
            starts.append(_doy(start))
        if peak:
            peaks.append(_doy(peak))
        if end:
            ends.append(_doy(end))

    if not starts and not peaks and not ends:
        return None

    def stat(xs: list[float]) -> tuple[float | None, float | None]:
        if not xs:
            return None, None
        if len(xs) == 1:
            return xs[0], 0.0
        return statistics.mean(xs), statistics.pstdev(xs)

    ms, ss = stat(starts)
    mp, sp = stat(peaks)
    me, se = stat(ends)

    return PhaseForecast(
        start=_date_from_doy(target_year, ms) if ms is not None else None,
        peak=_date_from_doy(target_year, mp) if mp is not None else None,
        end=_date_from_doy(target_year, me) if me is not None else None,
        start_std_days=ss,
        peak_std_days=sp,
        end_std_days=se,
        years_used=max(len(starts), len(peaks), len(ends)),
    )


def marker_status(
    today: date,
    start: date,
    end: date,
    soon_days: int = 14,
) -> str:
    if start <= today <= end:
        return "active"
    if today < start <= today + timedelta(days=soon_days):
        return "soon"
    if today < start:
        return "future"
    return "ended"
