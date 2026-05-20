"""Comparison route placeholders for API bootstrap phase."""

from fastapi import APIRouter, HTTPException, status


comparison_router = APIRouter(tags=["comparison"])


@comparison_router.post("/compare")
async def compare_placeholder() -> None:
    """Placeholder compare endpoint until model-comparison logic is implemented."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Compare endpoint not implemented yet.",
    )