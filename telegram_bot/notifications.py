"""Сервис уведомлений для Telegram-бота с хранением статусов в БД."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from aiogram import Bot
from aiogram.enums import ParseMode
from sqlalchemy import select, or_, and_, Column, Integer, String, DateTime
from sqlalchemy.orm import Session, joinedload

from database import SessionLocal, Base
from models import Event, Phenomenon, TelegramWatch
from services.forecast import marker_status
from telegram_bot.utils import format_event_message, get_kind_emoji, escape_html

log = logging.getLogger("tsvetashki.notifications")


class NotificationLog(Base):
    """Лог последних отправленных статусов — чтобы не дублировать уведомления при перезапуске."""

    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    last_status = Column(String(32), nullable=False)
    updated_at = Column(DateTime, nullable=False)


class NotificationService:
    """Сервис для проверки и отправки уведомлений."""

    def __init__(self, bot: Bot):
        self.bot = bot

    def _get_last_status(self, db: Session, event_id: int) -> str | None:
        row = db.scalars(
            select(NotificationLog).where(NotificationLog.event_id == event_id)
        ).first()
        return row.last_status if row else None

    def _save_status(self, db: Session, event_id: int, status: str) -> None:
        from datetime import datetime, timezone

        row = db.scalars(
            select(NotificationLog).where(NotificationLog.event_id == event_id)
        ).first()
        if row:
            row.last_status = status
            row.updated_at = datetime.now(timezone.utc)
        else:
            db.add(NotificationLog(
                event_id=event_id,
                last_status=status,
                updated_at=datetime.now(timezone.utc),
            ))

    async def check_and_notify(self) -> None:
        """Проверяет события и отправляет уведомления."""
        db = SessionLocal()
        today = date.today()

        try:
            # Ensure table exists
            NotificationLog.__table__.create(bind=db.get_bind(), checkfirst=True)

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
                old_status = self._get_last_status(db, event.id)

                if old_status != new_status:
                    self._save_status(db, event.id, new_status)
                    db.commit()
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

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"ph_view:{event.phenomenon_id}:mine"),
                    InlineKeyboardButton(text="🔕 Отписаться", callback_data=f"ph_unsub:{event.phenomenon_id}:mine")
                ]
            ])

            message = format_event_message(event, status, today)

            for watch in watches:
                try:
                    await self.bot.send_message(
                        chat_id=watch.chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
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

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"ph_view:{event.phenomenon_id}:mine"),
                    InlineKeyboardButton(text="🔕 Отписаться", callback_data=f"ph_unsub:{event.phenomenon_id}:mine")
                ]
            ])

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
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.error(f"Ошибка отправки напоминания в чат {watch.chat_id}: {e}")

        except Exception as e:
            log.exception(f"Ошибка при отправке напоминания: {e}")
        finally:
            db.close()
