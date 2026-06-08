"""Analysis routes for submission and history."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import run_analysis
from app.api.dependencies import get_request_owner
from app.api.middleware import limiter
from app.db.repository import AnalysisRepository, RequestOwner
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.analysis import AnalysisListItem, AnalysisRequest, AnalysisResponse
from app.schemas.agent_state import TimelineEvent
from app.schemas.claim import Claim, ClaimStatus
from app.schemas.evidence import Evidence


analysis_router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)


async def _run_analysis_in_background(
    *,
    analysis_id: str,
    owner: RequestOwner,
    prompt: str,
    response: str,
    model_name: str,
) -> None:
    """Execute the analysis workflow and persist terminal state fields."""
    async with AsyncSessionLocal() as db:
        repository = AnalysisRepository(db)
        analysis = await repository.get_analysis(analysis_id, owner)
        if analysis is None:
            return

        await repository.update_analysis_status(analysis_id, owner, "RUNNING")
        await db.commit()

        try:
            state = await run_analysis(
                analysis_id=analysis_id,
                prompt=prompt,
                response=response,
                model_name=model_name,
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Background analysis failed for %s", analysis_id)

            await repository.update_analysis_result(
                analysis_id,
                owner,
                {
                    "analysis_id": analysis_id,
                    "prompt": prompt,
                    "response": response,
                    "model_name": model_name,
                    "claims": [],
                    "evidence": [],
                    "verified_claims": [],
                    "critique": None,
                    "trust_score": None,
                    "hallucination_risk": "UNKNOWN",
                    "verdict": None,
                    "timeline": [],
                    "error": str(exc),
                },
            )
            await db.commit()
            return

        try:
            await repository.update_analysis_result(analysis_id, owner, state)
        except ValueError as exc:
            logger.warning(
                "Analysis state rejected before persistence for %s: %s",
                analysis_id,
                exc,
            )
            await repository.update_analysis_result(
                analysis_id,
                owner,
                {
                    "analysis_id": analysis_id,
                    "prompt": prompt,
                    "response": response,
                    "model_name": model_name,
                    "claims": [],
                    "evidence": [],
                    "verified_claims": [],
                    "critique": None,
                    "trust_score": None,
                    "hallucination_risk": "UNKNOWN",
                    "verdict": None,
                    "timeline": state.get("timeline") or [],
                    "error": str(exc),
                },
            )
        await db.commit()


@analysis_router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("30/minute")
async def analyze_route(
    request: Request,
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Create a pending analysis and dispatch background execution."""
    _ = request
    repository = AnalysisRepository(db)
    analysis = await repository.create_analysis(owner, request=payload, status="PENDING")
    await db.commit()

    background_tasks.add_task(
        _run_analysis_in_background,
        analysis_id=analysis.id,
        owner=owner,
        prompt=payload.prompt,
        response=payload.response,
        model_name=payload.model_name,
    )

    return {"id": analysis.id, "status": "PENDING"}


@analysis_router.get("/analyze/history", response_model=list[AnalysisListItem])
async def get_authenticated_history(
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[AnalysisListItem]:
    """Return analysis history for authenticated users only."""
    if owner.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="History is available for authenticated users only.",
        )

    repository = AnalysisRepository(db)
    records = await repository.list_authenticated_history(
        owner.user_id or "",
        limit=limit,
        offset=offset,
    )

    return [
        AnalysisListItem(
            id=item.id,
            status=item.status,
            trust_score=item.trust_score,
            hallucination_risk=item.hallucination_risk,
            created_at=item.created_at,
            completed_at=item.completed_at,
            error=item.error,
        )
        for item in records
    ]


@analysis_router.get("/analyze/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_by_id(
    analysis_id: str,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisResponse:
    """Return requester-scoped analysis status and available results."""
    repository = AnalysisRepository(db)
    analysis = await repository.get_analysis(analysis_id, owner)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    claims: list[Claim] = []
    evidence: list[Evidence] = []
    if analysis.status == "COMPLETED":
        for db_claim in analysis.claims:
            claims.append(
                Claim(
                    id=db_claim.id,
                    text=db_claim.text,
                    confidence=db_claim.confidence,
                    status=db_claim.status,
                    claim_index=db_claim.claim_index,
                    source_span=db_claim.source_span,
                )
            )
            for db_evidence in db_claim.evidence:
                evidence.append(
                    Evidence(
                        id=db_evidence.id,
                        claim_id=db_evidence.claim_id,
                        snippet=db_evidence.snippet,
                        source_url=db_evidence.source_url,
                        source_title=db_evidence.source_title,
                        relevance_score=db_evidence.relevance_score,
                        source_type=db_evidence.source_type,
                        polarity=db_evidence.polarity,
                        retrieved_at=db_evidence.retrieved_at,
                    )
                )

    return AnalysisResponse(
        id=analysis.id,
        status=analysis.status,
        trust_score=analysis.trust_score,
        hallucination_risk=analysis.hallucination_risk,
        claims=claims,
        evidence=evidence,
        critique=analysis.critique,
        verdict=analysis.verdict,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        error=analysis.error,
    )


@analysis_router.get("/analyze/{analysis_id}/claims", response_model=list[Claim])
async def get_analysis_claims(
    analysis_id: str,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Claim]:
    """Return requester-scoped claims, optionally filtered by claim status."""
    repository = AnalysisRepository(db)
    analysis = await repository.get_analysis(analysis_id, owner)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    claim_status: ClaimStatus | None = None
    if status_filter is not None:
        try:
            claim_status = ClaimStatus(status_filter)
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Invalid claim status: {status_filter}"},
            )

    claims = await repository.get_claims(
        analysis_id,
        owner,
        status=claim_status.value if claim_status else None,
    )
    return [
        Claim(
            id=db_claim.id,
            text=db_claim.text,
            confidence=db_claim.confidence,
            status=db_claim.status,
            claim_index=db_claim.claim_index,
            source_span=db_claim.source_span,
        )
        for db_claim in claims
    ]


@analysis_router.get("/analyze/{analysis_id}/evidence", response_model=list[Evidence])
async def get_analysis_evidence(
    analysis_id: str,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
    claim_id: UUID | None = Query(default=None),
) -> list[Evidence]:
    """Return requester-scoped evidence, optionally filtered by claim id."""
    repository = AnalysisRepository(db)
    analysis = await repository.get_analysis(analysis_id, owner)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    evidence_items = await repository.get_evidence(
        analysis_id,
        owner,
        claim_id=str(claim_id) if claim_id else None,
    )
    return [
        Evidence(
            id=db_evidence.id,
            claim_id=db_evidence.claim_id,
            snippet=db_evidence.snippet,
            source_url=db_evidence.source_url,
            source_title=db_evidence.source_title,
            relevance_score=db_evidence.relevance_score,
            source_type=db_evidence.source_type,
            polarity=db_evidence.polarity,
            retrieved_at=db_evidence.retrieved_at,
        )
        for db_evidence in evidence_items
    ]


@analysis_router.get("/analyze/{analysis_id}/timeline", response_model=list[TimelineEvent])
async def get_analysis_timeline(
    analysis_id: str,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineEvent]:
    """Return requester-scoped agent execution timeline in recorded order."""
    repository = AnalysisRepository(db)
    analysis = await repository.get_analysis(analysis_id, owner)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    if not analysis.timeline:
        return []

    try:
        timeline = json.loads(analysis.timeline)
    except json.JSONDecodeError:
        logger.warning("Invalid timeline JSON for analysis %s", analysis_id)
        return []

    if not isinstance(timeline, list):
        return []

    return [
        TimelineEvent(
            agent=str(event.get("agent", "")),
            started_at=str(event.get("started_at", "")),
            completed_at=str(event.get("completed_at", "")),
            input_summary=str(event.get("input_summary", "")),
            output_summary=str(event.get("output_summary", "")),
        )
        for event in timeline
        if isinstance(event, dict)
    ]
