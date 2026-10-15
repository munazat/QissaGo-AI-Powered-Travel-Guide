"""Shared helpers for API routes: database session, logged-in user, catalog, LLM."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import read_token
from app.db.models import User
from app.db.session import get_db
from app.services.catalog import Catalog, load_catalog
from app.services.llm import LLM, get_llm

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user_id = read_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in again")
    return user


def catalog(db: Session = Depends(get_db)) -> Catalog:
    return load_catalog(db)


def llm() -> LLM:
    return get_llm()
