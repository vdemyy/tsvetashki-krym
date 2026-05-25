#!/usr/bin/env python3
"""
Простой скрипт для проверки безопасности проекта
Проверяет OWASP Top-10 уязвимости
"""

import os
import sys

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.owasp_protection import check_secure_config, check_dependencies


def print_header(text: str):
    """Печатает заголовок"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_config():
    """Проверяет конфигурацию"""
    print_header("Проверка конфигурации")
    
    warnings = check_secure_config()
    
    if not warnings:
        print("✅ Конфигурация безопасна")
        return True
    
    print("⚠️  Найдены проблемы:")
    for warning in warnings:
        print(f"   - {warning}")
    
    return False


def check_deps():
    """Проверяет зависимости"""
    print_header("Проверка зависимостей")
    
    warnings = check_dependencies()
    
    if not warnings:
        print("✅ Зависимости безопасны")
        return True
    
    print("⚠️  Найдены уязвимости:")
    for warning in warnings:
        print(f"   - {warning}")
    
    return False


def check_files():
    """Проверяет наличие важных файлов"""
    print_header("Проверка файлов")
    
    important_files = [
        ".env",
        ".gitignore",
        "requirements.txt",
        "utils/security.py",
        "utils/owasp_protection.py",
        "utils/logger.py",
    ]
    
    all_ok = True
    
    for file in important_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - НЕ НАЙДЕН")
            all_ok = False
    
    return all_ok


def check_env_vars():
    """Проверяет переменные окружения"""
    print_header("Проверка переменных окружения")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "SESSION_SECRET",
        "ADMIN_PASSWORD",
        "DATABASE_URL",
    ]
    
    all_ok = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Показываем только первые 3 символа
            masked = value[:3] + "***" if len(value) > 3 else "***"
            print(f"✅ {var} = {masked}")
        else:
            print(f"❌ {var} - НЕ УСТАНОВЛЕНА")
            all_ok = False
    
    return all_ok


def check_gitignore():
    """Проверяет .gitignore"""
    print_header("Проверка .gitignore")
    
    if not os.path.exists(".gitignore"):
        print("❌ .gitignore не найден")
        return False
    
    with open(".gitignore", "r", encoding="utf-8") as f:
        content = f.read()
    
    important_patterns = [
        ".env",
        "*.log",
        "logs/",
        "__pycache__",
        "*.pyc",
    ]
    
    all_ok = True
    
    for pattern in important_patterns:
        if pattern in content:
            print(f"✅ {pattern}")
        else:
            print(f"⚠️  {pattern} - НЕ НАЙДЕН")
            all_ok = False
    
    return all_ok


def main():
    """Главная функция"""
    print("\n🔒 ПРОВЕРКА БЕЗОПАСНОСТИ ПРОЕКТА")
    print("=" * 60)
    
    results = []
    
    # Проверяем все аспекты
    results.append(("Конфигурация", check_config()))
    results.append(("Зависимости", check_deps()))
    results.append(("Файлы", check_files()))
    results.append(("Переменные окружения", check_env_vars()))
    results.append((".gitignore", check_gitignore()))
    
    # Итоги
    print_header("ИТОГИ")
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nПройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 Все проверки пройдены!")
        return 0
    else:
        print("\n⚠️  Есть проблемы, требующие внимания")
        return 1


if __name__ == "__main__":
    sys.exit(main())
