"""Top-level API router assembly."""

from fastapi import APIRouter

from app.api.routes.analysis import analysis_router
from app.api.routes.comparison import comparison_router
from app.api.routes.guest import guest_router
from app.api.routes.health import health_router


router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(analysis_router)
router.include_router(comparison_router)
router.include_router(guest_router)
