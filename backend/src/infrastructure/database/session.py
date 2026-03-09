from __future__ import annotations

from functools import lru_cache

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config import get_settings


@lru_cache
def create_session_factory() -> async_sessionmaker[AsyncSession]:
    """Session factory for the API server (connection pooling enabled)."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def create_worker_session_factory() -> async_sessionmaker[AsyncSession]:
    """Session factory for Celery workers (NullPool — no connection reuse).

    Each Celery task calls asyncio.run() which creates a new event loop.
    asyncpg connections are bound to their creating event loop, so reusing
    pooled connections across asyncio.run() calls causes InterfaceError.
    NullPool creates a fresh connection per session and closes it after use.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL, echo=False, poolclass=NullPool
    )
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
