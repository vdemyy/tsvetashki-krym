# Подключение к PostgreSQL через pgAdmin

## 🎯 Что это?

**pgAdmin** — это удобный веб-интерфейс для управления PostgreSQL. Вы можете:
- Просматривать таблицы и данные
- Выполнять SQL запросы
- Делать резервные копии
- Импортировать/экспортировать данные

---

## 🚀 Быстрый старт

### 1. Запустить pgAdmin

```bash
docker compose up -d pgadmin
```

### 2. Открыть в браузере

**http://localhost:5050**

### 3. Войти

- **Email**: `admin@admin.com`
- **Пароль**: `admin`

### 4. Добавить сервер PostgreSQL

#### Шаг 1: Создать новый сервер
1. В левом меню нажмите правой кнопкой на **Servers**
2. Выберите **Register** → **Server...**

#### Шаг 2: Вкладка "General"
- **Name**: `Tsvetashki Krym` (любое название)

#### Шаг 3: Вкладка "Connection"
Введите следующие данные:

```
Host name/address:  db
Port:               5432
Maintenance database: tsvetashki
Username:           tsvetashki
Password:           tsvetashki_pass_2026
```

✅ Поставьте галочку **Save password**

#### Шаг 4: Сохранить
Нажмите **Save**

---

## 📊 Структура базы данных

После подключения вы увидите:

```
Servers
└── Tsvetashki Krym
    └── Databases
        └── tsvetashki
            └── Schemas
                └── public
                    └── Tables
                        ├── events (31 строка)
                        ├── phenomena (29 строк)
                        ├── places (28 строк)
                        ├── subscriptions
                        └── telegram_watches
```

---

## 🔍 Работа с данными

### Просмотр данных таблицы

1. Раскройте **Tables**
2. Нажмите правой кнопкой на таблицу (например, **phenomena**)
3. Выберите **View/Edit Data** → **All Rows**

### Выполнение SQL запросов

1. Нажмите правой кнопкой на базу **tsvetashki**
2. Выберите **Query Tool**
3. Введите SQL запрос, например:

```sql
-- Посмотреть все явления
SELECT * FROM phenomena;

-- Посмотреть события с местами
SELECT 
    e.id,
    p.name as phenomenon,
    pl.name as place,
    e.start_date,
    e.peak_date,
    e.end_date,
    e.intensity
FROM events e
JOIN phenomena p ON e.phenomenon_id = p.id
JOIN places pl ON e.place_id = pl.id
ORDER BY e.start_date DESC;

-- Статистика по явлениям
SELECT 
    p.name,
    COUNT(e.id) as events_count
FROM phenomena p
LEFT JOIN events e ON p.id = e.phenomenon_id
GROUP BY p.id, p.name
ORDER BY events_count DESC;

-- Найти активные события
SELECT 
    p.name as phenomenon,
    pl.name as place,
    e.start_date,
    e.end_date
FROM events e
JOIN phenomena p ON e.phenomenon_id = p.id
JOIN places pl ON e.place_id = pl.id
WHERE CURRENT_DATE BETWEEN e.start_date AND e.end_date;
```

4. Нажмите **F5** или кнопку **Execute** (▶️)

---

## 💾 Резервное копирование

### Создать бэкап через pgAdmin

1. Правой кнопкой на базу **tsvetashki**
2. **Backup...**
3. Выберите:
   - **Format**: Custom (рекомендуется) или Plain
   - **Filename**: укажите путь для сохранения
4. Нажмите **Backup**

### Создать бэкап через командную строку

```bash
# Создать бэкап
docker compose exec db pg_dump -U tsvetashki tsvetashki > backup_20260521.sql

# Или с датой
docker compose exec db pg_dump -U tsvetashki tsvetashki > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановить из бэкапа

#### Через pgAdmin:
1. Правой кнопкой на базу **tsvetashki**
2. **Restore...**
3. Выберите файл бэкапа
4. Нажмите **Restore**

#### Через командную строку:
```bash
docker compose exec -T db psql -U tsvetashki tsvetashki < backup_20260521.sql
```

---

## 📤 Экспорт/Импорт данных

### Экспорт таблицы в CSV

1. Откройте таблицу (View/Edit Data → All Rows)
2. Нажмите кнопку **Download as CSV** (иконка стрелки вниз)
3. Сохраните файл

### Импорт данных из CSV

1. Правой кнопкой на таблицу
2. **Import/Export Data...**
3. Выберите:
   - **Import/Export**: Import
   - **Filename**: выберите CSV файл
   - **Format**: csv
   - **Header**: Yes (если первая строка — заголовки)
4. Нажмите **OK**

---

## 🛠️ Полезные функции

### Создать новую таблицу

1. Правой кнопкой на **Tables**
2. **Create** → **Table...**
3. Заполните поля и добавьте колонки
4. Нажмите **Save**

### Изменить структуру таблицы

1. Правой кнопкой на таблицу
2. **Properties...**
3. Перейдите на вкладку **Columns**
4. Добавьте/измените колонки
5. Нажмите **Save**

### Посмотреть SQL код таблицы

1. Правой кнопкой на таблицу
2. **Scripts** → **CREATE Script**

---

## 🔧 Управление pgAdmin

### Остановить pgAdmin

```bash
docker compose stop pgadmin
```

### Запустить pgAdmin

```bash
docker compose start pgadmin
```

### Посмотреть логи

```bash
docker compose logs pgadmin
```

### Удалить pgAdmin (данные сохранятся)

```bash
docker compose down pgadmin
```

### Полностью удалить (включая данные)

```bash
docker compose down pgadmin
docker volume rm tsvetashki-krym_pgadmin_data
```

---

## ❓ Устранение проблем

### Не могу подключиться к серверу

**Проблема**: "could not connect to server"

**Решение**:
1. Проверьте, что PostgreSQL запущен:
   ```bash
   docker compose ps db
   ```

2. Убедитесь, что используете правильный host: **`db`** (не `localhost`!)

3. Проверьте, что контейнеры в одной сети:
   ```bash
   docker compose ps
   ```

### Забыл пароль от pgAdmin

**Решение**: Пересоздайте контейнер:
```bash
docker compose down pgadmin
docker volume rm tsvetashki-krym_pgadmin_data
docker compose up -d pgadmin
```

Затем войдите с:
- Email: `admin@admin.com`
- Пароль: `admin`

### pgAdmin не открывается

**Решение**:
1. Проверьте статус:
   ```bash
   docker compose ps pgadmin
   ```

2. Посмотрите логи:
   ```bash
   docker compose logs pgadmin
   ```

3. Перезапустите:
   ```bash
   docker compose restart pgadmin
   ```

### Порт 5050 занят

**Решение**: Измените порт в `docker-compose.yml`:
```yaml
ports:
  - "5051:80"  # вместо 5050:80
```

Затем перезапустите:
```bash
docker compose up -d pgadmin
```

---

## 🆚 Альтернатива: psql в терминале

Если не хотите использовать pgAdmin, можно работать через командную строку:

```bash
# Подключиться к PostgreSQL
docker compose exec db psql -U tsvetashki -d tsvetashki

# Посмотреть таблицы
\dt

# Посмотреть структуру таблицы
\d phenomena

# Посмотреть данные
SELECT * FROM phenomena;

# Выйти
\q
```

### Полезные команды psql

```bash
\l              # Список баз данных
\dt             # Список таблиц
\d table_name   # Структура таблицы
\du             # Список пользователей
\q              # Выход
\?              # Справка по командам
```

---

## 📚 Дополнительные ресурсы

- [Официальная документация pgAdmin](https://www.pgadmin.org/docs/)
- [PostgreSQL документация](https://www.postgresql.org/docs/)
- [SQL туториал](https://www.postgresql.org/docs/current/tutorial.html)

---

**Готово!** Теперь вы можете управлять базой данных через удобный веб-интерфейс pgAdmin 🎉
