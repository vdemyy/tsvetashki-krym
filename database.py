import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(override=False)

Path("data").mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tsvetashki.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_schema_patches() -> None:
    """Лёгкие миграции без Alembic (новые колонки в SQLite/Postgres)."""
    insp = inspect(engine)
    if not insp.has_table("phenomena"):
        return
    cols = {c["name"] for c in insp.get_columns("phenomena")}
    stmts: list[str] = []
    if "icon_lucide" not in cols:
        if engine.dialect.name == "sqlite":
            stmts.append("ALTER TABLE phenomena ADD COLUMN icon_lucide VARCHAR(64)")
        else:
            stmts.append("ALTER TABLE phenomena ADD COLUMN IF NOT EXISTS icon_lucide VARCHAR(64)")
    if stmts:
        with engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
