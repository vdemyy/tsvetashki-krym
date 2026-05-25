# Простое логирование для безопасности

import logging
from datetime import datetime
from pathlib import Path

# Создаем папку для логов
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настраиваем логгер
logger = logging.getLogger("security")
logger.setLevel(logging.INFO)

# Файл для логов
log_file = logs_dir / "security.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


def log_login_attempt(ip: str, success: bool, username: str = "admin"):
    """Логирует попытку входа"""
    if success:
        logger.info(f"Успешный вход | IP: {ip} | Пользователь: {username}")
    else:
        logger.warning(f"Неудачная попытка входа | IP: {ip} | Пользователь: {username}")


def log_admin_action(ip: str, action: str, details: str = ""):
    """Логирует действия в админке"""
    logger.info(f"Действие админа | IP: {ip} | Действие: {action} | Детали: {details}")


def log_suspicious_activity(ip: str, reason: str):
    """Логирует подозрительную активность"""
    logger.warning(f"Подозрительная активность | IP: {ip} | Причина: {reason}")


def log_rate_limit(ip: str, endpoint: str):
    """Логирует превышение лимита запросов"""
    logger.warning(f"Rate limit превышен | IP: {ip} | Endpoint: {endpoint}")
