"""QissaGo API.

Run (from the backend folder, with the virtual environment active):
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Interactive API docs: http://localhost:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, chat, itineraries, meta
from app.core.config import BACKEND_DIR, get_settings
from app.db.session import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()  # creates any missing tables; data comes from scripts/seed_db.py
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(meta.router, prefix=API)
app.include_router(chat.router, prefix=API)
app.include_router(itineraries.router, prefix=API)
app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "llm": settings.llm_provider}
