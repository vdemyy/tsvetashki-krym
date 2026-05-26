"""Тесты для API-эндпоинтов, CSRF-защиты и rate-limiting."""

from datetime import date
import pytest
from models import Phenomenon, Place, Event


def test_api_events_pagination(client, db_session):
    # Создаём тестовые данные
    ph = Phenomenon(slug="test-ph", name="Test", kind="flowering")
    pl = Place(name="Test Place", latitude=44.5, longitude=34.2)
    db_session.add_all([ph, pl])
    db_session.flush()

    for i in range(5):
        ev = Event(
            phenomenon_id=ph.id,
            place_id=pl.id,
            start_date=date(2026, 6, 1 + i),
            peak_date=date(2026, 6, 15),
            end_date=date(2026, 6, 30),
            intensity=3,
        )
        db_session.add(ev)
    db_session.commit()

    # Запрашиваем с пагинацией limit=2, offset=1
    response = client.get("/api/events?limit=2&offset=1&feed=false")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1
    # Проверка схемы
    assert "today" in data
    assert data["items"][0]["intensity"] == 3


def test_api_subscribe_success(client, db_session):
    ph = Phenomenon(slug="sub-ph", name="Test Sub", kind="flowering")
    db_session.add(ph)
    db_session.commit()

    response = client.post(f"/api/subscribe?email=test@example.com&phenomenon_id={ph.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "message" in data


def test_csrf_protection_on_pages(client, db_session):
    # GET запрос инициализирует сессию с csrf_token
    response = client.get("/")
    assert response.status_code == 200
    
    # Пытаемся сделать POST без csrf_token — должно вернуть 403 Forbidden
    response_post = client.post("/subscribe", data={"email": "hacker@example.com", "phenomenon_id": 1})
    assert response_post.status_code == 403
    assert "CSRF Validation Failed" in response_post.text


def test_csrf_protection_with_valid_token(client, db_session):
    # Создаём тестовые данные, чтобы форма с csrf_token отрендерилась
    ph = Phenomenon(slug="csrf-ph", name="Test CSRF", kind="flowering")
    pl = Place(name="Test Place", latitude=44.5, longitude=34.2)
    db_session.add_all([ph, pl])
    db_session.flush()

    ev = Event(
        phenomenon_id=ph.id,
        place_id=pl.id,
        start_date=date.today(),
        peak_date=date.today(),
        end_date=date.today(),
        intensity=3,
    )
    db_session.add(ev)
    db_session.commit()

    # GET запрос инициализирует сессию с csrf_token
    response = client.get("/")
    assert response.status_code == 200
    
    # Извлекаем csrf_token из отрендеренной формы
    import re
    match = re.search(r'name="csrf_token" value="([a-f0-9]+)"', response.text)
    token = match.group(1) if match else None
    assert token is not None

    # Отправляем POST с правильным csrf_token
    response_post = client.post(
        "/subscribe",
        data={"email": "user@example.com", "phenomenon_id": ph.id, "csrf_token": token},
        follow_redirects=False
    )
    # Должен произойти редирект (303) к referer
    print("\n[DIAGNOSTIC] response_post status:", response_post.status_code)
    print("[DIAGNOSTIC] response_post text:", response_post.text)
    assert response_post.status_code == 303


def test_rate_limiting(client, db_session):
    from utils.limiter import limiter
    limiter.reset()

    ph = Phenomenon(slug="rate-ph", name="Test Rate", kind="flowering")
    db_session.add(ph)
    db_session.commit()

    # Делаем 5 запросов успешно
    for _ in range(5):
        response = client.post(f"/api/subscribe?email=rate@example.com&phenomenon_id={ph.id}")
        assert response.status_code == 200

    # 6-й запрос должен вызвать 429 Too Many Requests (наша ручка ограничена 5/minute)
    response = client.post(f"/api/subscribe?email=rate@example.com&phenomenon_id={ph.id}")
    assert response.status_code == 429
    assert "Слишком много запросов" in response.json()["detail"]
