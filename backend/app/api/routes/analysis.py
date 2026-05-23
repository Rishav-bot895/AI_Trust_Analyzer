"""Analysis route placeholders for API bootstrap phase."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_request_owner
from app.db.repository import AnalysisRepository, RequestOwner
from app.db.session import get_db
from app.schemas.analysis import AnalysisListItem


analysis_router = APIRouter(tags=["analysis"])


@analysis_router.post("/analyze")
async def analyze_placeholder(
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
) -> None:
    """Placeholder analyze endpoint until background workflow is implemented."""
    _ = owner
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Analyze endpoint not implemented yet.",
    )


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