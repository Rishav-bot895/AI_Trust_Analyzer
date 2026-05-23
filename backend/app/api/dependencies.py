"""Shared API dependencies for requester ownership context."""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import Header, HTTPException, status
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError

from app.db.repository import RequestOwner
from app.core.config import resolve_supabase_jwks_url, settings


_jwks_client: PyJWKClient | None = None


def create_guest_session_token(guest_session_id: str) -> str:
    """Create an HMAC-signed token for a guest session identifier."""
    digest = hmac.new(
        settings.SUPABASE_JWT_SECRET.encode("utf-8"),
        guest_session_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def verify_guest_session_token(guest_session_id: str, token: str) -> bool:
    """Verify that token matches guest session id signature."""
    expected = create_guest_session_token(guest_session_id)
    return hmac.compare_digest(expected, token)


def _jwt_decode_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "options": {
            "require": ["exp", "sub"],
            "verify_aud": bool(settings.SUPABASE_JWT_AUDIENCE),
        }
    }
    if settings.SUPABASE_JWT_ISSUER:
        kwargs["issuer"] = settings.SUPABASE_JWT_ISSUER
    if settings.SUPABASE_JWT_AUDIENCE:
        kwargs["audience"] = settings.SUPABASE_JWT_AUDIENCE
    return kwargs


def _decode_with_hs256(token: str) -> dict[str, object]:
    """Decode with shared-secret HS256 fallback for development only."""
    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        **_jwt_decode_kwargs(),
    )


def _decode_with_jwks(token: str) -> dict[str, object]:
    """Decode Supabase JWT using JWKS-based asymmetric verification."""
    global _jwks_client

    if _jwks_client is None:
        _jwks_client = PyJWKClient(resolve_supabase_jwks_url())

    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256", "EdDSA"],
        **_jwt_decode_kwargs(),
    )


def _decode_supabase_jwt(token: str) -> dict[str, object]:
    strategy = settings.SUPABASE_JWT_VERIFY_STRATEGY
    if strategy == "hs256":
        return _decode_with_hs256(token)
    if strategy == "jwks":
        return _decode_with_jwks(token)
    raise InvalidTokenError(f"Unsupported JWT verification strategy: {strategy}")


def _extract_authenticated_user_id(authorization: str) -> str:
    """Decode and verify Supabase JWT, returning authenticated user id."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be in the format: Bearer <token>",
        )

    try:
        payload = _decode_supabase_jwt(token.strip())
    except (InvalidTokenError, PyJWKClientError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
        ) from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated token missing subject claim.",
        )

    return user_id


async def get_request_owner(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_guest_session_id: Annotated[str | None, Header(alias="X-Guest-Session-Id")] = None,
    x_guest_session_token: Annotated[str | None, Header(alias="X-Guest-Session-Token")] = None,
) -> RequestOwner:
    """Resolve request ownership context from headers.

    Authenticated mode requires a valid Supabase JWT.
    Guest mode requires both signed guest session headers.
    """
    if authorization and (x_guest_session_id or x_guest_session_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either Authorization or guest session headers, not both.",
        )

    if authorization:
        return RequestOwner(is_guest=False, user_id=_extract_authenticated_user_id(authorization))

    if bool(x_guest_session_id) != bool(x_guest_session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest requests require both X-Guest-Session-Id and X-Guest-Session-Token.",
        )

    if x_guest_session_id and x_guest_session_token:
        if not verify_guest_session_token(x_guest_session_id, x_guest_session_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid guest session token.",
            )
        return RequestOwner(is_guest=True, guest_session_id=x_guest_session_id)

    guest_session_id = str(uuid4())
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Guest session is not initialized. Call POST /api/v1/guest/session/start "
            "to obtain session headers."
        ),
        headers={
            "X-Guest-Session-Id": guest_session_id,
            "X-Guest-Session-Token": create_guest_session_token(guest_session_id),
        },
    )
