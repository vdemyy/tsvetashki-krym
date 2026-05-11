import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import models  # noqa: F401 — регистрация таблиц в metadata
from database import Base, apply_schema_patches, engine
from routers import admin, api, pages
from seed import ensure_seed

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    ensure_seed()
    yield


app = FastAPI(title="Цветашки Крым", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-me-in-production"),
    session_cookie="tsvetashki_session",
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(api.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
