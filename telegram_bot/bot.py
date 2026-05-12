"""
Telegram-бот для подписок на сезонные явления с автоматическими уведомлениями.

Функции:
- Подписка/отписка на явления
- Ежедневная проверка изменения статусов событий
- Красивые форматированные сообщения с эмодзи и HTML
- Умные уведомления: начало, пик, конец, напоминания
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session, joinedload

from database import SessionLocal
from models import Event, Phenomenon, Place, TelegramWatch
from services.forecast import marker_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("tsvetashki.tg")

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

# Цветные статусы для HTML
STATUS_COLOR = {
    "active": "🟠",
    "soon": "🟡",
    "future": "⚪",
    "ended": "✅"
}


@dataclass
class EventStatusChange:
    """Изменение статуса события для уведомления."""
    event_id: int
    phenomenon_name: str
    phenomenon_slug: str
    place_name: str
    region: str
    old_status: str
    new_status: str
    start_date: date
    peak_date: date
    end_date: date
    intensity: int
    days_until: Optional[int] = None


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


def format_event_message(event: Event, status: str, today: date, include_buttons: bool = False) -> str:
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


class NotificationService:
    """Сервис для проверки и отправки уведомлений."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self._last_check_status: Dict[int, str] = {}
    
    async def check_and_notify(self) -> None:
        """Проверяет события и отправляет уведомления."""
        db = SessionLocal()
        today = date.today()
        
        try:
            future_limit = today + timedelta(days=30)
            events = db.scalars(
                select(Event)
                .options(joinedload(Event.phenomenon), joinedload(Event.place))
                .where(
                    or_(
                        Event.end_date >= today,
                        and_(
                            Event.start_date > today,
                            Event.start_date <= future_limit
                        )
                    )
                )
            ).unique().all()
            
            for event in events:
                new_status = marker_status(today, event.start_date, event.end_date)
                old_status = self._last_check_status.get(event.id)
                
                if old_status != new_status:
                    self._last_check_status[event.id] = new_status
                    await self._notify_subscribers(event, new_status, today)
                    
                    # Напоминание о пике
                    days_to_peak = (event.peak_date - today).days
                    if 1 <= days_to_peak <= 3 and new_status != "ended":
                        await self._send_peak_reminder(event, today, days_to_peak)
                        
        except Exception as e:
            log.exception(f"Ошибка при проверке уведомлений: {e}")
        finally:
            db.close()
    
    async def _notify_subscribers(self, event: Event, status: str, today: date) -> None:
        """Отправляет уведомления подписчикам."""
        db = SessionLocal()
        
        try:
            watches = db.scalars(
                select(TelegramWatch).where(
                    TelegramWatch.phenomenon_id == event.phenomenon_id
                )
            ).all()
            
            if not watches:
                return
            
            message = format_event_message(event, status, today)
            
            for watch in watches:
                try:
                    await self.bot.send_message(
                        chat_id=watch.chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.error(f"Ошибка отправки в чат {watch.chat_id}: {e}")
                    
        except Exception as e:
            log.exception(f"Ошибка при отправке уведомлений: {e}")
        finally:
            db.close()
    
    async def _send_peak_reminder(self, event: Event, today: date, days_to_peak: int) -> None:
        """Отправляет напоминание о пике."""
        db = SessionLocal()
        
        try:
            watches = db.scalars(
                select(TelegramWatch).where(
                    TelegramWatch.phenomenon_id == event.phenomenon_id
                )
            ).all()
            
            if not watches:
                return
            
            ph = event.phenomenon
            pl = event.place
            emoji = get_kind_emoji(ph.kind)
            
            if days_to_peak == 1:
                message = f"""<b>{emoji} {escape_html(ph.name)} - НАПОМИНАНИЕ</b> 🔔

🔥 <b>ПИК ЯВЛЕНИЯ - ЗАВТРА!</b> 🔥

📍 <b>Где:</b> {escape_html(pl.name)}
📅 <b>Дата пика:</b> {event.peak_date.strftime('%d.%m.%Y')}

<i>Самое время планировать поездку!</i> 🚗

💡 <b>Совет:</b> Лучшее время для посещения - утренние часы, когда меньше людей и лучший свет для фото."""
            else:
                message = f"""<b>{emoji} {escape_html(ph.name)} - НАПОМИНАНИЕ</b> 🔔

🌿 <b>Пик явления через {days_to_peak} дня!</b> 🌿

📍 <b>Где:</b> {escape_html(pl.name)}
📅 <b>Дата пика:</b> {event.peak_date.strftime('%d.%m.%Y')}

<i>Не пропустите самое красивое время!</i> ✨"""
            
            for watch in watches:
                try:
                    await self.bot.send_message(
                        chat_id=watch.chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.error(f"Ошибка отправки напоминания в чат {watch.chat_id}: {e}")
                    
        except Exception as e:
            log.exception(f"Ошибка при отправке напоминания: {e}")
        finally:
            db.close()


# Инициализация бота
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
dp = Dispatcher()
notification_service = NotificationService(bot)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт главную клавиатуру."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои подписки"), KeyboardButton(text="🔍 Найти явление")],
            [KeyboardButton(text="📅 Что сегодня"), KeyboardButton(text="📆 Что на неделе")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )


# ==================== КОМАНДЫ БОТА ====================

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Приветствие."""
    text = """<b>🌸 ДОБРО ПОЖАЛОВАТЬ В ЦВЕТАШКИ КРЫМ!</b> 🌸

Я помогу вам <b>не пропустить</b> самые красивые сезонные явления Крыма.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Как пользоваться ботом:</b>

▪️ <b>/follow</b> <i>&lt;slug&gt;</i> — подписаться на явление
   <i>Пример: /follow lavanda-turgenevka</i>

▪️ <b>/unfollow</b> <i>&lt;slug&gt;</i> — отписаться от явления

▪️ <b>/mine</b> — показать все мои подписки

▪️ <b>/search</b> <i>&lt;текст&gt;</i> — найти явление по названию

▪️ <b>/today</b> — что происходит сегодня

▪️ <b>/week</b> — события на неделю

▪️ <b>/help</b> — эта справка

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🌟 Начните с /follow и выберите явление!</b>"""
    
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Справка."""
    text = """<b>❓ ПОМОЩЬ ПО КОМАНДАМ</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📋 Управление подписками:</b>

▪️ <b>/follow</b> <i>&lt;slug&gt;</i> — подписаться
▪️ <b>/unfollow</b> <i>&lt;slug&gt;</i> — отписаться
▪️ <b>/mine</b> — мои подписки

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔍 Поиск и информация:</b>

▪️ <b>/search</b> <i>&lt;текст&gt;</i> — найти явление
▪️ <b>/today</b> — что происходит сегодня
▪️ <b>/week</b> — события на неделю

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🌟 Популярные slug-и:</b>

🌺 <b>lavanda-turgenevka</b> — Лаванда в Тургеневке
🌸 <b>sakura-nikitsky</b> — Сакура в НБС
❤️ <b>maki-koktebel</b> — Маки в Коктебеле
💜 <b>glycine-alupka</b> — Глициния в Алупке
🌿 <b>piony-nbs</b> — Пионы в НБС
❄️ <b>podsnezhniki-laspi</b> — Подснежники в Ласпи
🌅 <b>zakat-fiorent</b> — Закаты на Фиоленте
🍒 <b>cherry-kerch</b> — Черешня в Керчи

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Вернуться к началу: /start</i>"""
    
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("follow"))
async def cmd_follow(message: Message, command: CommandObject) -> None:
    """Подписка на явление."""
    slug = command.args.strip() if command and command.args else None
    
    if not slug:
        text = """<b>🌸 Как подписаться:</b>

Используйте команду:
<b>/follow</b> <i>&lt;slug&gt;</i>

<i>Пример: /follow lavanda-turgenevka</i>

💡 Чтобы узнать slug явления, введите /search или /help"""
        
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

По запросу <code>{escape_html(slug)}</code> ничего не найдено.

<b>🔍 Возможно, вы искали:</b>
{similar_list}

💡 Используйте: /follow &lt;slug&gt;"""
            else:
                text = f"""<b>❌ Явление не найдено</b>

Slug <code>{escape_html(slug)}</code> не существует.

💡 Введите /help чтобы увидеть список популярных slug-ов"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        # Проверяем существующую подписку
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
        
        # Создаём подписку
        watch = TelegramWatch(
            chat_id=message.chat.id,
            phenomenon_id=phenomenon.id
        )
        db.add(watch)
        db.commit()
        
        # Получаем актуальное событие
        today = date.today()
        event = db.scalar(
            select(Event)
            .where(
                Event.phenomenon_id == phenomenon.id,
                Event.end_date >= today
            )
            .order_by(Event.start_date)
        )
        
        emoji = get_kind_emoji(phenomenon.kind)
        response = f"""<b>{emoji} УСПЕШНО ПОДПИСАНА! {emoji}</b>

Вы подписались на <b>{escape_html(phenomenon.name)}</b>

📌 <b>Slug:</b> <code>{phenomenon.slug}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        if event:
            status = marker_status(today, event.start_date, event.end_date)
            if status == "active":
                response += f"\n\n🔴 <b>Прямо сейчас</b> это явление <b>активно</b>! Не пропустите!"
            elif status == "soon":
                days = (event.start_date - today).days
                response += f"\n\n🟡 <b>Начинается через {days} дней</b> — скоро вы получите уведомление!"
            elif status == "future":
                response += f"\n\n⚪ <b>Запланировано</b> на {event.start_date.strftime('%d.%m.%Y')}"
            else:
                response += f"\n\n📅 Следите за обновлениями"
        else:
            response += f"\n\n📅 Уведомления придут, когда появятся новые даты"
        
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
    """Отписка от явления."""
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

Slug <code>{escape_html(slug)}</code> не существует.

💡 Проверьте правильность написания."""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        # Удаляем подписку
        result = db.execute(
            select(TelegramWatch).where(
                TelegramWatch.chat_id == message.chat.id,
                TelegramWatch.phenomenon_id == phenomenon.id
            )
        )
        watch = result.scalar_one_or_none()
        
        if not watch:
            text = f"""<b>❌ Вы не подписаны</b>

Вы не подписаны на явление <b>{escape_html(phenomenon.name)}</b>.

💡 Подписаться: /follow {slug}"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        db.delete(watch)
        db.commit()
        
        emoji = get_kind_emoji(phenomenon.kind)
        text = f"""<b>{emoji} ВЫ ОТПИСАЛИСЬ {emoji}</b>

Вы больше не будете получать уведомления о явлении <b>{escape_html(phenomenon.name)}</b>.

💡 Чтобы подписаться снова: /follow {slug}"""
        
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
    """Показывает подписки пользователя."""
    db = SessionLocal()
    today = date.today()
    
    try:
        watches = db.scalars(
            select(TelegramWatch)
            .where(TelegramWatch.chat_id == message.chat.id)
        ).all()
        
        if not watches:
            text = """<b>📭 У вас пока нет подписок</b>

Чтобы подписаться на явление, используйте команду:
<b>/follow</b> <i>&lt;slug&gt;</i>

<i>Пример: /follow lavanda-turgenevka</i>

💡 Список популярных явлений: /help"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        phenomenon_ids = [w.phenomenon_id for w in watches]
        phenomena = db.scalars(
            select(Phenomenon)
            .where(Phenomenon.id.in_(phenomenon_ids))
        ).all()
        
        # Сортируем по названию
        phenomena = sorted(phenomena, key=lambda x: x.name)
        
        response = "<b>📋 МОИ ПОДПИСКИ</b>\n\n"
        
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
            response += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
            response += f"   📌 <code>{ph.slug}</code>\n"
            
            if event:
                status = marker_status(today, event.start_date, event.end_date)
                if status == "active":
                    response += f"   🔴 <b>ИДЁТ СЕЙЧАС!</b>\n"
                elif status == "soon":
                    days = (event.start_date - today).days
                    response += f"   🟡 Начнётся <b>через {days} дней</b>\n"
                elif status == "future":
                    response += f"   ⚪ Начало: {event.start_date.strftime('%d.%m.%Y')}\n"
                else:
                    response += f"   ✅ Завершено: {event.end_date.strftime('%d.%m.%Y')}\n"
            else:
                response += f"   ⏳ Ожидание новых дат\n"
            
            response += f"   🔕 /unfollow {ph.slug}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        response += "<i>Чтобы отписаться: /unfollow &lt;slug&gt;</i>"
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        log.exception(f"Ошибка при получении подписок: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка</b>\n\nНе удалось загрузить ваши подписки.",
            parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


@dp.message(Command("today"))
async def cmd_today(message: Message) -> None:
    """Показывает события на сегодня."""
    db = SessionLocal()
    today = date.today()
    
    try:
        events = db.scalars(
            select(Event)
            .options(joinedload(Event.phenomenon), joinedload(Event.place))
            .where(
                Event.start_date <= today,
                Event.end_date >= today
            )
            .order_by(Event.phenomenon_id)
        ).unique().all()
        
        if not events:
            text = """<b>📅 Сегодня нет активных явлений</b>

Но вы можете посмотреть, что будет скоро: /week

💡 Вернуться к началу: /start"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        response = "<b>🔴 АКТИВНО СЕГОДНЯ 🔴</b>\n\n"
        
        for event in events:
            ph = event.phenomenon
            pl = event.place
            emoji = get_kind_emoji(ph.kind)
            
            response += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
            response += f"   📍 {escape_html(pl.name)}\n"
            response += f"   🎯 Пик: {event.peak_date.strftime('%d.%m.%Y')}\n"
            response += f"   🔗 /follow {ph.slug}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        response += "<i>Для справки: /help</i>"
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        log.exception(f"Ошибка в /today: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка</b>\n\nПопробуйте позже или введите /help",
            parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


@dp.message(Command("week"))
async def cmd_week(message: Message) -> None:
    """Показывает события на неделю."""
    db = SessionLocal()
    today = date.today()
    next_week = today + timedelta(days=7)
    
    try:
        events = db.scalars(
            select(Event)
            .options(joinedload(Event.phenomenon), joinedload(Event.place))
            .where(
                Event.start_date >= today,
                Event.start_date <= next_week
            )
            .order_by(Event.start_date)
        ).unique().all()
        
        if not events:
            text = """<b>📅 На следующей неделе нет запланированных явлений</b>

Попробуйте поискать: /search

💡 Вернуться к началу: /start"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        response = "<b>📆 СОБЫТИЯ НА НЕДЕЛЮ</b>\n\n"
        
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
            
            response += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
            response += f"   📍 {escape_html(pl.name)}\n"
            response += f"   📅 Начало: <b>{day_str}</b>\n"
            response += f"   🔗 /follow {ph.slug}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        response += "<i>Для справки: /help</i>"
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        log.exception(f"Ошибка в /week: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка</b>\n\nПопробуйте позже или введите /help",
            parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


@dp.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject) -> None:
    """Поиск явлений."""
    query = command.args.strip() if command and command.args else None
    
    if not query:
        text = """<b>🔍 Как искать:</b>

Введите: <b>/search</b> <i>&lt;текст&gt;</i>

<i>Пример: /search лаванда</i> или <i>/search маки</i>

💡 Вернуться к началу: /start"""
        
        await message.answer(text, parse_mode=ParseMode.HTML)
        return
    
    db = SessionLocal()
    
    try:
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

По запросу "<i>{escape_html(query)}</i>" ничего не найдено.

💡 Попробуйте другое ключевое слово или посмотрите /help

Вернуться к началу: /start"""
            
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        response = f"<b>🔍 РЕЗУЛЬТАТЫ ПОИСКА:</b> <i>{escape_html(query)}</i>\n\n"
        
        for ph in phenomena:
            emoji = get_kind_emoji(ph.kind)
            response += f"{emoji} <b>{escape_html(ph.name)}</b>\n"
            response += f"   📌 <code>{ph.slug}</code>\n"
            response += f"   📂 Тип: {ph.kind}\n"
            if ph.description:
                desc = escape_html(ph.description[:80])
                if len(ph.description) > 80:
                    desc += "..."
                response += f"   📝 {desc}\n"
            response += f"   🔗 /follow {ph.slug}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        response += "<i>Для справки: /help</i>"
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        log.exception(f"Ошибка в /search: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка</b>\n\nПопробуйте позже или введите /help",
            parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


@dp.message(Command("about"))
async def cmd_about(message: Message) -> None:
    """О боте."""
    text = """<b>ℹ️ О БОТЕ</b>

<b>🌸 Цветашки Крым</b> — ваш помощник в отслеживании сезонных явлений Крыма.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🌟 Возможности:</b>

▪️ Подписка на любимые явления
▪️ Автоматические уведомления о начале
▪️ Напоминания о пике сезона
▪️ Поиск по всем явлениям
▪️ Информация о датах и местах

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 Статистика:</b>
• Активных явлений: много
• Довольных подписчиков: вы

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📞 Контакты:</b>
• GitHub: @videmyy
• Email: videmyy@gmail.com

<i>Вернуться к началу: /start</i>"""
    
    await message.answer(text, parse_mode=ParseMode.HTML)


# ==================== КНОПКИ ====================

@dp.message(F.text == "📋 Мои подписки")
async def handle_my_subscriptions_button(message: Message) -> None:
    """Кнопка моих подписок."""
    await cmd_mine(message)


@dp.message(F.text == "🔍 Найти явление")
async def handle_search_button(message: Message) -> None:
    """Кнопка поиска."""
    await message.answer(
        "<b>🔍 Поиск явлений</b>\n\nВведите ключевое слово для поиска:\n<code>/search лаванда</code>\n\nИли посмотрите список в /help",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text == "📅 Что сегодня")
async def handle_today_button(message: Message) -> None:
    """Кнопка \"Что сегодня\"."""
    await cmd_today(message)


@dp.message(F.text == "📆 Что на неделе")
async def handle_week_button(message: Message) -> None:
    """Кнопка \"Что на неделе\"."""
    await cmd_week(message)


@dp.message(F.text == "❓ Помощь")
async def handle_help_button(message: Message) -> None:
    """Кнопка помощи."""
    await cmd_help(message)


@dp.message(F.text == "ℹ️ О боте")
async def handle_about_button(message: Message) -> None:
    """Кнопка \"О боте\"."""
    await cmd_about(message)


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def run_notification_worker():
    """Фоновый процесс для уведомлений."""
    log.info("Запуск сервиса уведомлений")
    
    while True:
        try:
            await asyncio.sleep(6 * 60 * 60)  # 6 часов
            await notification_service.check_and_notify()
            log.info("Цикл уведомлений выполнен")
        except Exception as e:
            log.exception(f"Ошибка в цикле уведомлений: {e}")
            await asyncio.sleep(60)


# ==================== ЗАПУСК ====================

async def main() -> None:
    """Главная функция запуска бота."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    
    if not token:
        log.error("TELEGRAM_BOT_TOKEN не задан в переменных окружения")
        log.error("Добавьте TELEGRAM_BOT_TOKEN=ваш_токен в файл .env")
        sys.exit(1)
    
    log.info("🚀 Запуск Telegram-бота Цветашки Крым")
    log.info(f"Бот @{(await bot.get_me()).username}")
    
    # Запускаем фоновую задачу
    asyncio.create_task(run_notification_worker())
    
    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())