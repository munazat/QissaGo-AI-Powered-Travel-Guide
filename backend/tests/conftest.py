"""Test setup: a separate test database, seeded from the CSV files, no internet needed.

Uses TEST_DATABASE_URL (default: the local qissago_test database).
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://qissago:qissago@localhost:5432/qissago_test"
)
os.environ["LLM_PROVIDER"] = "none"
os.environ["LIVE_WEATHER"] = "false"

import datetime as dt  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import deps  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.catalog import load_catalog  # noqa: E402
from app.services.llm import NoLLM  # noqa: E402
from scripts.seed_db import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    from app.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def catalog(database):
    with SessionLocal() as db:
        return load_catalog(db)


@pytest.fixture
def today() -> dt.date:
    return dt.date.today()


@pytest.fixture
def client():
    app.dependency_overrides[deps.llm] = lambda: NoLLM()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


_counter = {"n": 0}


@pytest.fixture
def auth(client) -> dict:
    """Registers a fresh user and returns the Authorization header."""
    _counter["n"] += 1
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": f"user{_counter['n']}@example.com", "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
