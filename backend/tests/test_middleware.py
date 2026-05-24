"""Tests for global exception handling and API rate limiting (Task 3.7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db
from app.main import create_app


def _jwt_for(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        "test-supabase-jwt-secret-32bytes-long",
        algorithm="HS256",
    )


def _db_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / f'{name}.db').as_posix()}"


def test_unhandled_exception_returns_500_json():
    app = create_app()

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"] == "Internal server error"
    assert payload["detail"] == "boom"


def test_http_exception_returns_correct_status():
    app = create_app()

    @app.get("/teapot")
    async def teapot() -> dict[str, str]:
        raise HTTPException(status_code=404, detail="Not Found")

    with TestClient(app) as client:
        response = client.get("/teapot")

    assert response.status_code == 404
    assert response.json() == {"error": "Not Found"}


def test_rate_limit_returns_429(tmp_path: Path, monkeypatch):
    engine = create_async_engine(_db_url(tmp_path, "rate_limit"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def fake_background(**_: object) -> None:
        return None

    monkeypatch.setattr("app.api.routes.analysis._run_analysis_in_background", fake_background)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            payload = {
                "prompt": "Explain gravity",
                "response": "Gravity attracts masses toward each other.",
                "model_name": "gemini-3.1-flash-lite",
            }
            headers = {"Authorization": f"Bearer {_jwt_for('rate-user')}"}

            last = None
            saw_429 = False
            for _ in range(31):
                last = client.post("/api/v1/analyze", json=payload, headers=headers)
                if last.status_code == 429:
                    saw_429 = True
                    break
    finally:
        app.dependency_overrides.clear()

    assert saw_429 is True
    assert last is not None
    assert last.status_code == 429
    assert "Retry-After" in last.headers
