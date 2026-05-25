# Простые функции для безопасности

import re


def sanitize_string(text: str, max_length: int = 500) -> str:
    """
    Очищает строку от опасных символов
    
    Args:
        text: Входная строка
        max_length: Максимальная длина
    
    Returns:
        Очищенная строка
    """
    if not text:
        return ""
    
    # Обрезаем до максимальной длины
    text = text[:max_length]
    
    # Удаляем HTML теги (простая защита от XSS)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем опасные символы
    text = text.replace('<', '').replace('>', '')
    text = text.replace('javascript:', '')
    text = text.replace('onerror=', '')
    text = text.replace('onclick=', '')
    
    return text.strip()


def validate_email(email: str) -> bool:
    """
    Проверяет корректность email
    
    Args:
        email: Email адрес
    
    Returns:
        True если email корректный
    """
    if not email:
        return False
    
    # Простая проверка email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_slug(slug: str) -> bool:
    """
    Проверяет корректность slug
    
    Args:
        slug: Slug для проверки
    
    Returns:
        True если slug корректный
    """
    if not slug:
        return False
    
    # Slug должен содержать только буквы, цифры, дефисы
    pattern = r'^[a-z0-9-]+$'
    return bool(re.match(pattern, slug)) and len(slug) <= 100


def is_safe_url(url: str) -> bool:
    """
    Проверяет безопасность URL
    
    Args:
        url: URL для проверки
    
    Returns:
        True если URL безопасный
    """
    if not url:
        return True  # Пустой URL допустим
    
    # Разрешаем только http и https
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Запрещаем javascript: и data:
    if 'javascript:' in url.lower() or 'data:' in url.lower():
        return False
    
    return True


def check_password_strength(password: str) -> tuple[bool, str]:
    """
    Проверяет надежность пароля
    
    Args:
        password: Пароль для проверки
    
    Returns:
        (is_strong, message) - результат и сообщение
    """
    if len(password) < 8:
        return False, "Пароль должен быть минимум 8 символов"
    
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать заглавные буквы"
    
    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать строчные буквы"
    
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать цифры"
    
    return True, "Пароль надежный"
