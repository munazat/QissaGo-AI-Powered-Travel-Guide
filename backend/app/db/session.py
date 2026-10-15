"""Database connection. `get_db` gives each API request its own session."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after the first release. create_all() does not add columns to existing tables.
ADDED_COLUMNS = [
    ("cities", "jeep_per_day", "INTEGER DEFAULT 0"),
    ("cities", "speed_kmh", "DOUBLE PRECISION DEFAULT 24"),
    ("cities", "road_factor", "DOUBLE PRECISION DEFAULT 1.35"),
    ("pois", "cost_foreign", "INTEGER DEFAULT 0"),
    ("pois", "access", "VARCHAR(20) DEFAULT ''"),
]


def create_tables(bind=None) -> None:
    from app.db import models  # noqa: F401  (registers the tables)

    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    with bind.begin() as conn:
        for table, column, kind in ADDED_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {kind}"))
