# Защита от OWASP Top-10 уязвимостей
# Простые функции для студенческого проекта

import re
import html
import os
import time
import secrets
import hashlib
from datetime import date


# Проверка прав доступа
def check_user_permission(session, required_role="admin"):
    """Проверяет что пользователь авторизован"""
    if not session.get("admin"):
        return False
    return True


# Хеширование паролей
def hash_password(password):
    """Хеширует пароль с солью"""
    salt = "tsvetashki_salt_2024"
    password_with_salt = password + salt
    hashed = hashlib.sha256(password_with_salt.encode()).hexdigest()
    return hashed


def check_password(password, hashed):
    """Проверяет пароль"""
    return hash_password(password) == hashed


# Защита от SQL injection
def sanitize_sql_input(value):
    """Удаляет опасные SQL команды из ввода"""
    if not value:
        return ""
    
    # Список опасных слов
    dangerous_words = ["DROP", "DELETE", "UPDATE", "INSERT", "UNION", "SELECT", "EXEC", "EXECUTE"]
    
    # Удаляем опасные слова
    for word in dangerous_words:
        value = re.sub(word, "", value, flags=re.IGNORECASE)
    
    # Удаляем опасные символы
    value = value.replace("--", "")
    value = value.replace(";", "")
    value = value.replace("/*", "")
    value = value.replace("*/", "")
    
    return value.strip()


def sanitize_command_input(value):
    """Удаляет опасные символы для команд ОС"""
    if not value:
        return ""
    
    # Удаляем опасные символы
    dangerous_chars = [";", "|", "&", "$", "`", "\n", "\r"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    
    return value.strip()


# Проверка бизнес-логики
def validate_business_logic(data):
    """Проверяет что даты и интенсивность корректны"""
    # Проверяем даты
    if "start_date" in data and "peak_date" in data and "end_date" in data:
        start = data["start_date"]
        peak = data["peak_date"]
        end = data["end_date"]
        
        # Конвертируем строки в даты если нужно
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(peak, str):
            peak = date.fromisoformat(peak)
        if isinstance(end, str):
            end = date.fromisoformat(end)
        
        # Проверяем порядок дат
        if not (start <= peak <= end):
            return False, "Даты должны быть в порядке: начало <= пик <= конец"
    
    # Проверяем интенсивность
    if "intensity" in data:
        intensity = data["intensity"]
        if intensity < 1 or intensity > 5:
            return False, "Интенсивность должна быть от 1 до 5"
    
    return True, ""


# Проверка конфигурации
def check_secure_config():
    """Проверяет что настройки безопасности в порядке"""
    warnings = []
    
    # Проверяем секретный ключ
    secret = os.getenv("SESSION_SECRET", "")
    if secret == "change-me-in-production" or len(secret) < 32:
        warnings.append("SESSION_SECRET слишком простой")
    
    # Проверяем пароль админа
    password = os.getenv("ADMIN_PASSWORD", "")
    if password == "dreamteam" or len(password) < 8:
        warnings.append("ADMIN_PASSWORD слишком простой")
    
    # Проверяем DEBUG режим
    debug = os.getenv("DEBUG", "False")
    if debug.lower() == "true":
        warnings.append("DEBUG режим включен")
    
    return warnings


# Проверка зависимостей
def check_dependencies():
    """Проверяет версии библиотек на уязвимости"""
    warnings = []
    
    try:
        import pkg_resources
        
        # Известные уязвимые версии
        vulnerable = {
            "fastapi": ["0.68.0", "0.68.1"],
            "sqlalchemy": ["1.3.0"],
        }
        
        for package_name, bad_versions in vulnerable.items():
            try:
                package = pkg_resources.get_distribution(package_name)
                if package.version in bad_versions:
                    warnings.append(f"{package_name} {package.version} имеет уязвимости")
            except:
                pass
    except:
        pass
    
    return warnings


# Проверка сессии
def validate_session(session):
    """Проверяет что сессия валидна"""
    if not session:
        return False
    
    if not session.get("admin"):
        return False
    
    # Проверяем время жизни сессии (1 час)
    if "created_at" in session:
        created_at = session["created_at"]
        current_time = time.time()
        if current_time - created_at > 3600:
            return False
    
    return True


# Проверка целостности данных
def verify_data_integrity(data, expected_fields):
    """Проверяет что все нужные поля есть и нет лишних"""
    # Проверяем обязательные поля
    for field in expected_fields:
        if field not in data:
            return False
    
    # Проверяем что нет лишних полей
    allowed_fields = set(expected_fields)
    actual_fields = set(data.keys())
    if not actual_fields.issubset(allowed_fields):
        return False
    
    return True


# Безопасное логирование
def safe_log_data(data):
    """Скрывает чувствительные данные в логах"""
    sensitive_fields = ["password", "token", "secret", "api_key"]
    
    if isinstance(data, dict):
        safe_data = {}
        for key, value in data.items():
            # Скрываем пароли и токены
            if any(field in key.lower() for field in sensitive_fields):
                safe_data[key] = "***HIDDEN***"
            else:
                safe_data[key] = value
        return str(safe_data)
    
    return str(data)


# Защита от SSRF
def validate_url_for_ssrf(url):
    """Проверяет что URL безопасный"""
    from urllib.parse import urlparse
    
    if not url:
        return True, ""
    
    try:
        parsed = urlparse(url)
        
        # Только http и https
        if parsed.scheme not in ["http", "https"]:
            return False, "Разрешены только http и https"
        
        hostname = parsed.hostname or ""
        
        # Запрещаем localhost
        forbidden = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if hostname.lower() in forbidden:
            return False, "Запрещен доступ к localhost"
        
        # Запрещаем внутренние IP
        if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
            return False, "Запрещен доступ к внутренним IP"
        
        return True, ""
    except Exception as e:
        return False, f"Некорректный URL: {str(e)}"


# Защита от XSS
def sanitize_html(text):
    """Экранирует HTML символы"""
    if not text:
        return ""
    return html.escape(text)


# Проверка загружаемых файлов
def validate_file_upload(filename, allowed_extensions):
    """Проверяет что файл безопасный"""
    if not filename:
        return False, "Имя файла пустое"
    
    # Проверяем расширение
    if "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
    else:
        extension = ""
    
    if extension not in allowed_extensions:
        return False, f"Разрешены только: {', '.join(allowed_extensions)}"
    
    # Проверяем на опасные символы
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Некорректное имя файла"
    
    return True, ""


# CSRF токены
def generate_csrf_token():
    """Создает CSRF токен"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token, session_token):
    """Проверяет CSRF токен"""
    if not token or not session_token:
        return False
    return token == session_token
