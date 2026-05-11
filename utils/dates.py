from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class PhaseTimers:
    label: str
    days: int | None


def timers_for_phases(today: date, start: date, peak: date, end: date) -> list[PhaseTimers]:
    out: list[PhaseTimers] = []
    if today < start:
        out.append(PhaseTimers("до начала", (start - today).days))
        out.append(PhaseTimers("до пика", (peak - today).days))
        out.append(PhaseTimers("до конца", (end - today).days))
    elif today < peak:
        out.append(PhaseTimers("до пика", (peak - today).days))
        out.append(PhaseTimers("до конца", (end - today).days))
    elif today <= end:
        out.append(PhaseTimers("до конца", (end - today).days))
        out.append(PhaseTimers("после пика", (today - peak).days))
    else:
        out.append(PhaseTimers("сезон завершён", None))
    return out


def feed_window_days() -> int:
    return 7


def event_in_feed(today: date, start: date, end: date, upcoming_days: int = 7) -> bool:
    if start <= today <= end:
        return True
    if today < start <= today + timedelta(days=upcoming_days):
        return True
    return False
