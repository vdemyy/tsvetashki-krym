# Простые функции для безопасности

import re


def sanitize_string(text, max_length=500):
    """Очищает строку от опасных символов"""
    if not text:
        return ""
    
    # Обрезаем длину
    text = text[:max_length]
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем опасные слова
    text = text.replace('<', '')
    text = text.replace('>', '')
    text = text.replace('javascript:', '')
    text = text.replace('onerror=', '')
    text = text.replace('onclick=', '')
    
    return text.strip()


def validate_email(email):
    """Проверяет что email правильный"""
    if not email:
        return False
    
    # Простая проверка email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_slug(slug):
    """Проверяет что slug содержит только буквы, цифры и дефисы"""
    if not slug:
        return False
    
    # Только буквы, цифры и дефисы
    pattern = r'^[a-z0-9-]+$'
    if not re.match(pattern, slug):
        return False
    
    # Не слишком длинный
    if len(slug) > 100:
        return False
    
    return True


def is_safe_url(url):
    """Проверяет что URL безопасный"""
    if not url:
        return True
    
    # Только http и https
    if not url.startswith('http://') and not url.startswith('https://'):
        return False
    
    # Запрещаем javascript и data
    if 'javascript:' in url.lower() or 'data:' in url.lower():
        return False
    
    return True


def check_password_strength(password):
    """Проверяет надежность пароля"""
    if len(password) < 8:
        return False, "Пароль должен быть минимум 8 символов"
    
    # Проверяем заглавные буквы
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать заглавные буквы"
    
    # Проверяем строчные буквы
    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать строчные буквы"
    
    # Проверяем цифры
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать цифры"
    
    return True, "Пароль надежный"
