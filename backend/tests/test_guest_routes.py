"""Tests for guest session lifecycle routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import create_guest_session_token
from app.db.session import get_db
from app.main import app


async def _override_get_db():
    yield None


def test_guest_session_end_route_returns_202(monkeypatch):
    async def fake_end_guest_session(session, guest_session_id: str) -> int:  # noqa: ANN001
        return 3

    monkeypatch.setattr("app.api.routes.guest.end_guest_session", fake_end_guest_session)
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/guest/session/end",
                json={"guest_session_id": "guest-abc"},
                headers={"X-Guest-Session-Token": create_guest_session_token("guest-abc")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"deleted_analyses": 3}


def test_guest_session_start_returns_signed_session_headers():
    with TestClient(app) as client:
        response = client.post("/api/v1/guest/session/start")

    assert response.status_code == 201
    payload = response.json()
    assert payload["guest_session_id"]
    assert payload["guest_session_token"] == create_guest_session_token(payload["guest_session_id"])


def test_guest_cleanup_expired_route_requires_service_key(monkeypatch):
    async def fake_cleanup_expired_guest_data(session) -> int:  # noqa: ANN001
        return 2

    monkeypatch.setattr(
        "app.api.routes.guest.cleanup_expired_guest_data",
        fake_cleanup_expired_guest_data,
    )
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as client:
            forbidden = client.post("/api/v1/guest/cleanup-expired")
            allowed = client.post(
                "/api/v1/guest/cleanup-expired",
                headers={"X-Service-Role-Key": "test-supabase-service-role-key"},
            )
    finally:
        app.dependency_overrides.clear()

    assert forbidden.status_code == 403
    assert allowed.status_code == 202
    assert allowed.json() == {"deleted_analyses": 2}
