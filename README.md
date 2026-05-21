# 🌸 Цветашки Крым

> Сезонные явления Крыма — веб-приложение и Telegram бот

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

---

## 📖 О проекте

Веб-приложение и Telegram-бот для отслеживания сезонных явлений в Крыму.

### Что можно отслеживать

| Категория | Примеры |
|---|---|
| 🌺 Цветение | лаванда, сакура, маки, пионы, глициния, подснежники |
| 🌅 Визуальные эффекты | закаты, туманы, гало |
| 🍇 Урожай | черешня, виноград |
| 🐬 Животные | дельфины |
| 🎪 Мероприятия | фестивали, ярмарки |

---

## ⚙️ Переменные окружения (.env)

Создайте файл `.env` в корне проекта:

```env
# Обязательные
SESSION_SECRET=ваша-случайная-строка-из-32-символов
ADMIN_PASSWORD=ваш-пароль-для-админки
DATABASE_URL=sqlite:///./data/tsvetashki.db

# Опциональные
OPENWEATHER_API_KEY=
TELEGRAM_BOT_TOKEN=
BASE_URL=http://localhost:8000
```

---

## 🔐 Генерация SESSION_SECRET

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🚀 Запуск

### Способ 1 — локальный запуск

#### 1) Клонирование репозитория

```bash
git clone https://github.com/videmyy/tsvetashki-krym.git
cd tsvetashki-krym
```

---

#### 2) Создание виртуального окружения

```bash
python -m venv venv
```

---

#### 3) Активация окружения

**Windows**

```bash
venv\Scripts\activate
```

**Linux / Mac**

```bash
source venv/bin/activate
```

---

#### 4) Установка зависимостей

```bash
pip install -r requirements.txt
```

---

#### 5) Создание `.env`

**Windows**

```bash
copy .env.example .env
```

**Linux / Mac**

```bash
cp .env.example .env
```

---

#### 6) Запуск приложения

```bash
uvicorn main:app --reload --port 8000
```

После запуска приложение будет доступно по адресу:

```text
http://localhost:8000
```

---

### Способ 2 — запуск через Docker

#### Запуск backend

```bash
docker compose up backend
```

#### Запуск Telegram-бота

```bash
docker compose --profile bot up
```

#### Остановка контейнеров

```bash
docker compose down
```

---

## 🤖 Telegram Бот

### Команды

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

### Популярные slug-и

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
├── routers/              # Маршруты FastAPI (admin, api, pages)
├── services/             # Бизнес-логика (weather, forecast, icon_map)
├── static/               # Статические файлы
│   ├── css/              # Стили
│   ├── js/               # JavaScript (theme, petals, fireflies, map)
│   └── img/              # Изображения
├── templates/            # HTML шаблоны (Jinja2)
│   ├── admin/            # Админ-панель
│   ├── base.html         # Базовый шаблон
│   ├── feed.html         # Лента событий
│   ├── map.html          # Карта
│   └── phenomenon.html   # Страница явления
├── telegram_bot/         # Telegram бот
│   ├── bot.py            # Основная логика бота
│   └── notification_worker.py  # Отправка уведомлений
├── utils/                # Утилиты (dates)
├── data/                 # База данных
├── docs/                 # Документация разработки
├── scripts/              # Вспомогательные скрипты
│   └── seed.py           # Наполнение тестовыми данными
│
├── main.py               # Точка входа приложения
├── models.py             # Модели базы данных (SQLAlchemy)
├── database.py           # Настройка подключения к БД
│
├── requirements.txt      # Зависимости Python
├── docker-compose.yml    # Конфигурация Docker
├── Dockerfile            # Docker образ
├── .env.example          # Пример переменных окружения
└── README.md             # Этот файл
```

---

## 📡 API Эндпоинты

| Метод | Endpoint | Описание |
|---|---|---|
| `GET` | `/api/events` | Список событий с фильтрами |
| `GET` | `/api/events/map` | События для карты |
| `GET` | `/api/phenomena/{slug}` | Детальная информация о явлении |
| `GET` | `/api/filters/meta` | Список доступных фильтров |
| `POST` | `/api/subscribe` | Подписка на уведомления |

---

## 🐛 Решение проблем

### 1) База данных не создаётся

```bash
python -c "from main import app, lifespan; import asyncio; asyncio.run(lifespan(app))"
```

---

### 2) Порт 8000 уже занят (Windows)

#### Найти процесс

```bash
netstat -ano | findstr :8000
```

#### Завершить процесс

```bash
taskkill /PID <PID> /F
```

---

### 3) Docker контейнеры не запускаются

#### Полная очистка

```bash
docker compose down -v
```

#### Пересборка

```bash
docker compose build --no-cache
```

#### Повторный запуск

```bash
docker compose up
```

---

## 📞 Контакты

| Платформа | Контакт |
|---|---|
| GitHub | `@videmyy` |
| Email | `videmyy@gmail.com` |

---

## ❤️ Благодарности

Сделано с ❤️ для Крыма
