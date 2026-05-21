# Руководство для разработчиков

## Структура проекта

### Backend (FastAPI)
- `main.py` - точка входа, настройка приложения
- `models.py` - модели базы данных (SQLAlchemy)
- `database.py` - подключение к БД
- `routers/` - маршруты API и страниц
  - `admin.py` - админ-панель
  - `api.py` - REST API
  - `pages.py` - HTML страницы
- `services/` - бизнес-логика
  - `weather.py` - получение погоды
  - `forecast.py` - прогноз для событий
  - `icon_map.py` - маппинг иконок

### Frontend
- `templates/` - Jinja2 шаблоны
- `static/css/style.css` - все стили (единый файл)
- `static/js/` - JavaScript модули
  - `theme.js` - переключение темы, анимации
  - `petals.js` - анимация сакуры
  - `fireflies.js` - анимация светлячков
  - `map.js` - интерактивная карта

### Telegram Bot
- `telegram_bot/bot.py` - основная логика
- `telegram_bot/notification_worker.py` - уведомления

## Разработка

### Локальный запуск

```bash
# Активировать окружение
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Запустить сервер
uvicorn main:app --reload --port 8000
```

### Docker

```bash
# Backend
docker compose up backend

# С ботом
docker compose --profile bot up
```

### База данных

```bash
# Заполнить тестовыми данными
python scripts/seed.py
```

## Стилизация

### CSS
- Все стили в одном файле: `static/css/style.css`
- CSS переменные для цветов и размеров
- Темная тема через `[data-theme="dark"]`
- Mobile-first подход

### Версионирование
При изменении CSS/JS обновить версию в `templates/base.html`:
```html
<link rel="stylesheet" href="/static/css/style.css?v=16">
```

### Адаптивность
- Desktop: > 640px
- Mobile: ≤ 640px
- Extra small: ≤ 380px

## API

### Основные эндпоинты

```python
GET  /api/events              # Список событий
GET  /api/events/map          # События для карты
GET  /api/phenomena/{slug}    # Детали явления
POST /api/subscribe           # Подписка
GET  /api/filters/meta        # Метаданные фильтров
```

### Фильтры

```python
?extended=1          # Расширенный период
?q=текст             # Поиск
?region=регион       # Фильтр по региону
?subregion=подрегион # Фильтр по подрегиону
?kind=flowering      # Тип явления
?phenomenon_id=1     # Конкретное явление
?month=5             # Месяц
?sort=start          # Сортировка
```

## Telegram Bot

### Команды
- `/start` - приветствие
- `/follow <slug>` - подписка
- `/unfollow <slug>` - отписка
- `/mine` - мои подписки
- `/today` - события сегодня
- `/week` - события на неделю
- `/search <текст>` - поиск

### Уведомления
Worker проверяет события каждый час и отправляет уведомления подписчикам.

## Тестирование

### Проверка API
```bash
curl http://localhost:8000/api/events
```

### Проверка бота
```bash
python -m telegram_bot
```

## Деплой

### Переменные окружения
Обязательно установить в `.env`:
- `SESSION_SECRET` - для сессий
- `ADMIN_PASSWORD` - пароль админки
- `DATABASE_URL` - подключение к БД
- `TELEGRAM_BOT_TOKEN` - токен бота (опционально)
- `OPENWEATHER_API_KEY` - API погоды (опционально)

### Docker Compose
```bash
docker compose up -d
```

## Полезные команды

### Очистка кэша Python
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
```

### Обновление зависимостей
```bash
pip freeze > requirements.txt
```

### Логи Docker
```bash
docker compose logs -f backend
docker compose logs -f bot
```

## Соглашения

### Код
- Python: PEP 8
- JavaScript: ES6+
- HTML: семантическая разметка
- CSS: BEM-подобная методология

### Коммиты
```
feat: новая функция
fix: исправление бага
style: изменения стилей
refactor: рефакторинг
docs: документация
```

## Помощь

При возникновении проблем:
1. Проверьте `.env` файл
2. Проверьте логи: `docker compose logs`
3. Проверьте БД: `data/tsvetashki.db`
4. Создайте issue на GitHub
