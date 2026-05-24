"""Ownership-aware data access helpers for analysis persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Analysis, Claim


@dataclass(frozen=True)
class RequestOwner:
    """Requester identity context used to scope database operations."""

    is_guest: bool
    user_id: str | None = None
    guest_session_id: str | None = None

    def __post_init__(self) -> None:
        if self.is_guest:
            if not self.guest_session_id:
                raise ValueError("guest_session_id is required for guest requests")
            if self.user_id:
                raise ValueError("user_id is not allowed for guest requests")
            return

        if not self.user_id:
            raise ValueError("user_id is required for authenticated requests")
        if self.guest_session_id:
            raise ValueError("guest_session_id is not allowed for authenticated requests")


class AnalysisRepository:
    """Repository with strict ownership boundaries for analysis records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _owner_filter(owner: RequestOwner) -> tuple[object, ...]:
        if owner.is_guest:
            return (
                Analysis.is_guest.is_(True),
                Analysis.guest_session_id == owner.guest_session_id,
            )

        return (
            Analysis.is_guest.is_(False),
            Analysis.user_id == owner.user_id,
        )

    def _scoped_query(self, owner: RequestOwner) -> Select[tuple[Analysis]]:
        return select(Analysis).where(*self._owner_filter(owner))

    @staticmethod
    def apply_owner(analysis: Analysis, owner: RequestOwner) -> None:
        """Apply requester ownership markers to a newly-created analysis row."""
        analysis.is_guest = owner.is_guest
        analysis.user_id = owner.user_id
        analysis.guest_session_id = owner.guest_session_id

    async def create_analysis(self, owner: RequestOwner, *, status: str = "PENDING") -> Analysis:
        """Create an analysis row owned by the requester."""
        analysis = Analysis(status=status)
        self.apply_owner(analysis, owner)
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis

    async def get_analysis(self, analysis_id: str, owner: RequestOwner) -> Analysis | None:
        """Fetch a single analysis if and only if the requester owns it."""
        result = await self._session.execute(
            self._scoped_query(owner)
            .options(selectinload(Analysis.claims).selectinload(Claim.evidence))
            .where(Analysis.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def list_analyses(
        self,
        owner: RequestOwner,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Analysis]:
        """List only analyses visible to the requester."""
        query = (
            self._scoped_query(owner)
            .order_by(Analysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars())

    async def list_authenticated_history(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Analysis]:
        """List historical analyses for an authenticated user only."""
        query = (
            select(Analysis)
            .where(Analysis.is_guest.is_(False), Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars())

    async def update_status(
        self,
        analysis_id: str,
        owner: RequestOwner,
        *,
        status: str,
    ) -> bool:
        """Update status for a requester-owned analysis only."""
        result = await self._session.execute(
            update(Analysis)
            .where(Analysis.id == analysis_id, *self._owner_filter(owner))
            .values(status=status)
        )
        return result.rowcount > 0

    async def delete_guest_session_analyses(self, guest_session_id: str) -> int:
        """Delete all guest analyses for a session, returning deleted row count."""
        result = await self._session.execute(
            select(Analysis).where(
                Analysis.is_guest.is_(True),
                Analysis.guest_session_id == guest_session_id,
            )
        )
        analyses = list(result.scalars())
        for analysis in analyses:
            await self._session.delete(analysis)
        return len(analyses)

    async def delete_expired_guest_analyses(self, cutoff: datetime) -> int:
        """Delete guest analyses older than cutoff and return deleted row count."""
        result = await self._session.execute(
            select(Analysis).where(
                Analysis.is_guest.is_(True),
                Analysis.created_at < cutoff,
            )
        )
        analyses = list(result.scalars())
        for analysis in analyses:
            await self._session.delete(analysis)
        return len(analyses)
