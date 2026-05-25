import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

import models  # noqa: F401 — регистрация таблиц в metadata
from database import Base, apply_schema_patches, engine
from routers import admin, api, pages
from scripts.seed import ensure_seed

load_dotenv()


# Простой Rate Limiter (защита от спама)
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=100, window_seconds=60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [timestamp1, timestamp2, ...]}
    
    async def dispatch(self, request: Request, call_next):
        # Получаем IP адрес клиента
        client_ip = request.client.host
        current_time = time.time()
        
        # Инициализируем список запросов для IP
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Удаляем старые запросы (старше окна)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.max_requests:
            return Response(
                content="Слишком много запросов. Попробуйте позже.",
                status_code=429
            )
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(current_time)
        
        # Обрабатываем запрос
        response = await call_next(request)
        return response


# Security Headers (защита от атак)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Защита от clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Защита от XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (базовая)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Проверяем безопасность конфигурации при старте
    from utils.owasp_protection import check_secure_config
    
    warnings = check_secure_config()
    if warnings:
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ БЕЗОПАСНОСТИ:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    ensure_seed()
    yield


app = FastAPI(title="Цветашки Крым", lifespan=lifespan)

# Добавляем middleware для безопасности
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me-in-production"),
    session_cookie="tsvetashki_session",
    same_site="lax",
    max_age=3600,  # Сессия живет 1 час
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(api.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
