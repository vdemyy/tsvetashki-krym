"""Все хендлеры Telegram-бота с поддержкой интерактивных меню, каталога явлений и прогноза погоды."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo,
)
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Event, Phenomenon, Place, TelegramWatch
from services.forecast import marker_status
from telegram_bot.utils import (
    escape_html,
    get_kind_emoji,
    STATUS_EMOJI,
)

log = logging.getLogger("tsvetashki.tg.handlers")

# URL основного сайта для Telegram WebApp
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://tsvetashki-krym.ru").rstrip("/")

# Русский перевод для типов явлений
KIND_RU_MAP = {
    "flowering": "🌸 Цветение",
    "visual": "🌅 Визуальные явления",
    "harvest": "🍒 Урожай",
    "animals": "🐬 Животные",
    "activity": "🎪 События и фестивали",
}


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт главную клавиатуру."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои подписки"), KeyboardButton(text="📖 Все явления")],
            [KeyboardButton(text="📅 Что сегодня"), KeyboardButton(text="📆 Что на неделе")],
            [
                KeyboardButton(text="🗺️ Карта явлений", web_app=WebAppInfo(url=f"{WEBSITE_URL}/map?tg=1")),
                KeyboardButton(text="⛅ Погода в Крыму")
            ],
            [KeyboardButton(text="🔍 Найти явление"), KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ИНТЕРФЕЙСА ====================

def is_subscribed(db, chat_id: int, phenomenon_id: int) -> bool:
    """Проверяет подписку пользователя на конкретное явление."""
    return db.scalar(
        select(TelegramWatch).where(
            TelegramWatch.chat_id == chat_id,
            TelegramWatch.phenomenon_id == phenomenon_id
        )
    ) is not None


async def get_phenomenon_detail_text_and_keyboard(db, chat_id: int, ph_id: int, from_state: str) -> tuple[str, InlineKeyboardMarkup]:
    """Генерирует текст описания явления (с погодой для мест) и клавиатуру управления подпиской."""
    ph = db.get(Phenomenon, ph_id)
    if not ph:
        return "<b>❌ Явление не найдено.</b>", InlineKeyboardMarkup(inline_keyboard=[])

    emoji = get_kind_emoji(ph.kind)
    subscribed = is_subscribed(db, chat_id, ph_id)

    # Получаем будущие и активные события
    today = date.today()
    events = db.scalars(
        select(Event)
        .options(joinedload(Event.place))
        .where(Event.phenomenon_id == ph_id, Event.end_date >= today)
        .order_by(Event.start_date)
    ).all()

    text = f"<b>{emoji} {escape_html(ph.name)}</b>\n"
    if ph.category:
        text += f"📂 <b>Категория:</b> {escape_html(ph.category)}\n"
    text += f"📌 <b>Slug:</b> <code>{ph.slug}</code>\n"
    if ph.typical_season:
        text += f"📅 <b>Сезон:</b> {escape_html(ph.typical_season)}\n"
    if ph.water_temp_c:
        text += f"🌡️ <b>Температура воды:</b> ~{ph.water_temp_c}°C\n"
    if ph.website_url:
        text += f"🔗 <a href='{ph.website_url}'>Официальный сайт</a>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    if ph.description:
        text += f"📝 <b>Описание:</b>\n{escape_html(ph.description)}\n\n"

    if events:
        text += "📍 <b>Ближайшие места и погода:</b>\n\n"
        from services.weather import get_weather_details
        for ev in events:
            pl = ev.place
            status = marker_status(today, ev.start_date, ev.end_date)
            status_emoji = STATUS_EMOJI.get(status, "📌")
            
            # Индикатор интенсивности
            intensity_stars = "⭐" * ev.intensity + "☆" * (5 - ev.intensity)
            
            text += f"• <b>{escape_html(pl.name)}</b> ({escape_html(pl.region or 'Крым')})\n"
            text += f"  Даты: {ev.start_date.strftime('%d.%m.%Y')} — {ev.end_date.strftime('%d.%m.%Y')}\n"
            text += f"  Статус: {status_emoji} ({intensity_stars})\n"
            
            # Получаем текущую погоду для места
            try:
                w = await get_weather_details(pl.latitude, pl.longitude)
                if w and w.temp_c is not None:
                    desc_str = f", {w.weather_desc_ru}" if w.weather_desc_ru else ""
                    text += f"  Погода: 🌡️ {w.temp_c:.0f}°C{desc_str} (влажн. {w.humidity or 0}%, вет. {w.wind_speed_ms or 0:.1f} м/с)\n"
            except Exception:
                pass
            text += "\n"
    else:
        text += "⏳ <i>Даты на этот сезон пока не запланированы.</i>\n"

    # Формируем кнопки
    buttons = []
    
    # Кнопка подписки/отписки
    if subscribed:
        buttons.append([InlineKeyboardButton(text="🔕 Отписаться", callback_data=f"ph_unsub:{ph_id}:{from_state}")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ Подписаться на уведомления", callback_data=f"ph_sub:{ph_id}:{from_state}")])

    # Кнопка назад
    back_btn = None
    if from_state == "mine":
        back_btn = InlineKeyboardButton(text="🔙 Назад к подпискам", callback_data="nav_mine")
    elif from_state == "today":
        back_btn = InlineKeyboardButton(text="🔙 Назад к сегодня", callback_data="nav_today")
    elif from_state == "week":
        back_btn = InlineKeyboardButton(text="🔙 Назад к неделе", callback_data="nav_week")
    elif from_state.startswith("catalog_"):
        kind = from_state[8:]
        back_btn = InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"nav_catalog_kind:{kind}")
    elif from_state.startswith("search_"):
        query = from_state[7:]
        back_btn = InlineKeyboardButton(text="🔙 Назад к поиску", callback_data=f"nav_search:{query}")
    else:
        back_btn = InlineKeyboardButton(text="🔙 В начало", callback_data="nav_start")

    if back_btn:
        buttons.append([back_btn])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


def get_search_results_text_and_keyboard(db, query: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Ищет явления по запросу и возвращает сообщение со списком в виде инлайн-кнопок."""
    phenomena = db.scalars(
        select(Phenomenon)
        .where(
            or_(
                Phenomenon.name.ilike(f"%{query}%"),
                Phenomenon.description.ilike(f"%{query}%"),
                Phenomenon.slug.ilike(f"%{query}%")
            )
        )
        .limit(10)
    ).all()

    if not phenomena:
        text = f"""<b>❌ Ничего не найдено</b>

По запросу «<i>{escape_html(query)}</i>» явлений не найдено.

💡 Попробуйте ввести другое слово (например, <code>лаванда</code>, <code>маки</code>, <code>персики</code>)."""
        return text, None

    text = f"<b>🔍 Результаты поиска по запросу «{escape_html(query)}»:</b>\n\nВыберите интересующее явление из списка ниже:"
    
    buttons = []
    # Обрезаем запрос, чтобы callback_data влез в лимит 64 байта
    safe_query = query[:20]
    
    for ph in phenomena:
        emoji = get_kind_emoji(ph.kind)
        buttons.append([InlineKeyboardButton(text=f"{emoji} {ph.name}", callback_data=f"ph_view:{ph.id}:search_{safe_query}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


def get_today_text_and_keyboard(db) -> tuple[str, InlineKeyboardMarkup | None]:
    """Форматирует активные на сегодня события."""
    today = date.today()
    events = db.scalars(
        select(Event)
        .options(joinedload(Event.phenomenon), joinedload(Event.place))
        .where(Event.start_date <= today, Event.end_date >= today)
        .order_by(Event.phenomenon_id)
    ).unique().all()

    if not events:
        text = """<b>📅 Сегодня нет активных явлений</b>

Но вы можете посмотреть, что начнется скоро, отправив команду /week или нажав 📆 Что на неделе."""
        return text, None

    text = "<b>🔴 АКТИВНО СЕГОДНЯ 🔴</b>\n\n"
    buttons = []
    seen_ph = set()
    for event in events:
        ph = event.phenomenon
        pl = event.place
        emoji = get_kind_emoji(ph.kind)

        text += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
        text += f"   📍 {escape_html(pl.name)}\n"
        text += f"   🎯 Пик: {event.peak_date.strftime('%d.%m.%Y')}\n\n"
        
        if ph.id not in seen_ph:
            buttons.append([InlineKeyboardButton(text=f"{emoji} {ph.name}", callback_data=f"ph_view:{ph.id}:today")])
            seen_ph.add(ph.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


def get_week_text_and_keyboard(db) -> tuple[str, InlineKeyboardMarkup | None]:
    """Форматирует события на ближайшие 7 дней."""
    today = date.today()
    next_week = today + timedelta(days=7)
    events = db.scalars(
        select(Event)
        .options(joinedload(Event.phenomenon), joinedload(Event.place))
        .where(Event.start_date >= today, Event.start_date <= next_week)
        .order_by(Event.start_date)
    ).unique().all()

    if not events:
        text = """<b>📅 На следующей неделе нет запланированных событий</b>

Попробуйте воспользоваться поиском, отправив любое слово (например, <code>лаванда</code>)."""
        return text, None

    text = "<b>📆 СОБЫТИЯ НА НЕДЕЛЮ</b>\n\n"
    buttons = []
    seen_ph = set()
    for event in events:
        ph = event.phenomenon
        pl = event.place
        emoji = get_kind_emoji(ph.kind)
        days = (event.start_date - today).days

        if days == 0:
            day_str = "СЕГОДНЯ! 🔴"
        elif days == 1:
            day_str = "ЗАВТРА! 🟡"
        else:
            day_str = f"через {days} дней"

        text += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
        text += f"   📍 {escape_html(pl.name)}\n"
        text += f"   📅 Начало: <b>{day_str}</b>\n\n"

        if ph.id not in seen_ph:
            buttons.append([InlineKeyboardButton(text=f"{emoji} {ph.name}", callback_data=f"ph_view:{ph.id}:week")])
            seen_ph.add(ph.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


def get_mine_text_and_keyboard(db, chat_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Форматирует подписки пользователя."""
    today = date.today()
    watches = db.scalars(
        select(TelegramWatch).where(TelegramWatch.chat_id == chat_id)
    ).all()

    if not watches:
        text = """<b>📭 У вас пока нет подписок</b>

Чтобы подписаться, воспользуйтесь поиском, выберите явление и нажмите кнопку подписки."""
        return text, None

    phenomenon_ids = [w.phenomenon_id for w in watches]
    phenomena = db.scalars(
        select(Phenomenon).where(Phenomenon.id.in_(phenomenon_ids))
    ).all()
    phenomena = sorted(phenomena, key=lambda x: x.name)

    text = "<b>📋 ВАШИ ПОДПИСКИ</b>\n\nНажмите на явление ниже для просмотра дат и управления подпиской:\n\n"
    buttons = []
    for ph in phenomena:
        event = db.scalar(
            select(Event)
            .where(
                Event.phenomenon_id == ph.id,
                Event.end_date >= today - timedelta(days=30)
            )
            .order_by(Event.start_date)
        )

        emoji = get_kind_emoji(ph.kind)
        text += f"{emoji} <b>{escape_html(ph.name)}</b>\n"

        if event:
            status = marker_status(today, event.start_date, event.end_date)
            if status == "active":
                text += f"   🔴 <b>ИДЁТ СЕЙЧАС!</b>\n"
            elif status == "soon":
                days = (event.start_date - today).days
                text += f"   🟡 Начнётся через {days} дней\n"
            elif status == "future":
                text += f"   ⚪ Старт: {event.start_date.strftime('%d.%m.%Y')}\n"
            else:
                text += f"   ✅ Закончилось: {event.end_date.strftime('%d.%m.%Y')}\n"
        else:
            text += f"   ⏳ Даты ожидаются\n"
        text += "\n"

        buttons.append([InlineKeyboardButton(text=f"{emoji} {ph.name}", callback_data=f"ph_view:{ph.id}:mine")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


# ==================== ФУНКЦИИ КАТАЛОГА (ВСЕ ЯВЛЕНИЯ) ====================

def get_catalog_text_and_keyboard() -> tuple[str, InlineKeyboardMarkup]:
    """Генерирует список категорий каталога явлений."""
    text = "<b>📖 Каталог природных явлений Крыма</b>\n\nВыберите интересующую категорию:"
    buttons = [
        [InlineKeyboardButton(text="🌸 Цветение", callback_data="nav_catalog_kind:flowering")],
        [InlineKeyboardButton(text="🌅 Визуальные явления", callback_data="nav_catalog_kind:visual")],
        [InlineKeyboardButton(text="🍒 Урожай", callback_data="nav_catalog_kind:harvest")],
        [InlineKeyboardButton(text="🐬 Животные", callback_data="nav_catalog_kind:animals")],
        [InlineKeyboardButton(text="🎪 События и фестивали", callback_data="nav_catalog_kind:activity")]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


def get_catalog_kind_text_and_keyboard(db, kind: str) -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает список явлений в выбранной категории."""
    phenomena = db.scalars(
        select(Phenomenon).where(Phenomenon.kind == kind).order_by(Phenomenon.name)
    ).all()
    
    kind_ru = KIND_RU_MAP.get(kind, kind)
    if not phenomena:
        text = f"<b>{kind_ru}</b>\n\nВ этой категории пока нет добавленных явлений."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в каталог", callback_data="nav_catalog")]
        ])
        return text, keyboard
        
    text = f"<b>{kind_ru}</b>\n\nВыберите конкретное явление для просмотра описания, типичного сезона и оформления уведомлений:"
    buttons = []
    for ph in phenomena:
        buttons.append([InlineKeyboardButton(text=ph.name, callback_data=f"ph_view:{ph.id}:catalog_{kind}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в каталог", callback_data="nav_catalog")])
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ФУНКЦИИ ПОГОДЫ ====================

def get_weather_main_text_and_keyboard(db) -> tuple[str, InlineKeyboardMarkup]:
    """Создает главное меню просмотра погоды по регионам."""
    regions = db.scalars(select(Place.region).distinct().where(Place.region.isnot(None))).all()
    regions = sorted([r for r in regions if r])
    
    text = "<b>⛅ Погода в местах наблюдения Крыма</b>\n\nВыберите интересующий регион для просмотра прогноза:"
    buttons = []
    for r in regions:
        buttons.append([InlineKeyboardButton(text=f"📍 {r}", callback_data=f"nav_weather_region:{r}")])
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


def get_weather_region_text_and_keyboard(db, region: str) -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает список мест для просмотра погоды в конкретном регионе."""
    places = db.scalars(select(Place).where(Place.region == region).order_by(Place.name)).all()
    
    text = f"<b>⛅ Погода в регионе: {escape_html(region)}</b>\n\nВыберите локацию для получения актуальной сводки погоды:"
    buttons = []
    for pl in places:
        buttons.append([InlineKeyboardButton(text=pl.name, callback_data=f"weather_show:{pl.id}:{region}")])
    buttons.append([InlineKeyboardButton(text="🔙 К выбору региона", callback_data="nav_weather")])
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_weather_detail_text_and_keyboard(db, place_id: int, region: str) -> tuple[str, InlineKeyboardMarkup]:
    """Получает детальный прогноз погоды для конкретного места наблюдения."""
    from services.weather import get_weather_details, rain_hint
    
    pl = db.get(Place, place_id)
    if not pl:
        return "<b>❌ Место наблюдения не найдено.</b>", InlineKeyboardMarkup(inline_keyboard=[])
        
    text = f"<b>⛅ Текущая погода: {escape_html(pl.name)}</b>\n"
    text += f"🗺️ Регион: {escape_html(pl.region or 'Крым')}"
    if pl.subregion:
        text += f" · {escape_html(pl.subregion)}"
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 1. Сводка погоды
    try:
        w = await get_weather_details(pl.latitude, pl.longitude)
        if w:
            feels_str = f" (ощущается как {w.feels_like_c:.0f}°C)" if w.feels_like_c is not None else ""
            desc = f" ({w.weather_desc_ru})" if w.weather_desc_ru else ""
            text += f"🌡️ <b>Температура:</b> {w.temp_c:.1f}°C{feels_str}\n"
            text += f"☁️ <b>Состояние:</b> {w.weather_main or 'ясно'}{desc}\n"
            text += f"💧 <b>Влажность:</b> {w.humidity or 0}%\n"
            text += f"💨 <b>Ветер:</b> {w.wind_speed_ms or 0:.1f} м/с\n"
            if w.visibility_km is not None:
                text += f"👁️ <b>Видимость:</b> {w.visibility_km:.1f} км\n"
            if w.pressure_hpa is not None:
                text += f"🎈 <b>Давление:</b> {w.pressure_hpa} гПа\n"
        else:
            text += "⚠️ <i>Не удалось получить текущие метеоданные.</i>\n"
    except Exception as e:
        log.exception(f"Error fetching details: {e}")
        text += "⚠️ <i>Не удалось получить текущие метеоданные.</i>\n"
        
    text += "\n"
    
    # 2. Осадки
    try:
        hint = await rain_hint(pl.latitude, pl.longitude)
        if hint.message:
            text += f"🌧️ <b>Осадки:</b> {hint.message}\n"
        elif hint.raw_summary:
            text += f"🌧️ <b>Осадки:</b> {hint.raw_summary}\n"
    except Exception:
        pass
        
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Обновлено по данным OpenWeather</i>"
    
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Обновить данные", callback_data=f"weather_refresh:{place_id}:{region}"),
            InlineKeyboardButton(text="🔙 К выбору места", callback_data=f"nav_weather_region:{region}")
        ]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ КОМАНД ====================

def register_handlers(dp) -> None:
    """Регистрирует все хендлеры на диспатчере."""

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        text = """<b>🌸 ДОБРО ПОЖАЛОВАТЬ В ЦВЕТАШКИ КРЫМ!</b> 🌸

Я помогу вам <b>не пропустить</b> самые красивые сезонные явления Крыма (цветение лаванды, маков, сакуры, звездопады и многое другое).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Как пользоваться ботом:</b>
• Просто отправьте мне <b>любое слово</b> (например, <code>лаванда</code> или <code>маки</code>) для поиска!
• Используйте интерактивные кнопки меню на клавиатуре ниже.

<b>📋 Дополнительные команды:</b>
▪️ <b>/map</b> — интерактивная карта явлений 🗺️
▪️ <b>/all</b> — каталог всех явлений
▪️ <b>/weather</b> — погода в местах наблюдения
▪️ <b>/mine</b> — показать мои подписки
▪️ <b>/today</b> — что происходит сегодня
▪️ <b>/week</b> — события на неделю
▪️ <b>/help</b> — справка по командам

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Используйте кнопки меню для быстрой навигации!</i>"""

        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        text = """<b>❓ ПОМОЩЬ ПО КОМАНДАМ БОТА</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📋 Управление подписками:</b>
▪️ <b>/mine</b> — список моих подписок и быстрая отписка
▪️ <b>/follow</b> <i>&lt;slug&gt;</i> — подписаться по текстовому коду
▪️ <b>/unfollow</b> <i>&lt;slug&gt;</i> — отписаться по текстовому коду

<b>🔍 Поиск и информация:</b>
▪️ <b>Отправьте любое слово</b> напрямую боту для быстрого поиска явлений!
▪️ <b>/map</b> — интерактивная карта явлений (Mini App) 🗺️
▪️ <b>/all</b> — интерактивный каталог всех явлений по категориям
▪️ <b>/weather</b> — погода в ключевых точках полуострова
▪️ <b>/today</b> — активные явления на сегодня
▪️ <b>/week</b> — явления на ближайшие 7 дней
▪️ <b>/about</b> — информация о проекте

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Пример использования текстовых кодов: /follow lavanda-turgenevka</i>"""

        await message.answer(text, parse_mode=ParseMode.HTML)

    @dp.message(Command("map"))
    async def cmd_map(message: Message) -> None:
        text = """<b>🗺️ Карта сезонных явлений Крыма</b>

Откройте интерактивную карту, чтобы увидеть, где прямо сейчас цветут маки, лаванда, сакура или происходят другие интересные явления!"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗺️ Открыть карту", web_app=WebAppInfo(url=f"{WEBSITE_URL}/map?tg=1"))]
        ])
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    @dp.message(Command("follow"))
    async def cmd_follow(message: Message, command: CommandObject) -> None:
        slug = command.args.strip() if command and command.args else None

        if not slug:
            text = """<b>🌸 Как подписаться:</b>

Используйте команду:
<b>/follow</b> <i>&lt;slug&gt;</i>

<i>Пример: /follow lavanda-turgenevka</i>

💡 Чтобы узнать slug явления, воспользуйтесь поиском (просто отправьте боту название)."""

            await message.answer(text, parse_mode=ParseMode.HTML)
            return

        db = SessionLocal()
        try:
            phenomenon = db.scalars(
                select(Phenomenon).where(Phenomenon.slug == slug)
            ).first()

            if not phenomenon:
                similar = db.scalars(
                    select(Phenomenon)
                    .where(Phenomenon.name.ilike(f"%{slug}%"))
                    .limit(5)
                ).all()

                if similar:
                    similar_list = "\n".join([f"▪️ <code>{ph.slug}</code> — {escape_html(ph.name)}" for ph in similar])
                    text = f"""<b>❌ Явление не найдено</b>

По коду <code>{escape_html(slug)}</code> ничего не найдено.

<b>🔍 Возможно, вы имели в виду:</b>
{similar_list}

💡 Чтобы подписаться, скопируйте нужный код и отправьте /follow &lt;код&gt;"""
                else:
                    text = f"""<b>❌ Явление не найдено</b>

Код <code>{escape_html(slug)}</code> не существует."""

                await message.answer(text, parse_mode=ParseMode.HTML)
                return

            existing = db.scalar(
                select(TelegramWatch).where(
                    TelegramWatch.chat_id == message.chat.id,
                    TelegramWatch.phenomenon_id == phenomenon.id
                )
            )

            if existing:
                text = f"""<b>⚠️ Вы уже подписаны</b>

Вы уже получаете уведомления о явлении <b>{escape_html(phenomenon.name)}</b>.

🔕 Чтобы отписаться: /unfollow {phenomenon.slug}"""

                await message.answer(text, parse_mode=ParseMode.HTML)
                return

            watch = TelegramWatch(chat_id=message.chat.id, phenomenon_id=phenomenon.id)
            db.add(watch)
            db.commit()

            today = date.today()
            event = db.scalar(
                select(Event)
                .where(Event.phenomenon_id == phenomenon.id, Event.end_date >= today)
                .order_by(Event.start_date)
            )

            emoji = get_kind_emoji(phenomenon.kind)
            response = f"""<b>{emoji} ВЫ УСПЕШНО ПОДПИСАЛИСЬ! {emoji}</b>

Вы подписались на уведомления о явлении <b>{escape_html(phenomenon.name)}</b>.

📌 <b>Код явления:</b> <code>{phenomenon.slug}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

            if event:
                status = marker_status(today, event.start_date, event.end_date)
                if status == "active":
                    response += f"\n\n🔴 <b>Прямо сейчас</b> это явление <b>активно</b>!"
                elif status == "soon":
                    days = (event.start_date - today).days
                    response += f"\n\n🟡 <b>Начинается через {days} дней</b> — скоро вам придет оповещение!"
                elif status == "future":
                    response += f"\n\n⚪ <b>Запланировано</b> на {event.start_date.strftime('%d.%m.%Y')}"
                else:
                    response += f"\n\n📅 Следите за обновлениями"
            else:
                response += f"\n\n📅 Уведомления придут при установке новых дат цветения"

            response += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<i>Управлять подписками: /mine</i>"

            await message.answer(response, parse_mode=ParseMode.HTML)
            log.info(f"Пользователь {message.chat.id} подписался на {phenomenon.slug}")

        except Exception as e:
            log.exception(f"Ошибка при подписке: {e}")
            await message.answer(
                "<b>❌ Произошла ошибка</b>\n\nНе удалось оформить подписку. Попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            db.rollback()
        finally:
            db.close()

    @dp.message(Command("unfollow"))
    async def cmd_unfollow(message: Message, command: CommandObject) -> None:
        slug = command.args.strip() if command and command.args else None

        if not slug:
            text = """<b>🔕 Как отписаться:</b>

Используйте команду:
<b>/unfollow</b> <i>&lt;slug&gt;</i>

<i>Пример: /unfollow lavanda-turgenevka</i>

💡 Чтобы увидеть ваши подписки: /mine"""

            await message.answer(text, parse_mode=ParseMode.HTML)
            return

        db = SessionLocal()
        try:
            phenomenon = db.scalars(
                select(Phenomenon).where(Phenomenon.slug == slug)
            ).first()

            if not phenomenon:
                text = f"""<b>❌ Явление не найдено</b>

Код <code>{escape_html(slug)}</code> не существует. Проверьте правильность написания."""

                await message.answer(text, parse_mode=ParseMode.HTML)
                return

            watch = db.scalar(
                select(TelegramWatch).where(
                    TelegramWatch.chat_id == message.chat.id,
                    TelegramWatch.phenomenon_id == phenomenon.id
                )
            )

            if not watch:
                text = f"""<b>❌ Вы не были подписаны</b>

Вы не подписаны на явление <b>{escape_html(phenomenon.name)}</b>."""

                await message.answer(text, parse_mode=ParseMode.HTML)
                return

            db.delete(watch)
            db.commit()

            emoji = get_kind_emoji(phenomenon.kind)
            text = f"""<b>{emoji} ВЫ ОТПИСАЛИСЬ {emoji}</b>

Вы больше не будете получать уведомления о явлении <b>{escape_html(phenomenon.name)}</b>."""

            await message.answer(text, parse_mode=ParseMode.HTML)

        except Exception as e:
            log.exception(f"Ошибка при отписке: {e}")
            await message.answer(
                "<b>❌ Произошла ошибка</b>\n\nНе удалось отписаться. Попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            db.rollback()
        finally:
            db.close()

    @dp.message(Command("mine"))
    async def cmd_mine(message: Message) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_mine_text_and_keyboard(db, message.chat.id)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка при получении подписок: {e}")
            await message.answer("<b>❌ Не удалось загрузить ваши подписки.</b>", parse_mode=ParseMode.HTML)
        finally:
            db.close()

    @dp.message(Command("today"))
    async def cmd_today(message: Message) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_today_text_and_keyboard(db)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка в /today: {e}")
            await message.answer("<b>❌ Произошла ошибка при загрузке событий дня.</b>", parse_mode=ParseMode.HTML)
        finally:
            db.close()

    @dp.message(Command("week"))
    async def cmd_week(message: Message) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_week_text_and_keyboard(db)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка в /week: {e}")
            await message.answer("<b>❌ Произошла ошибка при загрузке событий недели.</b>", parse_mode=ParseMode.HTML)
        finally:
            db.close()

    @dp.message(Command("search"))
    async def cmd_search(message: Message, command: CommandObject) -> None:
        query = command.args.strip() if command and command.args else None

        if not query:
            text = """<b>🔍 Как искать:</b>

Введите команду с запросом:
<b>/search</b> <i>&lt;текст&gt;</i>

<i>Пример: /search лаванда</i>

💡 Также вы можете просто отправить любое слово боту напрямую без всяких команд!"""

            await message.answer(text, parse_mode=ParseMode.HTML)
            return

        db = SessionLocal()
        try:
            text, keyboard = get_search_results_text_and_keyboard(db, query)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка в /search: {e}")
            await message.answer("<b>❌ Не удалось выполнить поиск.</b>", parse_mode=ParseMode.HTML)
        finally:
            db.close()

    @dp.message(Command("all"))
    async def cmd_catalog(message: Message) -> None:
        text, keyboard = get_catalog_text_and_keyboard()
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    @dp.message(Command("weather"))
    async def cmd_weather(message: Message) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_weather_main_text_and_keyboard(db)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка при вызове погоды: {e}")
            await message.answer("<b>❌ Не удалось открыть меню погоды.</b>", parse_mode=ParseMode.HTML)
        finally:
            db.close()

    @dp.message(Command("about"))
    async def cmd_about(message: Message) -> None:
        text = """<b>ℹ️ О ПРОЕКТЕ</b>

<b>🌸 Цветашки Крым</b> — ваш персональный проводник по природным сезонам полуострова.

Мы отслеживаем даты цветения полей, садов, периоды активности редких животных, красивейшие визуальные явления на яйлах и у берегов моря, помогая вам вовремя планировать поездки.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📞 Контакты:</b>
• Разработчик: @videmyy
• Почта: videmyy@gmail.com

<i>Вернуться в начало: /start</i>"""

        await message.answer(text, parse_mode=ParseMode.HTML)


    # ==================== CALLBACK QUERY HANDLERS (ИНЛАЙН КНОПКИ) ====================

    @dp.callback_query(F.data.startswith("ph_view:"))
    async def callback_ph_view(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        ph_id = int(parts[1])
        from_state = parts[2]

        db = SessionLocal()
        try:
            text, keyboard = await get_phenomenon_detail_text_and_keyboard(db, callback.message.chat.id, ph_id, from_state)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при просмотре деталей явления: {e}")
            await callback.answer("Ошибка при загрузке данных.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("ph_sub:"))
    async def callback_ph_sub(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        ph_id = int(parts[1])
        from_state = parts[2]
        chat_id = callback.message.chat.id

        db = SessionLocal()
        try:
            phenomenon = db.get(Phenomenon, ph_id)
            if not phenomenon:
                await callback.answer("Явление не найдено.", show_alert=True)
                db.close()
                return

            existing = db.scalar(
                select(TelegramWatch).where(
                    TelegramWatch.chat_id == chat_id,
                    TelegramWatch.phenomenon_id == ph_id
                )
            )

            if not existing:
                watch = TelegramWatch(chat_id=chat_id, phenomenon_id=ph_id)
                db.add(watch)
                db.commit()
                await callback.answer(f"Вы подписались на «{phenomenon.name}»! 🔔")
            else:
                await callback.answer("Вы уже подписаны.")

            # Обновляем страницу с описанием
            text, keyboard = await get_phenomenon_detail_text_and_keyboard(db, chat_id, ph_id, from_state)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
        except Exception as e:
            log.exception(f"Ошибка при подписке в callback: {e}")
            await callback.answer("Не удалось подписаться. Попробуйте позже.", show_alert=True)
            db.rollback()
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("ph_unsub:"))
    async def callback_ph_unsub(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        ph_id = int(parts[1])
        from_state = parts[2]
        chat_id = callback.message.chat.id

        db = SessionLocal()
        try:
            phenomenon = db.get(Phenomenon, ph_id)
            if not phenomenon:
                await callback.answer("Явление не найдено.", show_alert=True)
                db.close()
                return

            watch = db.scalar(
                select(TelegramWatch).where(
                    TelegramWatch.chat_id == chat_id,
                    TelegramWatch.phenomenon_id == ph_id
                )
            )

            if watch:
                db.delete(watch)
                db.commit()
                await callback.answer(f"Вы отписались от «{phenomenon.name}» 🔕")
            else:
                await callback.answer("Вы не были подписаны.")

            # Обновляем страницу с описанием
            text, keyboard = await get_phenomenon_detail_text_and_keyboard(db, chat_id, ph_id, from_state)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
        except Exception as e:
            log.exception(f"Ошибка при отписке в callback: {e}")
            await callback.answer("Не удалось отписаться. Попробуйте позже.", show_alert=True)
            db.rollback()
        finally:
            db.close()

    @dp.callback_query(F.data == "nav_mine")
    async def callback_nav_mine(callback: CallbackQuery) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_mine_text_and_keyboard(db, callback.message.chat.id)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к подпискам: {e}")
            await callback.answer("Не удалось загрузить подписки.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data == "nav_today")
    async def callback_nav_today(callback: CallbackQuery) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_today_text_and_keyboard(db)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к сегодня: {e}")
            await callback.answer("Не удалось загрузить события дня.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data == "nav_week")
    async def callback_nav_week(callback: CallbackQuery) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_week_text_and_keyboard(db)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к неделе: {e}")
            await callback.answer("Не удалось загрузить события недели.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("nav_search:"))
    async def callback_nav_search(callback: CallbackQuery) -> None:
        query = callback.data.split(":", 1)[1]
        db = SessionLocal()
        try:
            text, keyboard = get_search_results_text_and_keyboard(db, query)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к поиску: {e}")
            await callback.answer("Не удалось загрузить результаты поиска.", show_alert=True)
        finally:
            db.close()

    # Catalog Callbacks
    @dp.callback_query(F.data == "nav_catalog")
    async def callback_nav_catalog(callback: CallbackQuery) -> None:
        try:
            text, keyboard = get_catalog_text_and_keyboard()
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к каталогу: {e}")
            await callback.answer("Не удалось загрузить каталог.", show_alert=True)

    @dp.callback_query(F.data.startswith("nav_catalog_kind:"))
    async def callback_nav_catalog_kind(callback: CallbackQuery) -> None:
        kind = callback.data.split(":")[1]
        db = SessionLocal()
        try:
            text, keyboard = get_catalog_kind_text_and_keyboard(db, kind)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при загрузке явлений категории: {e}")
            await callback.answer("Не удалось загрузить категорию.", show_alert=True)
        finally:
            db.close()

    # Weather Callbacks
    @dp.callback_query(F.data == "nav_weather")
    async def callback_nav_weather(callback: CallbackQuery) -> None:
        db = SessionLocal()
        try:
            text, keyboard = get_weather_main_text_and_keyboard(db)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к погоде: {e}")
            await callback.answer("Не удалось загрузить список регионов.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("nav_weather_region:"))
    async def callback_nav_weather_region(callback: CallbackQuery) -> None:
        region = callback.data.split(":", 1)[1]
        db = SessionLocal()
        try:
            text, keyboard = get_weather_region_text_and_keyboard(db, region)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при загрузке мест региона: {e}")
            await callback.answer("Не удалось загрузить локации.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("weather_show:"))
    async def callback_weather_show(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        place_id = int(parts[1])
        region = parts[2]
        db = SessionLocal()
        try:
            text, keyboard = await get_weather_detail_text_and_keyboard(db, place_id, region)
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при просмотре погоды места: {e}")
            await callback.answer("Не удалось загрузить погоду.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("weather_refresh:"))
    async def callback_weather_refresh(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        place_id = int(parts[1])
        region = parts[2]
        db = SessionLocal()
        try:
            text, keyboard = await get_weather_detail_text_and_keyboard(db, place_id, region)
            from aiogram.exceptions import TelegramBadRequest
            try:
                await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
                await callback.answer("Данные погоды обновлены! 🔄")
            except TelegramBadRequest as e:
                if "message is not modified" in str(e).lower():
                    await callback.answer("Погода уже актуальна! 👌")
                else:
                    raise e
        except Exception as e:
            log.exception(f"Ошибка при обновлении погоды: {e}")
            await callback.answer("Не удалось обновить погоду.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data == "nav_start")
    async def callback_nav_start(callback: CallbackQuery) -> None:
        try:
            start_text = """<b>🌸 ДОБРО ПОЖАЛОВАТЬ В ЦВЕТАШКИ КРЫМ!</b> 🌸

Я помогу вам <b>не пропустить</b> самые красивые сезонные явления Крыма.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Как пользоваться ботом:</b>
• Просто отправьте мне <b>любое слово</b> (например, <code>лаванда</code> или <code>маки</code>) для поиска!
• Нажимайте интерактивные кнопки меню на клавиатуре ниже.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Используйте кнопки меню для быстрой навигации!</i>"""
            await callback.message.edit_text(start_text, parse_mode=ParseMode.HTML)
            await callback.answer()
        except Exception as e:
            log.exception(f"Ошибка при возврате к старту: {e}")
            await callback.answer()


    # ==================== ОБРАБОТКА ТЕКСТОВЫХ КНОПОК И ПОИСКА ====================

    @dp.message(F.text == "📋 Мои подписки")
    async def handle_my_subscriptions_button(message: Message) -> None:
        await cmd_mine(message)

    @dp.message(F.text == "📖 Все явления")
    async def handle_catalog_button(message: Message) -> None:
        await cmd_catalog(message)

    @dp.message(F.text == "📅 Что сегодня")
    async def handle_today_button(message: Message) -> None:
        await cmd_today(message)

    @dp.message(F.text == "📆 Что на неделе")
    async def handle_week_button(message: Message) -> None:
        await cmd_week(message)

    @dp.message(F.text == "🔍 Найти явление")
    async def handle_search_button(message: Message) -> None:
        await message.answer(
            "<b>🔍 Поиск явлений</b>\n\nПросто <b>отправьте мне название</b> (или часть слова), например:\n<code>лаванда</code>, <code>сакура</code>, <code>маки</code> или <code>дельфины</code>.\n\nЯ найду все совпадения!",
            parse_mode=ParseMode.HTML
        )

    @dp.message(F.text == "⛅ Погода в Крыму")
    async def handle_weather_button(message: Message) -> None:
        await cmd_weather(message)

    @dp.message(F.text == "❓ Помощь")
    async def handle_help_button(message: Message) -> None:
        await cmd_help(message)

    @dp.message(F.text == "ℹ️ О боте")
    async def handle_about_button(message: Message) -> None:
        await cmd_about(message)

    # Fallback-обработчик для любого текста (воспринимается как поисковый запрос)
    BUTTON_TEXTS = {
        "📋 Мои подписки", "📖 Все явления",
        "📅 Что сегодня", "📆 Что на неделе",
        "🔍 Найти явление", "⛅ Погода в Крыму",
        "❓ Помощь", "ℹ️ О боте"
    }

    @dp.message(F.text & ~F.text.startswith("/"))
    async def handle_text_search(message: Message) -> None:
        if message.text in BUTTON_TEXTS:
            return
        
        query = message.text.strip()
        db = SessionLocal()
        try:
            text, keyboard = get_search_results_text_and_keyboard(db, query)
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            log.exception(f"Ошибка при свободном текстовом поиске: {e}")
            await message.answer(
                "<b>❌ Произошла ошибка</b>\n\nНе удалось выполнить поиск. Попробуйте другое слово.",
                parse_mode=ParseMode.HTML
            )
        finally:
            db.close()
