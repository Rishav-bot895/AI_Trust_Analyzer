"""Comparison route placeholders for API bootstrap phase."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_request_owner
from app.db.repository import RequestOwner


comparison_router = APIRouter(tags=["comparison"])


@comparison_router.post("/compare")
async def compare_placeholder(
    owner: Annotated[RequestOwner, Depends(get_request_owner)],
) -> None:
    """Placeholder compare endpoint until model-comparison logic is implemented."""
    _ = owner
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Compare endpoint not implemented yet.",
    )