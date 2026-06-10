"""Tests for requester-scoped analysis history endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import create_guest_session_token
from app.db.models import Analysis, Base
from app.db.session import get_db
from app.main import app


def _jwt_for(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        "test-supabase-jwt-secret-32bytes-long",
        algorithm="HS256",
    )


async def _seed_history(db: AsyncSession) -> None:
    rows = [
        Analysis(
            status="COMPLETED",
            trust_score=91.0,
            hallucination_risk="LOW",
            user_id="user-a",
            is_guest=False,
            created_at=datetime.now(timezone.utc),
        ),
        Analysis(
            status="FAILED",
            trust_score=None,
            hallucination_risk=None,
            user_id="user-a",
            is_guest=False,
            error="pipeline error",
            created_at=datetime.now(timezone.utc),
        ),
        Analysis(
            status="COMPLETED",
            trust_score=55.0,
            hallucination_risk="MEDIUM",
            user_id="user-b",
            is_guest=False,
            created_at=datetime.now(timezone.utc),
        ),
        Analysis(
            status="COMPLETED",
            trust_score=70.0,
            hallucination_risk="MEDIUM",
            is_guest=True,
            guest_session_id="guest-1",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    db.add_all(rows)
    await db.commit()


def _db_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / f'{name}.db').as_posix()}"


def test_history_returns_guest_session_records(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "history_guest_scoped"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    seeded = {"done": False}

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            if not seeded["done"]:
                await _seed_history(session)
                seeded["done"] = True
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.get(
                    "/api/v1/analyze/history",
                    headers={
                        "X-Guest-Session-Id": "guest-1",
                        "X-Guest-Session-Token": create_guest_session_token("guest-1"),
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["trust_score"] == 70.0


def test_history_returns_only_authenticated_users_records(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "history_authenticated_only"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    seeded = {"done": False}

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            if not seeded["done"]:
                await _seed_history(session)
                seeded["done"] = True
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analyze/history",
                headers={"Authorization": f"Bearer {_jwt_for('user-a')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert {item["status"] for item in payload} == {"COMPLETED", "FAILED"}
    assert all(item["id"] for item in payload)


def test_history_limit_and_offset_applied(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "history_limit_offset"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    seeded = {"done": False}

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            if not seeded["done"]:
                await _seed_history(session)
                seeded["done"] = True
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analyze/history?limit=1&offset=1",
                headers={"Authorization": f"Bearer {_jwt_for('user-a')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
