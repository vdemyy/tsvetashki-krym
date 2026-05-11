🌸 Цветашки Крым
Сезонные явления Крыма — веб-приложение и Telegram бот

-------------------------------------------------------------------------------

О проекте

Веб-приложение и Telegram-бот для отслеживания сезонных явлений в Крыму.

Что можно отслеживать:

🌺 Цветение: лаванда, сакура, маки, пионы, глициния, подснежники
🌅 Визуальные эффекты: закаты, туманы, гало
🍇 Урожай: черешня, виноград
🐬 Животные: дельфины
🎪 Мероприятия: фестивали, ярмарки

-------------------------------------------------------------------------------

Переменные окружения (.env)

Создайте файл .env в корне проекта:

# Обязательные
SESSION_SECRET=ваша-случайная-строка-из-32-символов
ADMIN_PASSWORD=ваш-пароль-для-админки
DATABASE_URL=sqlite:///./data/tsvetashki.db

# Опциональные
OPENWEATHER_API_KEY=
TELEGRAM_BOT_TOKEN=
BASE_URL=http://localhost:8000

Как сгенерировать SESSION_SECRET:

python -c "import secrets; print(secrets.token_urlsafe(32))"

-------------------------------------------------------------------------------

Запуск

Способ 1: Локальный запуск

git clone https://github.com/videmyy/tsvetashki-krym.git
cd tsvetashki-krym
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000

Способ 2: Запуск через Docker

docker compose up backend
docker compose --profile bot up
docker compose down

-------------------------------------------------------------------------------

Telegram Бот

Команды:

/start - Приветствие
/help - Справка
/follow <slug> - Подписаться
/unfollow <slug> - Отписаться
/mine - Мои подписки
/today - Что сегодня
/week - Что на неделе
/search <текст> - Поиск

Популярные slug-и:

Лаванда ......... lavanda-turgenevka
Сакура ......... sakura-nikitsky
Маки ........... maki-koktebel
Глициния ....... glycine-alupka
Пионы .......... piony-nbs
Подснежники .... podsnezhniki-laspi
Закаты ......... zakat-fiorent
Черешня ........ cherry-kerch

-------------------------------------------------------------------------------

Структура проекта

tsvetashki-krym/
├── routers/          # Маршруты FastAPI
├── services/         # Бизнес-логика
├── static/           # CSS, JS
├── templates/        # HTML шаблоны
├── telegram_bot/     # Telegram бот
├── data/             # База данных
├── main.py           # Точка входа
├── models.py         # Модели БД
├── database.py       # Настройка БД
├── seed.py           # Наполнение данными
├── requirements.txt  # Зависимости
├── docker-compose.yml
└── .env.example

-------------------------------------------------------------------------------

API Эндпоинты

GET /api/events - Список событий
GET /api/events/map - События для карты
GET /api/phenomena/{slug} - Детали явления
GET /api/filters/meta - Доступные фильтры
POST /api/subscribe - Подписка

-------------------------------------------------------------------------------

Решение проблем

Если база данных не создаётся:

python -c "from main import app, lifespan; import asyncio; asyncio.run(lifespan(app))"

Если порт 8000 занят (Windows):

netstat -ano | findstr :8000
taskkill /PID <PID> /F

Если Docker не запускается:

docker compose down -v
docker compose build --no-cache
docker compose up

-------------------------------------------------------------------------------

Контакты

GitHub: @videmyy
Email: videmyy@gmail.com
