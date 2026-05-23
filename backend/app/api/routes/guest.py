"""Guest session lifecycle routes."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import create_guest_session_token
from app.core.config import settings
from app.db.session import get_db
from app.services.guest_cleanup import cleanup_expired_guest_data, end_guest_session


guest_router = APIRouter(prefix="/guest", tags=["guest"])


class GuestSessionEndRequest(BaseModel):
    """Payload used to explicitly end an active guest session."""

    guest_session_id: str = Field(min_length=1)


class GuestSessionCleanupResponse(BaseModel):
    """Response payload for guest cleanup actions."""

    deleted_analyses: int


class GuestSessionStartResponse(BaseModel):
    """Response payload for guest session initialization."""

    guest_session_id: str
    guest_session_token: str


def _require_service_role_key(
    x_service_role_key: Annotated[str | None, Header(alias="X-Service-Role-Key")] = None,
) -> None:
    if x_service_role_key != settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service role key.",
        )


@guest_router.post("/session/start", response_model=GuestSessionStartResponse, status_code=201)
async def start_guest_session_route() -> GuestSessionStartResponse:
    """Issue a signed guest session identifier for subsequent guest-scoped requests."""
    guest_session_id = str(uuid4())
    return GuestSessionStartResponse(
        guest_session_id=guest_session_id,
        guest_session_token=create_guest_session_token(guest_session_id),
    )


@guest_router.post("/session/end", response_model=GuestSessionCleanupResponse, status_code=202)
async def end_guest_session_route(
    payload: GuestSessionEndRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_guest_session_token: Annotated[str, Header(alias="X-Guest-Session-Token")],
) -> GuestSessionCleanupResponse:
    """Delete all guest-owned analysis data for an explicit session end."""
    expected = create_guest_session_token(payload.guest_session_id)
    if expected != x_guest_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid guest session token.",
        )

    deleted = await end_guest_session(db, payload.guest_session_id)
    return GuestSessionCleanupResponse(deleted_analyses=deleted)


@guest_router.post(
    "/cleanup-expired",
    response_model=GuestSessionCleanupResponse,
    status_code=202,
    dependencies=[Depends(_require_service_role_key)],
)
async def cleanup_expired_guest_data_route(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GuestSessionCleanupResponse:
    """Delete abandoned guest data that exceeded the configured TTL."""
    deleted = await cleanup_expired_guest_data(db)
    return GuestSessionCleanupResponse(deleted_analyses=deleted)
