### 2) Создание виртуального окружения

```bash
python -m venv venv
```

---

### 3) Активация окружения

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

---

### 4) Установка зависимостей

```bash
pip install -r requirements.txt
```

---

### 5) Создание `.env`

**Windows**

```bash
copy .env.example .env
```

**Linux / macOS**

```bash
cp .env.example .env
```

---

### 6) Запуск приложения

```bash
uvicorn main:app --reload --port 8000
```

После запуска приложение будет доступно по адресу:

```text
http://localhost:8000
```

---

## 🐳 Docker

### Запуск backend

```bash
docker compose up backend
```

### Запуск Telegram-бота

```bash
docker compose --profile bot up
```

### Остановка контейнеров

```bash
docker compose down
```

---

## 🤖 Telegram Бот

| Команда | Описание |
|---|---|
| `/start` | Приветствие |
| `/help` | Справка |
| `/follow <slug>` | Подписаться на явление |
| `/unfollow <slug>` | Отписаться от явления |
| `/mine` | Мои подписки |
| `/today` | Что происходит сегодня |
| `/week` | События на неделю |
| `/search <текст>` | Поиск явлений |

---

## 🌸 Популярные slug-и

| Явление | slug |
|---|---|
| Лаванда | `lavanda-turgenevka` |
| Сакура | `sakura-nikitsky` |
| Маки | `maki-koktebel` |
| Глициния | `glycine-alupka` |
| Пионы | `piony-nbs` |
| Подснежники | `podsnezhniki-laspi` |
| Закаты | `zakat-fiorent` |
| Черешня | `cherry-kerch` |

---

## 📁 Структура проекта

```text
tsvetashki-krym/
│
├── routers/             # Маршруты FastAPI
├── services/            # Бизнес-логика
├── static/              # CSS, JavaScript
├── templates/           # HTML шаблоны
├── telegram_bot/        # Telegram бот
├── data/                # SQLite база данных
│
├── main.py              # Точка входа
├── models.py            # Модели БД
├── database.py          # Подключение к БД
├── seed.py              # Тестовые данные
│
├── requirements.txt     # Python зависимости
├── docker-compose.yml   # Docker конфигурация
└── .env.example         # Пример .env
```

---

## 📡 API Эндпоинты

| Метод | Endpoint | Описание |
|---|---|---|
| `GET` | `/api/events` | Список событий |
| `GET` | `/api/events/map` | События для карты |
| `GET` | `/api/phenomena/{slug}` | Детали явления |
| `GET` | `/api/filters/meta` | Доступные фильтры |
| `POST` | `/api/subscribe` | Подписка на уведомления |

---

## 🐛 Решение проблем

### База данных не создаётся

```bash
python -c "from main import app, lifespan; import asyncio; asyncio.run(lifespan(app))"
```

---

### Порт `8000` уже занят (Windows)

**Найти процесс**

```bash
netstat -ano | findstr :8000
```

**Завершить процесс**

```bash
taskkill /PID <PID> /F
```

---

### Docker контейнеры не запускаются

**Полная очистка**

```bash
docker compose down -v
```

**Пересборка**

```bash
docker compose build --no-cache
```

**Повторный запуск**

```bash
docker compose up
```

---

## 📞 Контакты

| Контакт | Ссылка |
|---|---|
| GitHub | `@videmyy` |
| Email | `videmyy@gmail.com` |

---

## ❤️ Благодарности

Сделано с любовью для Крыма 🌊🌸
