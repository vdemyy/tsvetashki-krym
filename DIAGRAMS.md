# Диаграммы UML для проекта "Цветашки Крым"

## 1. Диаграмма классов (Class Diagram)

```mermaid
classDiagram
    class Phenomenon {
        +int id
        +string slug
        +string name
        +string kind
        +string category
        +text description
        +string typical_season
        +string icon_emoji
        +string icon_lucide
        +string main_photo_url
        +string website_url
        +float water_temp_c
    }

    class Place {
        +int id
        +string name
        +string region
        +string subregion
        +float latitude
        +float longitude
    }

    class Event {
        +int id
        +int phenomenon_id
        +int place_id
        +date start_date
        +date peak_date
        +date end_date
        +int intensity
        +json phase_history
        +text notes
    }

    class Subscription {
        +int id
        +string email
        +int phenomenon_id
        +datetime created_at
        +bool active
    }

    class TelegramWatch {
        +int id
        +bigint chat_id
        +int phenomenon_id
        +datetime created_at
    }

    Phenomenon "1" --> "*" Event : has
    Place "1" --> "*" Event : hosts
    Phenomenon "1" --> "*" Subscription : subscribed_to
    Phenomenon "1" --> "*" TelegramWatch : watched_by
```

## 2. Диаграмма вариантов использования (Use Case Diagram)

```mermaid
graph TB
    subgraph "Система Цветашки Крым"
        UC1[Просмотр ленты событий]
        UC2[Фильтрация событий]
        UC3[Просмотр карты]
        UC4[Просмотр явления]
        UC5[Подписка на явление]
        UC6[Управление событиями]
        UC7[Управление явлениями]
        UC8[Управление местами]
        UC9[Вход в админку]
        UC10[Подписка через Telegram]
        UC11[Получение уведомлений]
        UC12[Поиск явлений]
        UC13[Просмотр погоды]
    end

    User((Пользователь))
    Admin((Администратор))
    TgUser((Telegram<br/>пользователь))
    System((Система<br/>уведомлений))

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC12
    User --> UC13

    Admin --> UC6
    Admin --> UC7
    Admin --> UC8
    Admin --> UC9

    TgUser --> UC10
    TgUser --> UC12
    System --> UC11

    UC2 -.-> UC1
    UC5 -.-> UC4
    UC6 -.-> UC9
    UC7 -.-> UC9
    UC8 -.-> UC9
```

## 3. Диаграммы последовательностей (Sequence Diagrams)

### 3.1. Сценарий: Просмотр ленты событий с фильтрацией

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant Browser as Браузер
    participant Server as FastAPI Server
    participant DB as База данных
    participant Weather as OpenWeather API

    User->>Browser: Открывает главную страницу
    Browser->>Server: GET /
    Server->>DB: SELECT events WHERE end_date >= today
    DB-->>Server: Список событий
    Server->>DB: SELECT regions, kinds, subregions
    DB-->>Server: Метаданные для фильтров
    Server-->>Browser: HTML страница с событиями
    Browser-->>User: Отображение ленты

    User->>Browser: Выбирает фильтр (регион, тип)
    Browser->>Server: GET /?region=X&kind=Y
    Server->>DB: SELECT events WHERE region=X AND kind=Y
    DB-->>Server: Отфильтрованные события
    Server-->>Browser: Обновленная лента
    Browser-->>User: Отображение результатов

    User->>Browser: Клик на место события
    Browser->>Weather: GET /api/weather/hint?lat=X&lon=Y
    Weather-->>Browser: Данные о погоде
    Browser-->>User: Показ погоды в popup
```

### 3.2. Сценарий: Подписка на явление через сайт

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant Browser as Браузер
    participant Server as FastAPI Server
    participant DB as База данных

    User->>Browser: Открывает страницу явления
    Browser->>Server: GET /p/{slug}
    Server->>DB: SELECT phenomenon WHERE slug={slug}
    DB-->>Server: Данные явления
    Server->>DB: SELECT events WHERE phenomenon_id=X
    DB-->>Server: История событий
    Server->>Server: Расчет прогноза
    Server-->>Browser: HTML страница явления
    Browser-->>User: Отображение информации

    User->>Browser: Вводит email и нажимает "Подписаться"
    Browser->>Server: POST /subscribe
    Note over Server: Валидация email
    Server->>DB: INSERT INTO subscriptions
    DB-->>Server: OK
    Server-->>Browser: Redirect на страницу явления
    Browser-->>User: Сообщение об успешной подписке
```

### 3.3. Сценарий: Администрирование - создание события

```mermaid
sequenceDiagram
    actor Admin as Администратор
    participant Browser as Браузер
    participant Server as FastAPI Server
    participant Security as OWASP Protection
    participant DB as База данных
    participant Logger as Security Logger

    Admin->>Browser: Открывает /admin/login
    Browser->>Server: GET /admin/login
    Server-->>Browser: Форма входа
    Admin->>Browser: Вводит пароль
    Browser->>Server: POST /admin/login
    Server->>Security: check_login_attempts(ip)
    Security-->>Server: OK (не заблокирован)
    Server->>Server: Проверка пароля
    Server->>Logger: log_login_attempt(ip, success=True)
    Server->>Server: Создание сессии
    Server-->>Browser: Redirect /admin
    Browser-->>Admin: Админ-панель

    Admin->>Browser: Переход в "События" → "Создать"
    Browser->>Server: GET /admin/events
    Server->>Security: check_user_permission(session)
    Security-->>Server: Authorized
    Server->>DB: SELECT phenomena, places
    DB-->>Server: Списки для выбора
    Server-->>Browser: Форма создания события
    Browser-->>Admin: Отображение формы

    Admin->>Browser: Заполняет форму и отправляет
    Browser->>Server: POST /admin/events/new
    Server->>Security: verify_csrf_token()
    Security-->>Server: Valid
    Server->>Security: validate_business_logic(dates, intensity)
    Security-->>Server: Valid
    Server->>Security: sanitize_html(notes)
    Security-->>Server: Cleaned data
    Server->>DB: INSERT INTO events
    DB-->>Server: OK
    Server->>Logger: log_admin_action(ip, "create_event")
    Server-->>Browser: Redirect /admin/events
    Browser-->>Admin: Список событий с новым
```

### 3.4. Сценарий: Telegram бот - подписка и уведомления

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant TG as Telegram
    participant Bot as Telegram Bot
    participant RateLimit as Rate Limiter
    participant DB as База данных
    participant Scheduler as Notification Worker

    User->>TG: /start
    TG->>Bot: Команда /start
    Bot-->>TG: Приветственное сообщение
    TG-->>User: Отображение меню

    User->>TG: /follow lavanda-turgenevka
    TG->>Bot: Команда /follow
    Bot->>RateLimit: check_rate_limit(chat_id)
    RateLimit-->>Bot: OK
    Bot->>DB: SELECT phenomenon WHERE slug='lavanda-turgenevka'
    DB-->>Bot: Данные явления
    Bot->>DB: SELECT telegram_watch WHERE chat_id=X AND phenomenon_id=Y
    DB-->>Bot: NULL (нет подписки)
    Bot->>DB: INSERT INTO telegram_watches
    DB-->>Bot: OK
    Bot->>DB: SELECT event WHERE phenomenon_id=Y AND end_date >= today
    DB-->>Bot: Актуальное событие
    Bot-->>TG: Сообщение об успешной подписке + статус
    TG-->>User: Подтверждение

    Note over Scheduler: Ежедневная проверка (cron)
    Scheduler->>DB: SELECT events WHERE end_date >= today
    DB-->>Scheduler: Список событий
    loop Для каждого события
        Scheduler->>Scheduler: Проверка изменения статуса
        alt Статус изменился
            Scheduler->>DB: SELECT telegram_watches WHERE phenomenon_id=X
            DB-->>Scheduler: Список подписчиков
            loop Для каждого подписчика
                Scheduler->>Bot: send_notification(chat_id, event)
                Bot->>TG: Отправка уведомления
                TG->>User: Получение уведомления
            end
        end
    end
```

### 3.5. Сценарий: Просмотр карты с событиями

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant Browser as Браузер
    participant Server as FastAPI Server
    participant DB as База данных
    participant Leaflet as Leaflet.js
    participant Weather as OpenWeather API

    User->>Browser: Открывает /map
    Browser->>Server: GET /map
    Server-->>Browser: HTML страница с картой
    Browser->>Leaflet: Инициализация карты
    Leaflet-->>Browser: Карта готова

    Browser->>Server: GET /api/events/map
    Server->>DB: SELECT events WHERE end_date >= today - 45 days
    DB-->>Server: События с координатами
    Server-->>Browser: JSON с событиями
    Browser->>Leaflet: Добавление маркеров
    Leaflet-->>Browser: Маркеры на карте
    Browser-->>User: Отображение карты с событиями

    User->>Browser: Клик на маркер
    Browser->>Browser: Показ popup с информацией
    Browser->>Weather: GET /api/weather/hint?lat=X&lon=Y
    Weather-->>Browser: Данные о погоде
    Browser->>Browser: Обновление popup с погодой
    Browser-->>User: Полная информация о событии
```

## 4. Диаграммы активностей (Activity Diagrams)

### 4.1. Активность: Просмотр ленты событий

```mermaid
flowchart TD
    Start([Пользователь открывает сайт]) --> LoadPage[Загрузка главной страницы]
    LoadPage --> GetEvents[Получение событий из БД]
    GetEvents --> CheckFilters{Фильтры<br/>применены?}
    
    CheckFilters -->|Нет| ShowAll[Показать все события<br/>на 7 дней]
    CheckFilters -->|Да| ApplyFilters[Применить фильтры<br/>регион, тип, месяц]
    
    ApplyFilters --> FilterEvents[Фильтрация событий]
    FilterEvents --> ShowFiltered[Показать отфильтрованные события]
    
    ShowAll --> RenderCards[Отрисовка карточек событий]
    ShowFiltered --> RenderCards
    
    RenderCards --> DisplayPage[Отображение страницы]
    DisplayPage --> UserAction{Действие<br/>пользователя}
    
    UserAction -->|Изменить фильтр| ApplyFilters
    UserAction -->|Клик на событие| OpenDetail[Открыть страницу явления]
    UserAction -->|Переключить режим| ToggleExtended{Расширенный<br/>режим?}
    UserAction -->|Открыть карту| OpenMap[Перейти на карту]
    
    ToggleExtended -->|Включить| ShowExtended[Показать события<br/>на 4 месяца]
    ToggleExtended -->|Выключить| ShowAll
    
    ShowExtended --> RenderCards
    OpenDetail --> End1([Страница явления])
    OpenMap --> End2([Страница карты])
```

### 4.2. Активность: Подписка на явление

```mermaid
flowchart TD
    Start([Пользователь на странице явления]) --> ViewInfo[Просмотр информации о явлении]
    ViewInfo --> Decision{Хочет<br/>подписаться?}
    
    Decision -->|Нет| End1([Продолжает просмотр])
    Decision -->|Да| EnterEmail[Вводит email в форму]
    
    EnterEmail --> ClickSubscribe[Нажимает "Подписаться"]
    ClickSubscribe --> ValidateEmail{Email<br/>корректный?}
    
    ValidateEmail -->|Нет| ShowError[Показать ошибку]
    ShowError --> EnterEmail
    
    ValidateEmail -->|Да| CheckExisting{Подписка<br/>существует?}
    
    CheckExisting -->|Да| ShowWarning[Показать: уже подписаны]
    ShowWarning --> End2([Остаться на странице])
    
    CheckExisting -->|Нет| SaveSubscription[Сохранить подписку в БД]
    SaveSubscription --> ShowSuccess[Показать успешное сообщение]
    ShowSuccess --> End3([Подписка активна])
```

### 4.3. Активность: Администрирование - создание события

```mermaid
flowchart TD
    Start([Администратор входит в систему]) --> Login[Страница входа]
    Login --> EnterPassword[Ввод пароля]
    EnterPassword --> CheckAttempts{Превышен<br/>лимит попыток?}
    
    CheckAttempts -->|Да| BlockIP[Блокировка на 5 минут]
    BlockIP --> ShowBlocked[Показать сообщение о блокировке]
    ShowBlocked --> End1([Ожидание разблокировки])
    
    CheckAttempts -->|Нет| ValidatePassword{Пароль<br/>верный?}
    
    ValidatePassword -->|Нет| LogFailed[Логирование неудачной попытки]
    LogFailed --> IncAttempts[Увеличить счетчик попыток]
    IncAttempts --> ShowError[Показать ошибку]
    ShowError --> EnterPassword
    
    ValidatePassword -->|Да| CreateSession[Создать сессию]
    CreateSession --> LogSuccess[Логирование успешного входа]
    LogSuccess --> Dashboard[Открыть админ-панель]
    
    Dashboard --> SelectAction{Выбор<br/>действия}
    
    SelectAction -->|События| EventsList[Список событий]
    SelectAction -->|Явления| PhenomenaList[Список явлений]
    SelectAction -->|Места| PlacesList[Список мест]
    
    EventsList --> CreateEvent{Создать<br/>событие?}
    CreateEvent -->|Нет| End2([Просмотр списка])
    CreateEvent -->|Да| EventForm[Форма создания события]
    
    EventForm --> FillForm[Заполнение формы]
    FillForm --> SubmitForm[Отправка формы]
    
    SubmitForm --> ValidateCSRF{CSRF токен<br/>валиден?}
    ValidateCSRF -->|Нет| ShowCSRFError[Ошибка безопасности]
    ShowCSRFError --> End3([Отклонено])
    
    ValidateCSRF -->|Да| ValidateDates{Даты<br/>корректны?}
    ValidateDates -->|Нет| ShowDateError[Ошибка: start <= peak <= end]
    ShowDateError --> FillForm
    
    ValidateDates -->|Да| SanitizeData[Очистка данных от XSS]
    SanitizeData --> SaveEvent[Сохранение в БД]
    SaveEvent --> LogAction[Логирование действия]
    LogAction --> ShowSuccess[Показать успех]
    ShowSuccess --> EventsList
```

### 4.4. Активность: Telegram бот - подписка

```mermaid
flowchart TD
    Start([Пользователь открывает бота]) --> SendStart[Отправка /start]
    SendStart --> ShowWelcome[Показ приветствия и меню]
    ShowWelcome --> UserChoice{Выбор<br/>действия}
    
    UserChoice -->|/help| ShowHelp[Показать справку]
    UserChoice -->|/search| SearchFlow[Поиск явлений]
    UserChoice -->|/follow| FollowFlow[Подписка на явление]
    UserChoice -->|/mine| ShowSubscriptions[Показать подписки]
    
    ShowHelp --> UserChoice
    ShowSubscriptions --> UserChoice
    
    SearchFlow --> EnterQuery[Ввод поискового запроса]
    EnterQuery --> CheckRateLimit{Rate limit<br/>OK?}
    CheckRateLimit -->|Нет| ShowWait[Подождите немного]
    ShowWait --> UserChoice
    
    CheckRateLimit -->|Да| SanitizeQuery[Очистка от SQL injection]
    SanitizeQuery --> SearchDB[Поиск в БД]
    SearchDB --> HasResults{Найдены<br/>результаты?}
    
    HasResults -->|Нет| ShowNoResults[Ничего не найдено]
    ShowNoResults --> UserChoice
    
    HasResults -->|Да| ShowResults[Показать список явлений]
    ShowResults --> UserChoice
    
    FollowFlow --> EnterSlug[Ввод slug явления]
    EnterSlug --> FindPhenomenon{Явление<br/>существует?}
    
    FindPhenomenon -->|Нет| ShowSimilar[Показать похожие]
    ShowSimilar --> UserChoice
    
    FindPhenomenon -->|Да| CheckExisting{Уже<br/>подписан?}
    
    CheckExisting -->|Да| ShowAlready[Уже подписаны]
    ShowAlready --> UserChoice
    
    CheckExisting -->|Нет| CreateWatch[Создать подписку в БД]
    CreateWatch --> GetCurrentEvent[Получить актуальное событие]
    GetCurrentEvent --> CheckStatus{Статус<br/>события}
    
    CheckStatus -->|active| ShowActive[Сообщение: идёт сейчас!]
    CheckStatus -->|soon| ShowSoon[Сообщение: скоро начнётся]
    CheckStatus -->|future| ShowFuture[Сообщение: запланировано]
    
    ShowActive --> ConfirmSubscription[Подтверждение подписки]
    ShowSoon --> ConfirmSubscription
    ShowFuture --> ConfirmSubscription
    
    ConfirmSubscription --> End([Подписка активна])
```

### 4.5. Активность: Система уведомлений

```mermaid
flowchart TD
    Start([Запуск по расписанию<br/>каждый день в 8:00]) --> GetEvents[Получить все события из БД]
    GetEvents --> FilterActive[Фильтр: end_date >= today]
    FilterActive --> LoopEvents{Для каждого<br/>события}
    
    LoopEvents -->|Следующее| CheckStatus[Проверить текущий статус]
    LoopEvents -->|Конец| End([Завершение проверки])
    
    CheckStatus --> GetOldStatus[Получить предыдущий статус]
    GetOldStatus --> CompareStatus{Статус<br/>изменился?}
    
    CompareStatus -->|Нет| CheckPeak{Пик через<br/>1-3 дня?}
    CompareStatus -->|Да| SaveNewStatus[Сохранить новый статус]
    
    SaveNewStatus --> GetSubscribers[Получить подписчиков]
    GetSubscribers --> HasSubscribers{Есть<br/>подписчики?}
    
    HasSubscribers -->|Нет| LoopEvents
    HasSubscribers -->|Да| FormatMessage[Форматировать сообщение]
    
    FormatMessage --> LoopSubscribers{Для каждого<br/>подписчика}
    
    LoopSubscribers -->|Следующий| SendNotification[Отправить уведомление]
    SendNotification --> Wait[Пауза 0.1 сек]
    Wait --> LoopSubscribers
    LoopSubscribers -->|Конец| CheckPeak
    
    CheckPeak -->|Нет| LoopEvents
    CheckPeak -->|Да| SendReminder[Отправить напоминание о пике]
    SendReminder --> LoopEvents
```

### 4.6. Активность: Просмотр карты

```mermaid
flowchart TD
    Start([Пользователь открывает карту]) --> LoadMapPage[Загрузка страницы /map]
    LoadMapPage --> InitLeaflet[Инициализация Leaflet.js]
    InitLeaflet --> SetCenter[Центрирование на Крыму]
    SetCenter --> FetchEvents[Запрос событий через API]
    
    FetchEvents --> GetMapEvents[GET /api/events/map]
    GetMapEvents --> FilterEvents[Фильтр: события за последние 45 дней]
    FilterEvents --> ReturnJSON[Возврат JSON с событиями]
    
    ReturnJSON --> LoopEvents{Для каждого<br/>события}
    
    LoopEvents -->|Следующее| GetCoords[Получить координаты места]
    LoopEvents -->|Конец| DisplayMap[Отображение карты]
    
    GetCoords --> DetermineStatus[Определить статус события]
    DetermineStatus --> ChooseColor{Выбор цвета<br/>маркера}
    
    ChooseColor -->|active| RedMarker[Красный маркер]
    ChooseColor -->|soon| YellowMarker[Желтый маркер]
    ChooseColor -->|future| WhiteMarker[Белый маркер]
    ChooseColor -->|ended| GreenMarker[Зеленый маркер]
    
    RedMarker --> CreateMarker[Создать маркер на карте]
    YellowMarker --> CreateMarker
    WhiteMarker --> CreateMarker
    GreenMarker --> CreateMarker
    
    CreateMarker --> AddPopup[Добавить popup с информацией]
    AddPopup --> LoopEvents
    
    DisplayMap --> UserInteraction{Действие<br/>пользователя}
    
    UserInteraction -->|Клик на маркер| ShowPopup[Показать popup]
    UserInteraction -->|Перемещение карты| UpdateView[Обновить вид]
    UserInteraction -->|Клик на явление| FetchWeather[Запрос погоды]
    
    ShowPopup --> DisplayInfo[Отображение информации о событии]
    DisplayInfo --> UserInteraction
    
    UpdateView --> UserInteraction
    
    FetchWeather --> GetWeatherAPI[GET /api/weather/hint]
    GetWeatherAPI --> ShowWeather[Показать погоду в popup]
    ShowWeather --> UserInteraction
    
    UserInteraction -->|Закрыть| End([Завершение])
```

## 5. Диаграмма компонентов (Component Diagram)

```mermaid
graph TB
    subgraph "Frontend"
        HTML[HTML Templates<br/>Jinja2]
        CSS[CSS Styles<br/>style.css]
        JS[JavaScript<br/>map.js, theme.js, petals.js]
        Leaflet[Leaflet.js<br/>Карты]
    end

    subgraph "Backend - FastAPI"
        Main[main.py<br/>Приложение]
        
        subgraph "Routers"
            Pages[pages.py<br/>Страницы]
            API[api.py<br/>REST API]
            Admin[admin.py<br/>Админка]
        end
        
        subgraph "Services"
            Weather[weather.py<br/>Погода]
            Forecast[forecast.py<br/>Прогнозы]
            IconMap[icon_map.py<br/>Иконки]
        end
        
        subgraph "Utils"
            Security[security.py<br/>Валидация]
            OWASP[owasp_protection.py<br/>Защита]
            Logger[logger.py<br/>Логирование]
            Dates[dates.py<br/>Даты]
        end
        
        subgraph "Middleware"
            RateLimit[RateLimitMiddleware<br/>Ограничение запросов]
            SecHeaders[SecurityHeadersMiddleware<br/>Заголовки безопасности]
            Session[SessionMiddleware<br/>Сессии]
        end
    end

    subgraph "Telegram Bot"
        Bot[bot.py<br/>Telegram Bot]
        NotifWorker[notification_worker.py<br/>Уведомления]
    end

    subgraph "Database"
        DB[(PostgreSQL<br/>База данных)]
        Models[models.py<br/>SQLAlchemy Models]
    end

    subgraph "External APIs"
        OpenWeather[OpenWeather API<br/>Погода]
        TelegramAPI[Telegram API<br/>Сообщения]
    end

    HTML --> Pages
    CSS --> HTML
    JS --> HTML
    Leaflet --> JS
    
    Pages --> Main
    API --> Main
    Admin --> Main
    
    Main --> RateLimit
    Main --> SecHeaders
    Main --> Session
    
    Pages --> Services
    API --> Services
    Admin --> Utils
    
    Services --> Weather
    Services --> Forecast
    Services --> IconMap
    
    Utils --> Security
    Utils --> OWASP
    Utils --> Logger
    Utils --> Dates
    
    Pages --> Models
    API --> Models
    Admin --> Models
    Bot --> Models
    
    Models --> DB
    
    Weather --> OpenWeather
    Bot --> TelegramAPI
    NotifWorker --> Bot
    NotifWorker --> DB
    
    API --> OpenWeather
```

## 6. Диаграмма развертывания (Deployment Diagram)

```mermaid
graph TB
    subgraph "Docker Environment"
        subgraph "Container: tsvetashki_backend"
            Backend[FastAPI Application<br/>Python 3.12<br/>Uvicorn Server<br/>Port: 8000]
        end
        
        subgraph "Container: tsvetashki_db"
            DB[(PostgreSQL 15<br/>Port: 5432)]
        end
        
        subgraph "Container: tsvetashki_pgadmin"
            PgAdmin[pgAdmin 4<br/>Port: 5050]
        end
        
        subgraph "Container: tsvetashki_bot"
            TgBot[Telegram Bot<br/>Python 3.12<br/>aiogram]
        end
        
        subgraph "Container: tsvetashki_notifier"
            Notifier[Notification Worker<br/>Cron: daily 8:00]
        end
    end
    
    subgraph "External Services"
        OpenWeather[OpenWeather API<br/>api.openweathermap.org]
        TelegramAPI[Telegram Bot API<br/>api.telegram.org]
    end
    
    subgraph "Client Devices"
        Browser[Web Browser<br/>Desktop/Mobile]
        TgClient[Telegram Client<br/>Mobile/Desktop]
    end
    
    Browser -->|HTTP/HTTPS<br/>Port 8000| Backend
    Backend -->|SQL| DB
    Backend -->|HTTPS| OpenWeather
    
    TgClient -->|HTTPS| TelegramAPI
    TelegramAPI -->|Webhook/Polling| TgBot
    TgBot -->|SQL| DB
    
    Notifier -->|SQL| DB
    Notifier -->|Send Messages| TgBot
    
    PgAdmin -->|SQL| DB
    
    Backend -.->|Static Files| Browser
    Backend -.->|JSON API| Browser
```

---

## Легенда

### Типы явлений (kind)
- 🌺 **flowering** - Цветение
- 🌅 **visual** - Визуальное явление
- 🍒 **harvest** - Урожай
- 🐬 **animals** - Животные
- 🎪 **activity** - Событие/активность

### Статусы событий
- 🔴 **active** - Идёт прямо сейчас
- 🟡 **soon** - Начинается в ближайшие 7 дней
- ⚪ **future** - Запланировано на будущее
- ✅ **ended** - Завершено

### Роли пользователей
- **Пользователь** - Просмотр событий, подписка через email
- **Администратор** - Управление событиями, явлениями, местами
- **Telegram пользователь** - Подписка и уведомления через бота
- **Система уведомлений** - Автоматическая отправка уведомлений

---

*Документация создана для проекта "Цветашки Крым" - система отслеживания сезонных явлений Крыма*
