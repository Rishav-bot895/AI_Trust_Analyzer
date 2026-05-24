"""Analysis routes for submission and history."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import run_analysis
from app.api.dependencies import get_request_owner
from app.db.repository import AnalysisRepository, RequestOwner
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.analysis import AnalysisListItem, AnalysisRequest, AnalysisResponse
from app.schemas.claim import Claim
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

        analysis.status = "RUNNING"
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
            analysis = await repository.get_analysis(analysis_id, owner)
            if analysis is None:
                return

            analysis.status = "FAILED"
            analysis.error = str(exc)
            analysis.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        analysis = await repository.get_analysis(analysis_id, owner)
        if analysis is None:
            return

        analysis.status = "FAILED" if state.get("error") else "COMPLETED"
        analysis.trust_score = state.get("trust_score")
        analysis.hallucination_risk = state.get("hallucination_risk")
        analysis.critique = state.get("critique")
        analysis.verdict = state.get("verdict")
        analysis.error = state.get("error")
        analysis.timeline = json.dumps(state.get("timeline") or [])
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()


@analysis_router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_route(
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Create a pending analysis and dispatch background execution."""
    repository = AnalysisRepository(db)
    analysis = await repository.create_analysis(owner, status="PENDING")
    analysis.prompt = payload.prompt
    analysis.response = payload.response
    analysis.model_name = payload.model_name
    analysis.include_comparison = payload.include_comparison
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
