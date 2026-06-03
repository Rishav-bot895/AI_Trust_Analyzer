"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _database_url_for_runtime() -> str:
    """Return validated runtime database URL for async SQLAlchemy engine."""
    if settings.ENVIRONMENT in {"development", "production"} and not settings.DATABASE_URL.startswith(
        "postgresql+asyncpg://"
    ):
        raise RuntimeError(
            "DATABASE_URL must use postgresql+asyncpg:// in development and production"
        )
    return settings.DATABASE_URL


engine = create_async_engine(_database_url_for_runtime(), future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and ensure it is closed."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()