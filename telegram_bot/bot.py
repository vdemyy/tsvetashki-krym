"""
Telegram-бот для подписок на сезонные явления с автоматическими уведомлениями.

Функции:
- Подписка/отписка на явления
- Ежедневная проверка изменения статусов событий
- Красивые форматированные сообщения с эмодзи и кнопками
- Умные уведомления: начало, пик, конец, напоминания
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Set, Tuple

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
from services.icon_map import lucide_icon_for_phenomenon

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

# Статус-тексты на русском
STATUS_TEXT = {
    "active": "🔴 ИДЁТ ПРЯМО СЕЙЧАС",
    "soon": "🟡 НАЧИНАЕТСЯ СКОРО",
    "future": "⚪ ЗАПЛАНИРОВАНО",
    "ended": "✅ ЗАВЕРШЕНО"
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
    """Форматирует дату с относительным указанием (сегодня, завтра и т.д.)."""
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


def format_event_message(
    event: Event,
    status: str,
    today: date,
    include_buttons: bool = True
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Форматирует сообщение о событии с красивым оформлением."""
    
    ph = event.phenomenon
    pl = event.place
    
    emoji = get_kind_emoji(ph.kind)
    status_emoji_full = STATUS_EMOJI.get(status, "📌")
    status_text_full = STATUS_TEXT.get(status, status.upper())
    
    # Индикатор интенсивности (звёздочки)
    intensity_stars = "⭐" * event.intensity + "☆" * (5 - event.intensity)
    
    # Относительные даты
    start_relative = format_date_relative(event.start_date, today)
    peak_relative = format_date_relative(event.peak_date, today)
    end_relative = format_date_relative(event.end_date, today)
    
    message = f"""\
{emoji} *{ph.name}* {status_emoji_full}

📍 *Место:* {pl.name}
🗺 *Регион:* {pl.region or "Крым"}{f" · {pl.subregion}" if pl.subregion else ""}

📅 *Даты:*
• Начало: `{event.start_date.strftime('%d.%m.%Y')}` ({start_relative})
• Пик: `{event.peak_date.strftime('%d.%m.%Y')}` ({peak_relative})
• Конец: `{event.end_date.strftime('%d.%m.%Y')}` ({end_relative})

💪 *Интенсивность:* {intensity_stars} ({event.intensity}/5)

{status_text_full}
"""

    if ph.description:
        message += f"\n📝 *Описание:* {ph.description[:200]}{'...' if len(ph.description) > 200 else ''}"
    
    if ph.typical_season:
        message += f"\n📆 *Типичный сезон:* {ph.typical_season}"
    
    # Кнопки
    buttons = InlineKeyboardBuilder()
    
    if include_buttons:
        # Кнопка "Подробнее на сайте"
        website_url = ph.website_url or ""
        if website_url and website_url.startswith("/"):
            base_url = os.getenv("BASE_URL", "https://tsvetashki.ru")
            website_url = f"{base_url}{website_url}"
        
        if website_url:
            buttons.button(text="🔗 Подробнее", url=website_url)
        
        # Кнопка "Отписаться"
        buttons.button(
            text="🔕 Отписаться",
            callback_data=f"unsubscribe_{ph.id}"
        )
        
        buttons.adjust(1)
        return message, buttons.as_markup()
    
    return message, None


class NotificationService:
    """Сервис для проверки и отправки уведомлений."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self._last_check_status: Dict[int, str] = {}  # event_id -> last_status
    
    async def check_and_notify(self) -> None:
        """Проверяет все события и отправляет уведомления при смене статуса."""
        db = SessionLocal()
        today = date.today()
        
        try:
            # Получаем все активные события (текущие и будущие на 30 дней)
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
            
            changes = []
            
            for event in events:
                new_status = marker_status(today, event.start_date, event.end_date)
                old_status = self._last_check_status.get(event.id)
                
                # Если статус изменился или это первая проверка
                if old_status != new_status:
                    changes.append(EventStatusChange(
                        event_id=event.id,
                        phenomenon_name=event.phenomenon.name,
                        phenomenon_slug=event.phenomenon.slug,
                        place_name=event.place.name,
                        region=event.place.region or "Крым",
                        old_status=old_status or "unknown",
                        new_status=new_status,
                        start_date=event.start_date,
                        peak_date=event.peak_date,
                        end_date=event.end_date,
                        intensity=event.intensity,
                        days_until=(event.start_date - today).days if new_status == "soon" else None
                    ))
                    
                    # Обновляем сохранённый статус
                    self._last_check_status[event.id] = new_status
                    
                    # Также отправляем напоминания за 3 дня до пика
                    days_to_peak = (event.peak_date - today).days
                    if 1 <= days_to_peak <= 3 and new_status != "ended":
                        await self._send_peak_reminder(event, today, days_to_peak)
            
            # Отправляем уведомления о смене статуса
            for change in changes:
                await self._notify_subscribers(change)
                
        except Exception as e:
            log.exception(f"Ошибка при проверке уведомлений: {e}")
        finally:
            db.close()
    
    async def _notify_subscribers(self, change: EventStatusChange) -> None:
        """Отправляет уведомления подписчикам об изменении статуса."""
        db = SessionLocal()
        
        try:
            # Получаем всех подписчиков на это явление
            # Сначала получаем phenomenon_id по event_id
            event = db.get(Event, change.event_id)
            if not event:
                return
            
            watches = db.scalars(
                select(TelegramWatch).where(
                    TelegramWatch.phenomenon_id == event.phenomenon_id
                )
            ).all()
            
            if not watches:
                return
            
            message, keyboard = format_event_message(event, change.new_status, date.today())
            
            # Отправляем каждому подписчику
            for watch in watches:
                try:
                    await self.bot.send_message(
                        chat_id=watch.chat_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )
                    log.info(f"Уведомление отправлено в чат {watch.chat_id} о событии {change.event_id}")
                    # Небольшая задержка, чтобы не флудить
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.error(f"Не удалось отправить сообщение в чат {watch.chat_id}: {e}")
                    
        except Exception as e:
            log.exception(f"Ошибка при отправке уведомлений: {e}")
        finally:
            db.close()
    
    async def _send_peak_reminder(self, event: Event, today: date, days_to_peak: int) -> None:
        """Отправляет напоминание о приближающемся пике."""
        db = SessionLocal()
        
        try:
            watches = db.scalars(
                select(TelegramWatch).where(TelegramWatch.phenomenon_id == event.phenomenon_id)
            ).all()
            
            if not watches:
                return
            
            ph = event.phenomenon
            pl = event.place
            
            emoji = get_kind_emoji(ph.kind)
            
            if days_to_peak == 1:
                message = f"""\
{emoji} *{ph.name}* — НАПОМИНАНИЕ 🌟

🔥 *Пик явления — ЗАВТРА!* 🔥

📍 *Где:* {pl.name}
📅 *Дата пика:* {event.peak_date.strftime('%d.%m.%Y')}

Самое время планировать поездку! 🚗

💡 *Совет:* Лучшее время для посещения — утренние часы, когда меньше людей и лучший свет для фото.
"""
            else:
                message = f"""\
{emoji} *{ph.name}* — НАПОМИНАНИЕ 📅

🌿 *Пик явления через {days_to_peak} дня!* 🌿

📍 *Где:* {pl.name}
📅 *Дата пика:* {event.peak_date.strftime('%d.%m.%Y')}

Не пропустите самое красивое время! ✨
"""
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔗 Подробнее",
                        url=ph.website_url or f"https://tsvetashki.ru/p/{ph.slug}"
                    )],
                    [InlineKeyboardButton(
                        text="🗺 Показать на карте",
                        callback_data=f"show_map_{event.place_id}"
                    )]
                ]
            )
            
            for watch in watches:
                try:
                    await self.bot.send_message(
                        chat_id=watch.chat_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.error(f"Не удалось отправить напоминание в чат {watch.chat_id}: {e}")
                    
        except Exception as e:
            log.exception(f"Ошибка при отправке напоминания о пике: {e}")
        finally:
            db.close()


# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
dp = Dispatcher()
notification_service = NotificationService(bot)


# --- Вспомогательные функции ---

async def get_user_subscriptions(chat_id: int) -> List[Tuple[Phenomenon, Event]]:
    """Возвращает список подписок пользователя с актуальными событиями."""
    db = SessionLocal()
    today = date.today()
    
    try:
        # Получаем подписки пользователя
        watches = db.scalars(
            select(TelegramWatch)
            .where(TelegramWatch.chat_id == chat_id)
        ).all()
        
        if not watches:
            return []
        
        phenomenon_ids = [w.phenomenon_id for w in watches]
        
        # Получаем актуальные события для этих явлений
        events = db.scalars(
            select(Event)
            .options(joinedload(Event.phenomenon), joinedload(Event.place))
            .where(
                Event.phenomenon_id.in_(phenomenon_ids),
                Event.end_date >= today - timedelta(days=30)  # Показываем завершённые за последний месяц
            )
            .order_by(Event.start_date)
        ).unique().all()
        
        return [(e.phenomenon, e) for e in events]
    finally:
        db.close()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт главную клавиатуру бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои подписки")],
            [KeyboardButton(text="🔍 Найти явление"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )


# --- Обработчики команд ---

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    welcome_text = """\
🌺 *Добро пожаловать в Цветашки Крым!* 🌺

Я помогу вам не пропустить самые красивые сезонные явления Крыма:
• Цветение лаванды, сакуры, маков 🌸
• Удивительные закаты и рассветы 🌅
• Сбор урожая черешни, винограда 🍇
• Встречи с дельфинами 🐬
• И многое другое...

*Как пользоваться ботом:*

📌 `/follow <slug>` — подписаться на явление
   Пример: `/follow lavanda-turgenevka`

🔕 `/unfollow <slug>` — отписаться от явления

📋 `/mine` — показать все мои подписки

🔍 `/search <текст>` — найти явление по названию

📊 `/today` — что происходит сегодня

📅 `/week` — события на неделю

❓ `/help` — эта справка

*Активные подписки:* вы будете получать уведомления:
• Когда явление вот-вот начнётся
• Когда наступит пик
• Когда явление завершится
• Напоминания за 3 дня до пика

Начните с `/follow` и выберите явление! ✨
"""
    
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help."""
    help_text = """\
❓ *Помощь по командам*

*Управление подписками:*
/follow `<slug>` — подписаться
/unfollow `<slug>` — отписаться
/mine — мои подписки

*Поиск и информация:*
/search `<текст>` — найти явление
/today — что происходит сегодня
/week — события на неделю

*Популярные slug-и:*
• `lavanda-turgenevka` — Лаванда в Тургеневке
• `sakura-nikitsky` — Сакура в НБС
• `maki-koktebel` — Маки в Коктебеле
• `glycine-alupka` — Глициния в Алупке
• `piony-nbs` — Пионы в НБС
• `podsnezhniki-laspi` — Подснежники в Ласпи
• `zakat-fiorent` — Закаты на Фиоленте
• `cherry-kerch` — Черешня в Керчи
• `delfiny-sudak` — Дельфины в Судаке

Больше явлений можно найти на сайте: https://tsvetashki.ru

*Вопросы или предложения?*
Напишите нам: @tsvetashki_support

*Вернуться к началу:* /start
"""
    
    await message.answer(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("follow"))
async def cmd_follow(message: Message, command: CommandObject) -> None:
    """Обработчик команды /follow."""
    slug = command.args.strip() if command and command.args else None
    
    if not slug:
        await message.answer(
            "🌸 *Как подписаться:*\n\n"
            "Используйте команду: `/follow <slug>`\n\n"
            "Например: `/follow lavanda-turgenevka`\n\n"
            "Чтобы узнать slug явления, введите `/search` или посмотрите `/help`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    db = SessionLocal()
    try:
        # Ищем явление по slug
        phenomenon = db.scalars(
            select(Phenomenon).where(Phenomenon.slug == slug)
        ).first()
        
        if not phenomenon:
            # Поиск похожих
            similar = db.scalars(
                select(Phenomenon)
                .where(Phenomenon.name.ilike(f"%{slug}%"))
                .limit(5)
            ).all()
            
            if similar:
                similar_list = "\n".join([f"• `{ph.slug}` — {ph.name}" for ph in similar])
                await message.answer(
                    f"❌ *Явление не найдено*\n\n"
                    f"По вашему запросу `{slug}` ничего не найдено.\n\n"
                    f"*Возможно, вы искали:*\n{similar_list}\n\n"
                    f"Используйте один из этих slug-ов в команде `/follow`",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await message.answer(
                    f"❌ *Явление не найдено*\n\n"
                    f"Slug `{slug}` не существует.\n\n"
                    f"Введите `/help` чтобы увидеть список популярных slug-ов",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Проверяем, не подписан ли уже
        existing = db.scalar(
            select(TelegramWatch).where(
                TelegramWatch.chat_id == message.chat.id,
                TelegramWatch.phenomenon_id == phenomenon.id
            )
        )
        
        if existing:
            emoji = get_kind_emoji(phenomenon.kind)
            await message.answer(
                f"{emoji} *Вы уже подписаны*\n\n"
                f"Вы уже получаете уведомления о явлении *{phenomenon.name}*.\n\n"
                f"Чтобы отписаться, используйте `/unfollow {phenomenon.slug}`",
                parse_mode=ParseMode.MARKDOWN
            )
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
        response = f"""\
{emoji} *УСПЕШНО ПОДПИСАНА!* {emoji}

Вы подписались на *{phenomenon.name}*

📌 *Slug:* `{phenomenon.slug}`

"""
        
        if event:
            status = marker_status(today, event.start_date, event.end_date)
            if status == "active":
                response += f"🔴 *Прямо сейчас* это явление *активно*! Не пропустите!"
            elif status == "soon":
                days = (event.start_date - today).days
                response += f"🟡 *Начинается через {days} дней* — скоро вы получите уведомление!"
            elif status == "future":
                response += f"⚪ *Запланировано* на {event.start_date.strftime('%d.%m.%Y')}"
            else:
                response += f"📅 Следите за обновлениями"
        else:
            response += f"📅 Уведомления придут, когда появятся новые даты события"
        
        response += f"\n\nУправлять подписками: `/mine`"
        
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        log.info(f"Пользователь {message.chat.id} подписался на {phenomenon.slug}")
        
    except Exception as e:
        log.exception(f"Ошибка при подписке: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Не удалось оформить подписку. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )
        db.rollback()
    finally:
        db.close()


@dp.message(Command("unfollow"))
async def cmd_unfollow(message: Message, command: CommandObject) -> None:
    """Обработчик команды /unfollow."""
    slug = command.args.strip() if command and command.args else None
    
    if not slug:
        await message.answer(
            "🔕 *Как отписаться:*\n\n"
            "Используйте команду: `/unfollow <slug>`\n\n"
            "Например: `/unfollow lavanda-turgenevka`\n\n"
            "Чтобы увидеть ваши подписки, введите `/mine`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    db = SessionLocal()
    try:
        phenomenon = db.scalars(
            select(Phenomenon).where(Phenomenon.slug == slug)
        ).first()
        
        if not phenomenon:
            await message.answer(
                f"❌ *Явление не найдено*\n\n"
                f"Slug `{slug}` не существует.\n\n"
                f"Проверьте правильность написания.",
                parse_mode=ParseMode.MARKDOWN
            )
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
            await message.answer(
                f"❌ *Вы не подписаны*\n\n"
                f"Вы не подписаны на явление *{phenomenon.name}*.\n\n"
                f"Подписаться: `/follow {slug}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        db.delete(watch)
        db.commit()
        
        emoji = get_kind_emoji(phenomenon.kind)
        await message.answer(
            f"{emoji} *Вы отписались* {emoji}\n\n"
            f"Вы больше не будете получать уведомления о явлении *{phenomenon.name}*.\n\n"
            f"Чтобы подписаться снова: `/follow {slug}`",
            parse_mode=ParseMode.MARKDOWN
        )
        log.info(f"Пользователь {message.chat.id} отписался от {phenomenon.slug}")
        
    except Exception as e:
        log.exception(f"Ошибка при отписке: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Не удалось отписаться. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )
        db.rollback()
    finally:
        db.close()


@dp.message(Command("mine"))
async def cmd_mine(message: Message) -> None:
    """Обработчик команды /mine — показывает подписки пользователя."""
    db = SessionLocal()
    today = date.today()
    
    try:
        watches = db.scalars(
            select(TelegramWatch)
            .where(TelegramWatch.chat_id == message.chat.id)
        ).all()
        
        if not watches:
            await message.answer(
                "📭 *У вас пока нет подписок*\n\n"
                "Чтобы подписаться на явление, используйте команду:\n"
                "`/follow <slug>`\n\n"
                "Например: `/follow lavanda-turgenevka`\n\n"
                "Список популярных явлений: `/help`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard()
            )
            return
        
        # Получаем явления с актуальными событиями
        phenomenon_ids = [w.phenomenon_id for w in watches]
        phenomena = db.scalars(
            select(Phenomenon)
            .where(Phenomenon.id.in_(phenomenon_ids))
        ).all()
        
        # Получаем события для каждого явления
        subscriptions_info = []
        for ph in phenomena:
            event = db.scalar(
                select(Event)
                .where(
                    Event.phenomenon_id == ph.id,
                    Event.end_date >= today - timedelta(days=30)
                )
                .order_by(Event.start_date)
            )
            
            status = None
            if event:
                status = marker_status(today, event.start_date, event.end_date)
            
            subscriptions_info.append((ph, event, status))
        
        # Сортируем: активные → скоро → будущие → завершённые
        def sort_key(item):
            status = item[2]
            if status == "active":
                return 0
            elif status == "soon":
                return 1
            elif status == "future":
                return 2
            else:
                return 3
        
        subscriptions_info.sort(key=sort_key)
        
        # Формируем красивое сообщение
        message_text = "📋 *Мои подписки*\n\n"
        
        status_icons = {
            "active": "🔴",
            "soon": "🟡",
            "future": "⚪",
            "ended": "✅"
        }
        
        for ph, event, status in subscriptions_info:
            emoji = get_kind_emoji(ph.kind)
            status_icon = status_icons.get(status, "📌")
            
            message_text += f"{emoji} *{ph.name}*\n"
            message_text += f"   📌 Slug: `{ph.slug}`\n"
            
            if event:
                if status == "active":
                    message_text += f"   {status_icon} *ИДЁТ СЕЙЧАС!*\n"
                elif status == "soon":
                    days = (event.start_date - today).days
                    message_text += f"   {status_icon} Начнётся *через {days} дней*\n"
                elif status == "future":
                    message_text += f"   {status_icon} Начало: {event.start_date.strftime('%d.%m.%Y')}\n"
                else:
                    message_text += f"   {status_icon} Завершено: {event.end_date.strftime('%d.%m.%Y')}\n"
            else:
                message_text += f"   ⏳ Ожидание новых дат\n"
            
            message_text += f"   🔕 `/unfollow {ph.slug}`\n\n"
        
        message_text += "---\n"
        message_text += "Чтобы отписаться, используйте `/unfollow <slug>`"
        
        await message.answer(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        log.exception(f"Ошибка при получении подписок: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Не удалось загрузить ваши подписки.",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        db.close()


@dp.message(Command("today"))
async def cmd_today(message: Message) -> None:
    """Показывает события, которые происходят сегодня."""
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
            await message.answer(
                "📅 *Сегодня нет активных явлений*\n\n"
                "Но вы можете посмотреть, что будет скоро: `/week`\n\n"
                "Или вернуться к началу: `/start`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        response = "🔴 *АКТИВНО СЕГОДНЯ* 🔴\n\n"
        
        for event in events:
            ph = event.phenomenon
            pl = event.place
            emoji = get_kind_emoji(ph.kind)
            
            response += f"{emoji} *{ph.name}*\n"
            response += f"   📍 {pl.name}\n"
            response += f"   🎯 Пик: {event.peak_date.strftime('%d.%m.%Y')}\n"
            response += f"   🔗 `/follow {ph.slug}`\n\n"
        
        response += "\n---\nДля справки: `/help`"
        
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        log.exception(f"Ошибка в /today: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Попробуйте позже или введите `/help`",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        db.close()


@dp.message(Command("week"))
async def cmd_week(message: Message) -> None:
    """Показывает события на ближайшую неделю."""
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
            await message.answer(
                "📅 *На следующей неделе нет запланированных явлений*\n\n"
                "Попробуйте поискать: `/search`\n\n"
                "Или вернуться к началу: `/start`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        response = "📅 *СОБЫТИЯ НА НЕДЕЛЮ* 📅\n\n"
        
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
            
            response += f"{emoji} *{ph.name}*\n"
            response += f"   📍 {pl.name}\n"
            response += f"   📅 Начало: {day_str}\n"
            response += f"   🔗 `/follow {ph.slug}`\n\n"
        
        response += "\n---\nДля справки: `/help`"
        
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        log.exception(f"Ошибка в /week: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Попробуйте позже или введите `/help`",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        db.close()


@dp.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject) -> None:
    """Поиск явлений по названию."""
    query = command.args.strip() if command and command.args else None
    
    if not query:
        await message.answer(
            "🔍 *Как искать:*\n\n"
            "Введите: `/search <текст>`\n\n"
            "Например: `/search лаванда` или `/search маки`\n\n"
            "Или вернуться к началу: `/start`",
            parse_mode=ParseMode.MARKDOWN
        )
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
            await message.answer(
                f"❌ *Ничего не найдено*\n\n"
                f"По запросу `{query}` ничего не найдено.\n\n"
                f"Попробуйте другое ключевое слово или посмотрите `/help`\n\n"
                f"Вернуться к началу: `/start`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        response = f"🔍 *Результаты поиска:* `{query}`\n\n"
        
        for ph in phenomena:
            emoji = get_kind_emoji(ph.kind)
            response += f"{emoji} *{ph.name}*\n"
            response += f"   📌 Slug: `{ph.slug}`\n"
            response += f"   📂 Тип: {ph.kind}\n"
            if ph.description:
                desc = ph.description[:80] + "..." if len(ph.description) > 80 else ph.description
                response += f"   📝 {desc}\n"
            response += f"   🔗 `/follow {ph.slug}`\n\n"
        
        response += "---\nДля справки: `/help`"
        
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        log.exception(f"Ошибка в /search: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n\n"
            "Попробуйте позже или введите `/help`",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        db.close()


# --- Обработчики кнопок и текстовых сообщений ---

@dp.callback_query(lambda c: c.data.startswith("unsubscribe_"))
async def process_unsubscribe_callback(callback: CallbackQuery) -> None:
    """Обработчик нажатия кнопки "Отписаться"."""
    phenomenon_id = int(callback.data.split("_")[1])
    
    db = SessionLocal()
    try:
        phenomenon = db.get(Phenomenon, phenomenon_id)
        
        if not phenomenon:
            await callback.answer("Явление не найдено", show_alert=True)
            return
        
        # Удаляем подписку
        result = db.execute(
            select(TelegramWatch).where(
                TelegramWatch.chat_id == callback.message.chat.id,
                TelegramWatch.phenomenon_id == phenomenon_id
            )
        )
        watch = result.scalar_one_or_none()
        
        if watch:
            db.delete(watch)
            db.commit()
            emoji = get_kind_emoji(phenomenon.kind)
            await callback.message.edit_text(
                f"{emoji} *Вы отписались* {emoji}\n\n"
                f"Вы больше не будете получать уведомления о явлении *{phenomenon.name}*.\n\n"
                f"Чтобы подписаться снова: `/follow {phenomenon.slug}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await callback.answer("Вы отписались от уведомлений")
        else:
            await callback.answer("Вы не были подписаны", show_alert=True)
            
    except Exception as e:
        log.exception(f"Ошибка при отписке по callback: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
        db.rollback()
    finally:
        db.close()


@dp.callback_query(lambda c: c.data.startswith("show_map_"))
async def process_map_callback(callback: CallbackQuery) -> None:
    """Обработчик кнопки "Показать на карте"."""
    place_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    try:
        place = db.get(Place, place_id)
        
        if place:
            # Создаём ссылку на карту
            maps_url = f"https://www.openstreetmap.org/?mlat={place.latitude}&mlon={place.longitude}#map=15/{place.latitude}/{place.longitude}"
            
            await callback.message.answer(
                f"📍 *{place.name}*\n\n"
                f"🗺 [Открыть на карте]({maps_url})\n"
                f"📌 Координаты: {place.latitude}, {place.longitude}",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            await callback.answer()
        else:
            await callback.answer("Место не найдено", show_alert=True)
            
    finally:
        db.close()


@dp.message(F.text == "📋 Мои подписки")
async def handle_my_subscriptions_button(message: Message) -> None:
    """Обработчик кнопки моих подписок."""
    await cmd_mine(message)


@dp.message(F.text == "🔍 Найти явление")
async def handle_search_button(message: Message) -> None:
    """Обработчик кнопки поиска."""
    await message.answer(
        "🔍 *Поиск явлений*\n\n"
        "Введите ключевое слово для поиска:\n"
        "`/search лаванда`\n\n"
        "Или посмотрите список в `/help`",
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message(F.text == "❓ Помощь")
async def handle_help_button(message: Message) -> None:
    """Обработчик кнопки помощи."""
    await cmd_help(message)


# --- Фоновая задача для рассылок ---

async def run_notification_worker():
    """Фоновый процесс для периодической проверки и отправки уведомлений."""
    log.info("Запуск сервиса уведомлений")
    
    while True:
        try:
            # Проверяем каждые 6 часов
            await asyncio.sleep(6 * 60 * 60)
            await notification_service.check_and_notify()
            log.info("Цикл уведомлений выполнен")
        except Exception as e:
            log.exception(f"Ошибка в цикле уведомлений: {e}")
            await asyncio.sleep(60)  # При ошибке ждём минуту и пробуем снова


async def main() -> None:
    """Главная функция запуска бота."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    
    if not token:
        log.error("TELEGRAM_BOT_TOKEN не задан в переменных окружения")
        log.error("Добавьте TELEGRAM_BOT_TOKEN=ваш_токен в файл .env")
        sys.exit(1)
    
    log.info("🚀 Запуск Telegram-бота Цветашки Крым")
    log.info(f"Бот @{(await bot.get_me()).username}")
    
    # Запускаем фоновую задачу для уведомлений
    asyncio.create_task(run_notification_worker())
    
    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())