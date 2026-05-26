"""Фикстуры для тестов."""

import os
import sys

# Override DATABASE_URL for all tests before imports
os.environ["DATABASE_URL"] = "sqlite:///./data/test_temp.db"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base  # noqa: E402
import models  # noqa: E402
from telegram_bot.notifications import NotificationLog  # noqa: E402


@pytest.fixture
def db_session():
    """Создаёт in-memory SQLite сессию для тестов."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Создаёт TestClient для FastAPI с подменённой БД."""
    from database import get_db
    from main import app
    app.dependency_overrides[get_db] = lambda: db_session
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

