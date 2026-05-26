import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

import models  # noqa: F401 — регистрация таблиц в metadata
from database import Base, apply_schema_patches, engine
from routers import admin, api, pages
from scripts.seed import ensure_seed
from utils.limiter import limiter

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("tsvetashki")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Цветашки Крым…")
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    ensure_seed()
    log.info("Ready.")
    yield


SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip()
if not SESSION_SECRET or SESSION_SECRET in ("change-me-in-production", "замените-на-длинную-случайную-строку"):
    log.warning("SESSION_SECRET not set or insecure! Generate one: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    SESSION_SECRET = os.urandom(32).hex()  # random per-run fallback for dev

app = FastAPI(title="Цветашки Крым", lifespan=lifespan)

# Rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Слишком много запросов. Попробуйте позже."},
    )


class CSRFMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and not scope["path"].startswith("/api/"):
            headers = dict(scope.get("headers", []))
            content_type = headers.get(b"content-type", b"").decode("latin1")
            
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                # Read request body
                body = b""
                more_body = True
                while more_body:
                    message = await receive()
                    body += message.get("body", b"")
                    more_body = message.get("more_body", False)

                # Parse CSRF token
                import urllib.parse
                form_data = urllib.parse.parse_qs(body.decode("utf-8", errors="ignore"))
                csrf_token = form_data.get("csrf_token", [None])[0]

                # Get expected token from session
                session = scope.get("session", {})
                expected_token = session.get("csrf_token")

                if not expected_token or csrf_token != expected_token:
                    log.warning(f"CSRF validation failed for {scope['path']}")
                    response_body = b"<html><body><h1>CSRF Validation Failed</h1><p>Please return to the previous page, refresh, and try again.</p></body></html>"
                    await send({
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"text/html; charset=utf-8")],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": response_body,
                    })
                    return

                # Recreate the receive channel
                async def new_receive():
                    return {
                        "type": "http.request",
                        "body": body,
                        "more_body": False
                    }
                await self.app(scope, new_receive, send)
                return

        await self.app(scope, receive, send)


app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="tsvetashki_session",
    same_site="lax",
)
app.add_middleware(SlowAPIMiddleware)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(api.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

