"""
Telegram-бот для подписок на сезонные явления с автоматическими уведомлениями.

Рефакторинг: логика разнесена по модулям:
- handlers.py  — команды и кнопки
- notifications.py — сервис уведомлений (статусы хранятся в БД)
- utils.py — форматирование, эмодзи, escape
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo

from telegram_bot.handlers import register_handlers
from telegram_bot.notifications import NotificationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("tsvetashki.tg")

# Инициализация бота
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
dp = Dispatcher()
notification_service = NotificationService(bot)

# Регистрация хендлеров
register_handlers(dp)


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def run_notification_worker():
    """Фоновый процесс для уведомлений."""
    log.info("Запуск сервиса уведомлений")

    # Выполняем проверку сразу при запуске бота
    try:
        await notification_service.check_and_notify()
        log.info("Первоначальный цикл уведомлений выполнен")
    except Exception as e:
        log.exception(f"Ошибка в первоначальном цикле уведомлений: {e}")

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

    # Устанавливаем кнопку меню для Mini App
    try:
        website_url = os.getenv("WEBSITE_URL", "https://tsvetashki-krym.ru").rstrip("/")
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🗺️ Карта",
                web_app=WebAppInfo(url=f"{website_url}/map?tg=1")
            )
        )
        log.info("Кнопка меню для Mini App успешно установлена")
    except Exception as e:
        log.exception(f"Не удалось установить кнопку меню Mini App: {e}")

    # Запускаем фоновую задачу
    asyncio.create_task(run_notification_worker())

    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())