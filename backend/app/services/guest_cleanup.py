"""Guest-session data deletion lifecycle helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repository import AnalysisRepository


async def end_guest_session(session: AsyncSession, guest_session_id: str) -> int:
    """Delete all analyses for an explicit guest session end signal."""
    repository = AnalysisRepository(session)
    deleted = await repository.delete_guest_session_analyses(guest_session_id)
    await session.commit()
    return deleted


async def cleanup_expired_guest_data(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    """Delete guest analyses older than configured TTL hours."""
    reference_time = now or datetime.now(timezone.utc)
    cutoff = reference_time - timedelta(hours=settings.GUEST_SESSION_TTL_HOURS)

    repository = AnalysisRepository(session)
    deleted = await repository.delete_expired_guest_analyses(cutoff)
    await session.commit()
    return deleted
