# Защита от OWASP Top-10 уязвимостей
# Простые функции для студенческого проекта

import re
import html
from typing import Any


# ============================================
# A01:2021 – Broken Access Control
# ============================================

def check_user_permission(session: dict, required_role: str = "admin") -> bool:
    """
    Проверяет права доступа пользователя
    
    Args:
        session: Сессия пользователя
        required_role: Требуемая роль
    
    Returns:
        True если есть доступ
    """
    # Проверяем что пользователь авторизован
    if not session.get("admin"):
        return False
    
    # В будущем можно добавить проверку ролей
    # if session.get("role") != required_role:
    #     return False
    
    return True


# ============================================
# A02:2021 – Cryptographic Failures
# ============================================

def hash_password(password: str) -> str:
    """
    Хеширует пароль (простая версия для примера)
    В реальном проекте используйте bcrypt или argon2
    
    Args:
        password: Пароль
    
    Returns:
        Хешированный пароль
    """
    import hashlib
    
    # Добавляем соль для безопасности
    salt = "tsvetashki_salt_2024"
    
    # Хешируем с солью
    password_with_salt = password + salt
    hashed = hashlib.sha256(password_with_salt.encode()).hexdigest()
    
    return hashed


def check_password(password: str, hashed: str) -> bool:
    """
    Проверяет пароль
    
    Args:
        password: Введенный пароль
        hashed: Хешированный пароль из БД
    
    Returns:
        True если пароль верный
    """
    return hash_password(password) == hashed


# ============================================
# A03:2021 – Injection (SQL, NoSQL, OS)
# ============================================

def sanitize_sql_input(value: str) -> str:
    """
    Очищает ввод от SQL injection
    Примечание: SQLAlchemy уже защищает, это дополнительная проверка
    
    Args:
        value: Входное значение
    
    Returns:
        Очищенное значение
    """
    if not value:
        return ""
    
    # Удаляем опасные SQL команды
    dangerous_patterns = [
        r"(\bDROP\b|\bDELETE\b|\bUPDATE\b|\bINSERT\b)",
        r"(\bUNION\b|\bSELECT\b|\bEXEC\b|\bEXECUTE\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bAND\b\s+\d+\s*=\s*\d+)",
    ]
    
    for pattern in dangerous_patterns:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)
    
    return value.strip()


def sanitize_command_input(value: str) -> str:
    """
    Очищает ввод от OS command injection
    
    Args:
        value: Входное значение
    
    Returns:
        Очищенное значение
    """
    if not value:
        return ""
    
    # Удаляем опасные символы для команд
    dangerous_chars = [";", "|", "&", "$", "`", "\n", "\r", "$(", "&&", "||"]
    
    for char in dangerous_chars:
        value = value.replace(char, "")
    
    return value.strip()


# ============================================
# A04:2021 – Insecure Design
# ============================================

def validate_business_logic(data: dict) -> tuple[bool, str]:
    """
    Проверяет бизнес-логику (например, даты событий)
    
    Args:
        data: Данные для проверки
    
    Returns:
        (is_valid, error_message)
    """
    from datetime import date
    
    # Проверяем что start_date <= peak_date <= end_date
    if "start_date" in data and "peak_date" in data and "end_date" in data:
        start = data["start_date"]
        peak = data["peak_date"]
        end = data["end_date"]
        
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(peak, str):
            peak = date.fromisoformat(peak)
        if isinstance(end, str):
            end = date.fromisoformat(end)
        
        if not (start <= peak <= end):
            return False, "Даты должны быть в порядке: начало <= пик <= конец"
    
    # Проверяем интенсивность (1-5)
    if "intensity" in data:
        intensity = data["intensity"]
        if not (1 <= intensity <= 5):
            return False, "Интенсивность должна быть от 1 до 5"
    
    return True, ""


# ============================================
# A05:2021 – Security Misconfiguration
# ============================================

def check_secure_config() -> list[str]:
    """
    Проверяет безопасность конфигурации
    
    Returns:
        Список предупреждений
    """
    import os
    warnings = []
    
    # Проверяем SESSION_SECRET
    secret = os.getenv("SESSION_SECRET", "")
    if secret == "change-me-in-production" or len(secret) < 32:
        warnings.append("SESSION_SECRET слишком простой или короткий")
    
    # Проверяем ADMIN_PASSWORD
    password = os.getenv("ADMIN_PASSWORD", "")
    if password == "dreamteam" or len(password) < 8:
        warnings.append("ADMIN_PASSWORD слишком простой")
    
    # Проверяем DEBUG режим
    debug = os.getenv("DEBUG", "False")
    if debug.lower() == "true":
        warnings.append("DEBUG режим включен в production")
    
    return warnings


# ============================================
# A06:2021 – Vulnerable Components
# ============================================

def check_dependencies() -> list[str]:
    """
    Проверяет зависимости на известные уязвимости
    Примечание: В реальном проекте используйте pip-audit
    
    Returns:
        Список предупреждений
    """
    warnings = []
    
    try:
        import pkg_resources
        
        # Список известных уязвимых версий (пример)
        vulnerable = {
            "fastapi": ["0.68.0", "0.68.1"],  # Пример
            "sqlalchemy": ["1.3.0"],  # Пример
        }
        
        for package_name, bad_versions in vulnerable.items():
            try:
                package = pkg_resources.get_distribution(package_name)
                if package.version in bad_versions:
                    warnings.append(f"{package_name} {package.version} имеет уязвимости")
            except pkg_resources.DistributionNotFound:
                pass
    
    except Exception:
        pass
    
    return warnings


# ============================================
# A07:2021 – Authentication Failures
# ============================================

def validate_session(session: dict) -> bool:
    """
    Проверяет валидность сессии
    
    Args:
        session: Сессия пользователя
    
    Returns:
        True если сессия валидна
    """
    import time
    
    # Проверяем что сессия существует
    if not session:
        return False
    
    # Проверяем что пользователь авторизован
    if not session.get("admin"):
        return False
    
    # Проверяем время создания сессии (если есть)
    if "created_at" in session:
        created_at = session["created_at"]
        current_time = time.time()
        
        # Сессия живет максимум 1 час (3600 секунд)
        if current_time - created_at > 3600:
            return False
    
    return True


# ============================================
# A08:2021 – Software and Data Integrity
# ============================================

def verify_data_integrity(data: dict, expected_fields: list[str]) -> bool:
    """
    Проверяет целостность данных
    
    Args:
        data: Данные для проверки
        expected_fields: Ожидаемые поля
    
    Returns:
        True если данные корректны
    """
    # Проверяем что все обязательные поля присутствуют
    for field in expected_fields:
        if field not in data:
            return False
    
    # Проверяем что нет лишних полей (защита от mass assignment)
    allowed_fields = set(expected_fields)
    actual_fields = set(data.keys())
    
    if not actual_fields.issubset(allowed_fields):
        return False
    
    return True


# ============================================
# A09:2021 – Logging Failures
# ============================================

def safe_log_data(data: Any) -> str:
    """
    Безопасно логирует данные (удаляет чувствительную информацию)
    
    Args:
        data: Данные для логирования
    
    Returns:
        Безопасная строка для лога
    """
    # Список чувствительных полей
    sensitive_fields = ["password", "token", "secret", "api_key", "credit_card"]
    
    if isinstance(data, dict):
        safe_data = {}
        for key, value in data.items():
            # Скрываем чувствительные поля
            if any(field in key.lower() for field in sensitive_fields):
                safe_data[key] = "***HIDDEN***"
            else:
                safe_data[key] = value
        return str(safe_data)
    
    return str(data)


# ============================================
# A10:2021 – Server-Side Request Forgery
# ============================================

def validate_url_for_ssrf(url: str) -> tuple[bool, str]:
    """
    Проверяет URL на SSRF атаки
    
    Args:
        url: URL для проверки
    
    Returns:
        (is_safe, error_message)
    """
    from urllib.parse import urlparse
    
    if not url:
        return True, ""
    
    try:
        parsed = urlparse(url)
        
        # Разрешаем только http и https
        if parsed.scheme not in ["http", "https"]:
            return False, "Разрешены только http и https"
        
        # Запрещаем localhost и внутренние IP
        forbidden_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "169.254.169.254",  # AWS metadata
        ]
        
        hostname = parsed.hostname or ""
        
        # Проверяем запрещенные хосты
        if hostname.lower() in forbidden_hosts:
            return False, "Запрещен доступ к localhost"
        
        # Проверяем внутренние IP (10.x.x.x, 192.168.x.x, 172.16-31.x.x)
        if hostname.startswith(("10.", "192.168.", "172.")):
            return False, "Запрещен доступ к внутренним IP"
        
        return True, ""
    
    except Exception as e:
        return False, f"Некорректный URL: {str(e)}"


# ============================================
# Дополнительные защиты
# ============================================

def sanitize_html(text: str) -> str:
    """
    Экранирует HTML (защита от XSS)
    
    Args:
        text: Текст с возможным HTML
    
    Returns:
        Безопасный текст
    """
    if not text:
        return ""
    
    # Экранируем HTML символы
    return html.escape(text)


def validate_file_upload(filename: str, allowed_extensions: list[str]) -> tuple[bool, str]:
    """
    Проверяет загружаемый файл
    
    Args:
        filename: Имя файла
        allowed_extensions: Разрешенные расширения
    
    Returns:
        (is_valid, error_message)
    """
    if not filename:
        return False, "Имя файла пустое"
    
    # Проверяем расширение
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if extension not in allowed_extensions:
        return False, f"Разрешены только: {', '.join(allowed_extensions)}"
    
    # Проверяем на path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Некорректное имя файла"
    
    return True, ""


def generate_csrf_token() -> str:
    """
    Генерирует CSRF токен
    
    Returns:
        CSRF токен
    """
    import secrets
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """
    Проверяет CSRF токен
    
    Args:
        token: Токен из формы
        session_token: Токен из сессии
    
    Returns:
        True если токен валиден
    """
    if not token or not session_token:
        return False
    
    return token == session_token
