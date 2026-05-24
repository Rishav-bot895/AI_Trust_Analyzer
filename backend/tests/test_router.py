"""Tests for API router wiring (Task 1.11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db


def _jwt_for(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        "test-supabase-jwt-secret-32bytes-long",
        algorithm="HS256",
    )


def _load_main_module():
    return importlib.import_module("app.main")


def test_router_prefix_applied(monkeypatch):
    """POST analyze route should be mounted under /api/v1 prefix."""
    async def _fake_background(**_: object) -> None:
        return None

    analysis_routes = importlib.import_module("app.api.routes.analysis")
    monkeypatch.setattr(analysis_routes, "_run_analysis_in_background", _fake_background)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    main = _load_main_module()
    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as client:
        prefixed_response = client.post(
            "/api/v1/analyze",
            json={
                "prompt": "Explain gravity",
                "response": "Gravity attracts masses toward each other.",
                "model_name": "gemini-3.1-flash-lite",
            },
            headers={"Authorization": f"Bearer {_jwt_for('user-123')}"},
        )
        unprefixed_response = client.post("/analyze")
    main.app.dependency_overrides.clear()

    assert prefixed_response.status_code == 202
    assert unprefixed_response.status_code == 404


def test_openapi_schema_includes_analyze():
    """Analyze endpoint should appear in generated OpenAPI schema."""
    main = _load_main_module()
    with TestClient(main.app) as client:
        schema = client.get("/openapi.json").json()

    assert "/api/v1/analyze" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/analyze"]


def test_health_route_exists():
    """Health endpoint should exist under API v1 and return ok payload."""
    main = _load_main_module()
    with TestClient(main.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}