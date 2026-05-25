# Прогноз фаз по историческим данным

import statistics
from datetime import date, datetime, timedelta


def _parse_date(value):
    """Парсит дату из разных форматов"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    
    s = str(value).strip()
    if not s:
        return None
    
    # Пробуем разные форматы
    formats = ["%Y-%m-%d", "%d.%m.%Y", "%m-%d", "%d.%m"]
    for fmt in formats:
        try:
            if fmt == "%m-%d":
                y = date.today().year
                return datetime.strptime(f"{y}-{s}", "%Y-%m-%d").date()
            return datetime.strptime(s, fmt).date()
        except:
            continue
    
    return None


def _doy(d):
    """Возвращает день года (1-365)"""
    return float(d.timetuple().tm_yday)


def _date_from_doy(year, doy):
    """Создает дату из года и дня года"""
    d0 = date(year, 1, 1)
    return d0 + timedelta(days=int(round(doy)) - 1)


class PhaseForecast:
    """Прогноз фаз явления"""
    def __init__(self, start, peak, end, start_std, peak_std, end_std, years_used):
        self.start = start
        self.peak = peak
        self.end = end
        self.start_std_days = start_std
        self.peak_std_days = peak_std
        self.end_std_days = end_std
        self.years_used = years_used


def forecast_from_history(phase_history, target_year=None):
    """Создает прогноз на основе исторических данных"""
    if not phase_history:
        return None
    
    if not target_year:
        target_year = date.today().year
    
    starts = []
    peaks = []
    ends = []
    
    # Собираем данные из истории
    for row in phase_history:
        if not isinstance(row, dict):
            continue
        
        y = row.get("year") or row.get("y")
        start = _parse_date(row.get("start") or row.get("s"))
        peak = _parse_date(row.get("peak") or row.get("p"))
        end = _parse_date(row.get("end") or row.get("e"))
        
        # Корректируем год если нужно
        if y and isinstance(y, int):
            if start and start.year != y:
                start = start.replace(year=y)
            if peak and peak.year != y:
                peak = peak.replace(year=y)
            if end and end.year != y:
                end = end.replace(year=y)
        
        # Добавляем дни года
        if start:
            starts.append(_doy(start))
        if peak:
            peaks.append(_doy(peak))
        if end:
            ends.append(_doy(end))
    
    if not starts and not peaks and not ends:
        return None
    
    # Считаем среднее и стандартное отклонение
    def calc_stats(values):
        if not values:
            return None, None
        if len(values) == 1:
            return values[0], 0.0
        return statistics.mean(values), statistics.pstdev(values)
    
    ms, ss = calc_stats(starts)
    mp, sp = calc_stats(peaks)
    me, se = calc_stats(ends)
    
    return PhaseForecast(
        start=_date_from_doy(target_year, ms) if ms is not None else None,
        peak=_date_from_doy(target_year, mp) if mp is not None else None,
        end=_date_from_doy(target_year, me) if me is not None else None,
        start_std=ss,
        peak_std=sp,
        end_std=se,
        years_used=max(len(starts), len(peaks), len(ends))
    )


def marker_status(today, start, end, soon_days=14):
    """Определяет статус события"""
    if start <= today <= end:
        return "active"
    if today < start <= today + timedelta(days=soon_days):
        return "soon"
    if today < start:
        return "future"
    return "ended"
