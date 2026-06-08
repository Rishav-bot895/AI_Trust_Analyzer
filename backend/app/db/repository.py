"""Ownership-aware data access helpers for analysis persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Analysis, Claim, Evidence
from app.schemas.agent_state import AgentState
from app.schemas.analysis import AnalysisRequest
from app.services.policy_guardrails import assert_persistable_analysis_state


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

    async def create_analysis(
        self,
        owner: RequestOwner,
        request: AnalysisRequest | None = None,
        *,
        status: str = "PENDING",
    ) -> Analysis:
        """Create an analysis row owned by the requester."""
        analysis = Analysis(status=status)
        self.apply_owner(analysis, owner)
        if request is not None:
            analysis.prompt = request.prompt
            analysis.response = request.response
            analysis.model_name = request.model_name
            analysis.include_comparison = request.include_comparison
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

    async def get_analysis_for_requester(
        self,
        analysis_id: UUID | str,
        owner: RequestOwner,
    ) -> Analysis | None:
        """Fetch a requester-scoped analysis by id."""
        return await self.get_analysis(str(analysis_id), owner)

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

    async def get_claims(
        self,
        analysis_id: str,
        owner: RequestOwner,
        *,
        status: str | None = None,
    ) -> list[Claim]:
        """Return requester-scoped claims for an analysis with optional status filter."""
        query = (
            select(Claim)
            .join(Analysis, Claim.analysis_id == Analysis.id)
            .where(Claim.analysis_id == analysis_id, *self._owner_filter(owner))
            .order_by(Claim.claim_index.asc())
        )
        if status is not None:
            query = query.where(Claim.status == status)

        result = await self._session.execute(query)
        return list(result.scalars())

    async def create_claims(self, analysis_id: str, claims: list[dict]) -> list[Claim]:
        """Persist claim rows for an analysis and return saved claim models."""
        saved_claims: list[Claim] = []
        for index, claim_data in enumerate(claims):
            text = str(claim_data.get("text", "")).strip()
            if not text:
                continue

            claim_kwargs = {
                "analysis_id": analysis_id,
                "text": text,
                "confidence": float(claim_data.get("confidence", 0.0)),
                "status": str(claim_data.get("status", "UNVERIFIABLE")),
                "claim_index": int(claim_data.get("claim_index", index)),
                "source_span": claim_data.get("source_span"),
            }
            if claim_data.get("id"):
                claim_kwargs["id"] = str(claim_data["id"])

            claim = Claim(**claim_kwargs)
            self._session.add(claim)
            saved_claims.append(claim)

        await self._session.flush()
        return saved_claims

    async def create_evidence(self, claims: list[Claim], evidence: list[dict]) -> list[Evidence]:
        """Persist evidence rows linked to saved claims and return saved evidence."""
        if not claims:
            return []

        claim_ids = {claim.id for claim in claims}
        saved_evidence: list[Evidence] = []

        for evidence_data in evidence:
            claim_id = str(evidence_data.get("claim_id", ""))
            if claim_id not in claim_ids:
                continue

            snippet = str(evidence_data.get("snippet", "")).strip()
            if not snippet:
                continue

            evidence_kwargs = {
                "claim_id": claim_id,
                "snippet": snippet,
                "source_url": evidence_data.get("source_url"),
                "source_title": evidence_data.get("source_title"),
                "relevance_score": float(evidence_data.get("relevance_score", 0.0)),
                "source_type": str(evidence_data.get("source_type", "WEB_SEARCH")),
                "polarity": evidence_data.get("polarity"),
            }
            if evidence_data.get("id"):
                evidence_kwargs["id"] = str(evidence_data["id"])

            row = Evidence(**evidence_kwargs)
            self._session.add(row)
            saved_evidence.append(row)

        await self._session.flush()
        return saved_evidence

    async def get_evidence(
        self,
        analysis_id: str,
        owner: RequestOwner,
        *,
        claim_id: str | None = None,
    ) -> list[Evidence]:
        """Return requester-scoped evidence for an analysis with optional claim filter."""
        query = (
            select(Evidence)
            .join(Claim, Evidence.claim_id == Claim.id)
            .join(Analysis, Claim.analysis_id == Analysis.id)
            .where(Claim.analysis_id == analysis_id, *self._owner_filter(owner))
            .order_by(Evidence.relevance_score.desc())
        )
        if claim_id is not None:
            query = query.where(Evidence.claim_id == claim_id)

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

    async def update_analysis_status(
        self,
        analysis_id: UUID | str,
        owner: RequestOwner,
        status: str,
    ) -> None:
        """Update requester-scoped analysis status."""
        await self.update_status(str(analysis_id), owner, status=status)

    async def update_analysis_result(
        self,
        analysis_id: UUID | str,
        owner: RequestOwner,
        state: AgentState,
    ) -> Analysis | None:
        """Persist final workflow state, including claims/evidence and timeline."""
        assert_persistable_analysis_state(state)
        analysis = await self.get_analysis_for_requester(analysis_id, owner)
        if analysis is None:
            return None

        has_error = bool(state.get("error"))
        analysis.status = "FAILED" if has_error else "COMPLETED"
        analysis.trust_score = state.get("trust_score")
        analysis.hallucination_risk = state.get("hallucination_risk")
        analysis.critique = state.get("critique")
        analysis.verdict = state.get("verdict")
        analysis.error = state.get("error")
        analysis.timeline = json.dumps(state.get("timeline") or [])
        analysis.completed_at = datetime.now(timezone.utc)

        for claim in list(analysis.claims):
            await self._session.delete(claim)
        await self._session.flush()

        claim_payload = state.get("verified_claims") or state.get("claims") or []
        saved_claims = await self.create_claims(analysis.id, claim_payload)
        await self.create_evidence(saved_claims, state.get("evidence") or [])

        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis

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

    async def delete_guest_session_data(self, guest_session_id: str) -> None:
        """Delete guest analysis data for a session id."""
        await self.delete_guest_session_analyses(guest_session_id)

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
