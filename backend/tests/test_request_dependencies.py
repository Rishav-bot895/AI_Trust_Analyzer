"""Tests for requester ownership dependency parsing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.api.dependencies import create_guest_session_token, get_request_owner
from app.core.config import settings


def _jwt_for(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        "test-supabase-jwt-secret-32bytes-long",
        algorithm="HS256",
    )


def _jwt_for_claims(
    user_id: str,
    *,
    secret: str,
    expires_in_minutes: int = 30,
    issuer: str | None = None,
    audience: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    if issuer:
        payload["iss"] = issuer
    if audience:
        payload["aud"] = audience
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_get_request_owner_authenticated_mode():
    owner = await get_request_owner(
        authorization=f"Bearer {_jwt_for('user-123')}",
        x_guest_session_id=None,
        x_guest_session_token=None,
    )

    assert owner.is_guest is False
    assert owner.user_id == "user-123"
    assert owner.guest_session_id is None


@pytest.mark.asyncio
async def test_get_request_owner_guest_mode_with_explicit_session():
    owner = await get_request_owner(
        authorization=None,
        x_guest_session_id="guest-123",
        x_guest_session_token=create_guest_session_token("guest-123"),
    )

    assert owner.is_guest is True
    assert owner.user_id is None
    assert owner.guest_session_id == "guest-123"


@pytest.mark.asyncio
async def test_get_request_owner_without_headers_raises_401():
    with pytest.raises(HTTPException) as exc:
        await get_request_owner(authorization=None, x_guest_session_id=None, x_guest_session_token=None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_request_owner_rejects_mixed_headers():
    with pytest.raises(HTTPException) as exc:
        await get_request_owner(
            authorization=f"Bearer {_jwt_for('user-123')}",
            x_guest_session_id="guest-123",
            x_guest_session_token=create_guest_session_token("guest-123"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_request_owner_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", None)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", None)

    invalid_token = _jwt_for_claims(
        "user-123",
        secret="wrong-secret-key-that-is-at-least-thirty-two-bytes",
    )

    with pytest.raises(HTTPException) as exc:
        await get_request_owner(
            authorization=f"Bearer {invalid_token}",
            x_guest_session_id=None,
            x_guest_session_token=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_request_owner_rejects_wrong_issuer_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", "https://expected-issuer")
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", None)

    token = _jwt_for_claims(
        "user-123",
        secret=settings.SUPABASE_JWT_SECRET,
        issuer="https://wrong-issuer",
    )

    with pytest.raises(HTTPException) as exc:
        await get_request_owner(
            authorization=f"Bearer {token}",
            x_guest_session_id=None,
            x_guest_session_token=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_request_owner_rejects_wrong_audience_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", None)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "expected-audience")

    token = _jwt_for_claims(
        "user-123",
        secret=settings.SUPABASE_JWT_SECRET,
        audience="wrong-audience",
    )

    with pytest.raises(HTTPException) as exc:
        await get_request_owner(
            authorization=f"Bearer {token}",
            x_guest_session_id=None,
            x_guest_session_token=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_request_owner_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", None)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", None)

    expired_token = _jwt_for_claims(
        "user-123",
        secret=settings.SUPABASE_JWT_SECRET,
        expires_in_minutes=-1,
    )

    with pytest.raises(HTTPException) as exc:
        await get_request_owner(
            authorization=f"Bearer {expired_token}",
            x_guest_session_id=None,
            x_guest_session_token=None,
        )

    assert exc.value.status_code == 401
