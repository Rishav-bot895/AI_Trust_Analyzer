"""Health route placeholders for API bootstrap phase."""

from fastapi import APIRouter


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health endpoint used for readiness checks."""
    return {"status": "ok"}