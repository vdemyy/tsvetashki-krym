"""Утилиты для Telegram-бота."""

from __future__ import annotations

from datetime import date

# Эмодзи для разных типов явлений
KIND_EMOJI = {
    "flowering": "🌺",
    "visual": "🌅",
    "harvest": "🍒",
    "animals": "🐬",
    "activity": "🎪",
    "default": "✨"
}

# Эмодзи для статусов
STATUS_EMOJI = {
    "active": "🔴",
    "soon": "🟡",
    "future": "⚪",
    "ended": "✅"
}


def get_kind_emoji(kind: str) -> str:
    """Возвращает эмодзи для типа явления."""
    return KIND_EMOJI.get(kind, KIND_EMOJI["default"])


def format_date_relative(target_date: date, today: date) -> str:
    """Форматирует дату с относительным указанием."""
    diff = (target_date - today).days

    if diff == 0:
        return "сегодня"
    elif diff == 1:
        return "завтра"
    elif diff == 2:
        return "послезавтра"
    elif 3 <= diff <= 7:
        return f"через {diff} дней"
    elif diff < 0:
        return f"{abs(diff)} дней назад"
    else:
        return target_date.strftime("%d.%m.%Y")


def escape_html(text: str) -> str:
    """Экранирует HTML спецсимволы."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_event_message(event, status: str, today: date) -> str:
    """Форматирует сообщение о событии с HTML."""
    ph = event.phenomenon
    pl = event.place

    emoji = get_kind_emoji(ph.kind)
    status_emoji = STATUS_EMOJI.get(status, "📌")

    # Индикатор интенсивности
    intensity_stars = "⭐" * event.intensity + "☆" * (5 - event.intensity)

    # Относительные даты
    start_relative = format_date_relative(event.start_date, today)
    peak_relative = format_date_relative(event.peak_date, today)
    end_relative = format_date_relative(event.end_date, today)

    status_text = ""
    if status == "active":
        status_text = "🔴 ИДЁТ ПРЯМО СЕЙЧАС"
    elif status == "soon":
        status_text = "🟡 НАЧИНАЕТСЯ СКОРО"
    elif status == "future":
        status_text = "⚪ ЗАПЛАНИРОВАНО"
    else:
        status_text = "✅ ЗАВЕРШЕНО"

    message = f"""<b>{emoji} {escape_html(ph.name)}</b> {status_emoji}

📍 <b>Место:</b> {escape_html(pl.name)}
🗺 <b>Регион:</b> {escape_html(pl.region or "Крым")}{f" · {escape_html(pl.subregion)}" if pl.subregion else ""}

📅 <b>Даты:</b>
• <b>Начало:</b> {event.start_date.strftime('%d.%m.%Y')} ({start_relative})
• <b>Пик:</b> {event.peak_date.strftime('%d.%m.%Y')} ({peak_relative})
• <b>Конец:</b> {event.end_date.strftime('%d.%m.%Y')} ({end_relative})

💪 <b>Интенсивность:</b> {intensity_stars} ({event.intensity}/5)

{status_emoji} <b>{status_text}</b>"""

    if ph.description:
        desc = escape_html(ph.description[:200])
        if len(ph.description) > 200:
            desc += "..."
        message += f"\n\n📝 <b>Описание:</b> {desc}"

    return message
