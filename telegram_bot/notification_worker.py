"""Скрипт для ручного запуска проверки уведомлений."""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot
from telegram_bot.notifications import NotificationService


async def run_once():
    """Запускает одну проверку уведомлений."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN не задан")
        sys.exit(1)

    bot = Bot(token=token)
    service = NotificationService(bot)

    print("Запуск проверки уведомлений...")
    await service.check_and_notify()
    print("Проверка завершена")

    await bot.session.close()


def main():
    asyncio.run(run_once())


if __name__ == "__main__":
    main()