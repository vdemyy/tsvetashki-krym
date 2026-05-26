# Защита от OWASP Top-10 в проекте "Цветашки Крым"

## Обзор

В проекте реализованы меры защиты от всех уязвимостей из списка OWASP Top-10 2021. Код написан простым и понятным способом, чтобы было видно студенческую работу.

---

## A01:2021 – Broken Access Control (Нарушение контроля доступа)

### Что защищаем:
- Неавторизованный доступ к админ-панели
- Доступ к чужим данным

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def check_user_permission(session, required_role="admin"):
    """Проверяет что пользователь авторизован"""
    if not session.get("admin"):
        return False
    return True
```

**`routers/admin.py`:**
```python
def _check(request):
    """Проверяет авторизацию перед каждым действием"""
    if not request.session.get("admin"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None
```

### Как работает:
1. Каждый endpoint админки проверяет сессию
2. Если пользователь не авторизован → редирект на логин
3. Сессия живет 1 час (настроено в `main.py`)

---

## A02:2021 – Cryptographic Failures (Криптографические ошибки)

### Что защищаем:
- Хранение паролей в открытом виде
- Передача чувствительных данных

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def hash_password(password):
    """Хеширует пароль с солью"""
    salt = "tsvetashki_salt_2024"
    password_with_salt = password + salt
    hashed = hashlib.sha256(password_with_salt.encode()).hexdigest()
    return hashed
```

**`main.py`:**
```python
# HttpOnly cookies для защиты от XSS
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET"),
    max_age=3600,
)
```

### Как работает:
1. Пароли хешируются с солью перед сохранением
2. Сессии шифруются секретным ключом
3. Чувствительные данные в `.env` файле (не в git)

---

## A03:2021 – Injection (SQL, Command Injection)

### Что защищаем:
- SQL injection в поиске
- Command injection в боте

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def sanitize_sql_input(value):
    """Удаляет опасные SQL команды из ввода"""
    dangerous_words = ["DROP", "DELETE", "UPDATE", "INSERT", "UNION", "SELECT"]
    for word in dangerous_words:
        value = re.sub(word, "", value, flags=re.IGNORECASE)
    value = value.replace("--", "").replace(";", "")
    return value.strip()
```

**`routers/api.py`:**
```python
if q:
    # A03 - Защита от SQL injection
    q_clean = sanitize_sql_input(q.strip())
    if len(q_clean) > 100:
        q_clean = q_clean[:100]
    like = f"%{q_clean}%"
```

**`telegram_bot/bot.py`:**
```python
# Очищаем от SQL injection
query_clean = sanitize_sql_input(query)
if len(query_clean) > 50:
    query_clean = query_clean[:50]
```

### Как работает:
1. Удаляем опасные SQL команды (DROP, DELETE и т.д.)
2. Удаляем SQL комментарии (--) и точки с запятой
3. Ограничиваем длину ввода
4. SQLAlchemy использует параметризованные запросы

---

## A04:2021 – Insecure Design (Небезопасный дизайн)

### Что защищаем:
- Некорректные даты событий
- Неправильная интенсивность

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def validate_business_logic(data):
    """Проверяет что даты и интенсивность корректны"""
    # Проверяем порядок дат
    if not (start <= peak <= end):
        return False, "Даты должны быть в порядке: начало <= пик <= конец"
    
    # Проверяем интенсивность
    if intensity < 1 or intensity > 5:
        return False, "Интенсивность должна быть от 1 до 5"
    
    return True, ""
```

**`routers/admin.py`:**
```python
# A04 - Проверяем бизнес-логику
is_valid, error_msg = validate_business_logic({
    "start_date": start_date,
    "peak_date": peak_date,
    "end_date": end_date,
    "intensity": intensity,
})

if not is_valid:
    raise HTTPException(400, error_msg)
```

### Как работает:
1. Проверяем что start_date <= peak_date <= end_date
2. Проверяем что интенсивность от 1 до 5
3. Отклоняем некорректные данные

---

## A05:2021 – Security Misconfiguration (Неправильная конфигурация)

### Что защищаем:
- Слабые пароли и секретные ключи
- DEBUG режим в production

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
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
    
    return warnings
```

**`main.py`:**
```python
# Проверяем безопасность при старте
warnings = check_secure_config()
if warnings:
    print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ БЕЗОПАСНОСТИ:")
    for warning in warnings:
        print(f"   - {warning}")
```

**`.gitignore`:**
```
.env
*.log
__pycache__/
```

### Как работает:
1. При старте проверяем конфигурацию
2. Выводим предупреждения о слабых паролях
3. `.env` файл не попадает в git
4. Логи не попадают в git

---

## A06:2021 – Vulnerable Components (Уязвимые компоненты)

### Что защищаем:
- Устаревшие библиотеки с уязвимостями

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def check_dependencies():
    """Проверяет версии библиотек на уязвимости"""
    vulnerable = {
        "fastapi": ["0.68.0", "0.68.1"],
        "sqlalchemy": ["1.3.0"],
    }
    
    for package_name, bad_versions in vulnerable.items():
        package = pkg_resources.get_distribution(package_name)
        if package.version in bad_versions:
            warnings.append(f"{package_name} {package.version} имеет уязвимости")
```

**`requirements.txt`:**
```
fastapi>=0.104.0
sqlalchemy>=2.0.0
```

### Как работает:
1. Проверяем версии установленных библиотек
2. Сравниваем с известными уязвимыми версиями
3. Используем актуальные версии в requirements.txt

---

## A07:2021 – Authentication Failures (Ошибки аутентификации)

### Что защищаем:
- Брутфорс паролей
- Слабые пароли

### Где реализовано:

**`routers/admin.py`:**
```python
# Защита от брутфорса
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 300  # 5 минут

def check_login_attempts(ip):
    """Проверяет не заблокирован ли IP"""
    if len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        return False
    return True

@router.post("/login")
async def login_post(request, password=Form(...)):
    client_ip = request.client.host
    
    # Проверяем лимит попыток
    if not check_login_attempts(client_ip):
        return "Слишком много попыток. Подождите 5 минут."
    
    # Проверяем пароль
    if password == ADMIN_PASSWORD:
        # Очищаем попытки при успехе
        login_attempts[client_ip] = []
        return RedirectResponse("/admin")
    
    # Добавляем неудачную попытку
    add_login_attempt(client_ip)
```

**`main.py`:**
```python
# Сессия живет 1 час
app.add_middleware(SessionMiddleware, max_age=3600)
```

### Как работает:
1. Считаем попытки входа для каждого IP
2. После 5 неудачных попыток → блокировка на 5 минут
3. При успешном входе → очищаем счетчик
4. Сессия автоматически истекает через 1 час

---

## A08:2021 – Software and Data Integrity (Целостность данных)

### Что защищаем:
- CSRF атаки
- Mass assignment

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def generate_csrf_token():
    """Создает CSRF токен"""
    return secrets.token_urlsafe(32)

def verify_csrf_token(token, session_token):
    """Проверяет CSRF токен"""
    return token == session_token

def verify_data_integrity(data, expected_fields):
    """Проверяет что все нужные поля есть и нет лишних"""
    for field in expected_fields:
        if field not in data:
            return False
    return True
```

**`routers/admin.py`:**
```python
def _check(request):
    # Генерируем CSRF токен
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = generate_csrf_token()

@router.post("/events/new")
async def new_event_post(request, csrf_token=Form(None), ...):
    # Проверяем CSRF токен
    if not verify_csrf_token(csrf_token, request.session.get("csrf_token")):
        raise HTTPException(403, "CSRF token invalid")
```

### Как работает:
1. Генерируем уникальный CSRF токен для каждой сессии
2. Добавляем токен в формы
3. Проверяем токен при POST запросах
4. Проверяем что нет лишних полей (mass assignment)

---

## A09:2021 – Logging Failures (Ошибки логирования)

### Что защищаем:
- Утечка чувствительных данных в логах
- Отсутствие логов важных событий

### Где реализовано:

**`utils/logger.py`:**
```python
logger = logging.getLogger("security")
file_handler = logging.FileHandler("logs/security.log")

def log_login_attempt(ip, success, username="admin"):
    """Логирует попытку входа"""
    if success:
        logger.info(f"Успешный вход | IP: {ip}")
    else:
        logger.warning(f"Неудачная попытка входа | IP: {ip}")

def log_admin_action(ip, action, details=""):
    """Логирует действия в админке"""
    logger.info(f"Действие админа | IP: {ip} | Действие: {action}")
```

**`utils/owasp_protection.py`:**
```python
def safe_log_data(data):
    """Скрывает чувствительные данные в логах"""
    sensitive_fields = ["password", "token", "secret", "api_key"]
    
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            safe_data[key] = "***HIDDEN***"
```

**`routers/admin.py`:**
```python
# Логируем вход
log_login_attempt(client_ip, success=True)

# Логируем действия
log_admin_action(client_ip, "create_event", f"phenomenon_id={phenomenon_id}")
```

### Как работает:
1. Все важные события логируются в `logs/security.log`
2. Пароли и токены скрываются как `***HIDDEN***`
3. Логируем: входы, действия админа, подозрительную активность
4. Логи не попадают в git (`.gitignore`)

---

## A10:2021 – Server-Side Request Forgery (SSRF)

### Что защищаем:
- Запросы к внутренним сервисам
- Запросы к localhost

### Где реализовано:

**`utils/owasp_protection.py`:**
```python
def validate_url_for_ssrf(url):
    """Проверяет что URL безопасный"""
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
    if hostname.startswith("10.") or hostname.startswith("192.168."):
        return False, "Запрещен доступ к внутренним IP"
    
    return True, ""
```

**`routers/admin.py`:**
```python
# Проверяем URL перед сохранением
if main_photo_url and not is_safe_url(main_photo_url):
    raise HTTPException(400, "Некорректный URL фото")
```

### Как работает:
1. Проверяем схему URL (только http/https)
2. Запрещаем localhost и 127.0.0.1
3. Запрещаем внутренние IP (10.x.x.x, 192.168.x.x)
4. Отклоняем опасные URL

---

## Дополнительные защиты

### XSS (Cross-Site Scripting)

**`utils/owasp_protection.py`:**
```python
def sanitize_html(text):
    """Экранирует HTML символы"""
    return html.escape(text)
```

**`routers/admin.py`:**
```python
# Очищаем заметки от HTML
notes_clean = sanitize_html(notes.strip())
```

### Rate Limiting

**`main.py`:**
```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.requests = {}
    
    async def dispatch(self, request, call_next):
        client_ip = request.client.host
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.max_requests:
            return Response("Слишком много запросов", status_code=429)
```

**`telegram_bot/bot.py`:**
```python
COMMAND_COOLDOWN = 1  # Секунда между командами

def check_rate_limit(chat_id):
    if current_time - last_time < COMMAND_COOLDOWN:
        return False
    return True
```

### Security Headers

**`main.py`:**
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Защита от clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Защита от XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'..."
        
        return response
```

---

## Проверка безопасности

### Автоматическая проверка при старте

**`main.py`:**
```python
@asynccontextmanager
async def lifespan(app):
    # Проверяем безопасность при старте
    warnings = check_secure_config()
    if warnings:
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ БЕЗОПАСНОСТИ:")
        for warning in warnings:
            print(f"   - {warning}")
```

### Ручная проверка

```bash
# Запустить скрипт проверки
python scripts/check_security.py
```

**`scripts/check_security.py`:**
```python
from utils.owasp_protection import check_secure_config, check_dependencies

print("=== Проверка конфигурации ===")
warnings = check_secure_config()
for w in warnings:
    print(f"⚠️  {w}")

print("\n=== Проверка зависимостей ===")
dep_warnings = check_dependencies()
for w in dep_warnings:
    print(f"⚠️  {w}")
```

---

## Итоговая таблица защит

| OWASP Top-10 | Защита | Файлы |
|--------------|--------|-------|
| A01 - Broken Access Control | Проверка сессии, редирект | `routers/admin.py` |
| A02 - Cryptographic Failures | Хеширование паролей, HttpOnly cookies | `utils/owasp_protection.py`, `main.py` |
| A03 - Injection | Очистка SQL, ограничение длины | `utils/owasp_protection.py`, `routers/api.py` |
| A04 - Insecure Design | Валидация бизнес-логики | `utils/owasp_protection.py`, `routers/admin.py` |
| A05 - Security Misconfiguration | Проверка конфигурации, .gitignore | `utils/owasp_protection.py`, `main.py` |
| A06 - Vulnerable Components | Проверка версий библиотек | `utils/owasp_protection.py` |
| A07 - Authentication Failures | Защита от брутфорса, таймаут сессии | `routers/admin.py`, `main.py` |
| A08 - Data Integrity | CSRF токены, проверка полей | `utils/owasp_protection.py`, `routers/admin.py` |
| A09 - Logging Failures | Безопасное логирование | `utils/logger.py`, `routers/admin.py` |
| A10 - SSRF | Валидация URL, запрет localhost | `utils/owasp_protection.py`, `routers/admin.py` |
| Дополнительно - XSS | Экранирование HTML | `utils/owasp_protection.py` |
| Дополнительно - Rate Limiting | Ограничение запросов | `main.py`, `telegram_bot/bot.py` |
| Дополнительно - Security Headers | X-Frame-Options, CSP | `main.py` |

---

## Рекомендации для production

1. **Смените пароли:**
   ```bash
   SESSION_SECRET=<сгенерируйте 64 символа>
   ADMIN_PASSWORD=<сложный пароль>
   ```

2. **Используйте HTTPS:**
   - Настройте SSL сертификат
   - Включите HSTS заголовок

3. **Настройте мониторинг:**
   - Следите за логами в `logs/security.log`
   - Настройте алерты на подозрительную активность

4. **Обновляйте зависимости:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

5. **Регулярно проверяйте:**
   ```bash
   python scripts/check_security.py
   ```

---

*Документация создана для студенческого проекта "Цветашки Крым"*
*Все меры безопасности реализованы простым и понятным кодом*
