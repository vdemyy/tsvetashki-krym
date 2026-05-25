# Работа с датами и таймерами

from datetime import date, timedelta


class PhaseTimers:
    """Таймеры для фаз события"""
    def __init__(self, label, days):
        self.label = label
        self.days = days


def timers_for_phases(today, start, peak, end):
    """Создает таймеры для разных фаз события"""
    timers = []
    
    if today < start:
        # До начала
        timers.append(PhaseTimers("до начала", (start - today).days))
        timers.append(PhaseTimers("до пика", (peak - today).days))
        timers.append(PhaseTimers("до конца", (end - today).days))
    elif today < peak:
        # Между началом и пиком
        timers.append(PhaseTimers("до пика", (peak - today).days))
        timers.append(PhaseTimers("до конца", (end - today).days))
    elif today <= end:
        # Между пиком и концом
        timers.append(PhaseTimers("до конца", (end - today).days))
        timers.append(PhaseTimers("после пика", (today - peak).days))
    else:
        # После конца
        timers.append(PhaseTimers("сезон завершён", None))
    
    return timers


def feed_window_days():
    """Возвращает количество дней для ленты"""
    return 7


def event_in_feed(today, start, end, upcoming_days=7):
    """Проверяет попадает ли событие в ленту"""
    # Событие идет сейчас
    if start <= today <= end:
        return True
    
    # Событие начнется скоро
    if today < start <= today + timedelta(days=upcoming_days):
        return True
    
    return False
