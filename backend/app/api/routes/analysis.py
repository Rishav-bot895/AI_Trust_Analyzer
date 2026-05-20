"""Analysis route placeholders for API bootstrap phase."""

from fastapi import APIRouter, HTTPException, status


analysis_router = APIRouter(tags=["analysis"])


@analysis_router.post("/analyze")
async def analyze_placeholder() -> None:
    """Placeholder analyze endpoint until background workflow is implemented."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Analyze endpoint not implemented yet.",
    )