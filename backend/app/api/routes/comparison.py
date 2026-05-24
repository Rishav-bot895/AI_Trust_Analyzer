"""Comparison route implementation for synchronous multi-model analysis."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.workflow import run_analysis
from app.api.dependencies import get_request_owner
from app.db.repository import RequestOwner
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisStatus,
    ComparisonRequest,
    ComparisonResponse,
)


comparison_router = APIRouter(tags=["comparison"])


@comparison_router.post("/compare", response_model=ComparisonResponse)
async def compare_models(
    payload: ComparisonRequest,
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
) -> ComparisonResponse:
    """Run comparisons across requested models concurrently and return all results."""
    _ = owner

    async def _run_for_model(model_name: str) -> AnalysisResponse:
        analysis_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        try:
            state = await run_analysis(
                analysis_id=analysis_id,
                prompt=payload.prompt,
                response=payload.response,
                model_name=model_name,
            )
        except Exception as exc:
            return AnalysisResponse(
                id=analysis_id,
                status=AnalysisStatus.FAILED,
                trust_score=None,
                hallucination_risk=None,
                claims=[],
                evidence=[],
                critique=None,
                verdict=None,
                created_at=created_at,
                completed_at=datetime.now(timezone.utc),
                error=str(exc),
            )

        failed = bool(state.get("error"))
        return AnalysisResponse(
            id=analysis_id,
            status=AnalysisStatus.FAILED if failed else AnalysisStatus.COMPLETED,
            trust_score=state.get("trust_score"),
            hallucination_risk=state.get("hallucination_risk"),
            claims=state.get("claims") or [],
            evidence=state.get("evidence") or [],
            critique=state.get("critique"),
            verdict=state.get("verdict"),
            created_at=created_at,
            completed_at=datetime.now(timezone.utc),
            error=state.get("error"),
        )

    analyses = await asyncio.gather(*[_run_for_model(model) for model in payload.models])
    return ComparisonResponse(analyses=analyses)