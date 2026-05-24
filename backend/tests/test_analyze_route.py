"""Tests for POST /api/v1/analyze route (Task 3.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Analysis, Base, Claim, Evidence
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


def _db_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / f'{name}.db').as_posix()}"


async def _init_db(engine) -> None:  # noqa: ANN001
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_post_analyze_returns_202(tmp_path: Path, monkeypatch):
    engine = create_async_engine(_db_url(tmp_path, "post_analyze_202"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def fake_background(**_: object) -> None:
        return None

    monkeypatch.setattr("app.api.routes.analysis._run_analysis_in_background", fake_background)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                json={
                    "prompt": "Explain gravity",
                    "response": "Gravity attracts masses toward each other.",
                    "model_name": "gemini-3.1-flash-lite",
                },
                headers={"Authorization": f"Bearer {_jwt_for('user-123')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202


def test_post_analyze_returns_id_and_pending_status(tmp_path: Path, monkeypatch):
    engine = create_async_engine(_db_url(tmp_path, "post_analyze_payload"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def fake_background(**_: object) -> None:
        return None

    monkeypatch.setattr("app.api.routes.analysis._run_analysis_in_background", fake_background)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                json={
                    "prompt": "Explain gravity",
                    "response": "Gravity attracts masses toward each other.",
                    "model_name": "gemini-3.1-flash-lite",
                },
                headers={"Authorization": f"Bearer {_jwt_for('user-abc')}"},
            )

        async def _fetch_saved() -> Analysis | None:
            async with session_factory() as session:
                result = await session.execute(select(Analysis))
                return result.scalar_one_or_none()

        saved = __import__("asyncio").run(_fetch_saved())
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert payload["id"]
    assert payload["status"] == "PENDING"
    assert saved is not None
    assert saved.id == payload["id"]
    assert saved.status == "PENDING"
    assert saved.prompt == "Explain gravity"


def test_post_analyze_invalid_body_returns_422(tmp_path: Path, monkeypatch):
    engine = create_async_engine(_db_url(tmp_path, "post_analyze_invalid"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def fake_background(**_: object) -> None:
        return None

    monkeypatch.setattr("app.api.routes.analysis._run_analysis_in_background", fake_background)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                json={
                    "prompt": "",
                    "response": "still present",
                },
                headers={"Authorization": f"Bearer {_jwt_for('user-123')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_post_analyze_background_task_fires(tmp_path: Path, monkeypatch):
    engine = create_async_engine(_db_url(tmp_path, "post_analyze_background"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    calls: list[dict[str, object]] = []

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def fake_background(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.api.routes.analysis._run_analysis_in_background", fake_background)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                json={
                    "prompt": "Explain gravity",
                    "response": "Gravity attracts masses toward each other.",
                    "model_name": "gemini-3.1-flash-lite",
                },
                headers={"Authorization": f"Bearer {_jwt_for('user-999')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert len(calls) == 1
    assert calls[0]["analysis_id"] == response.json()["id"]
    assert calls[0]["model_name"] == "gemini-3.1-flash-lite"


def test_get_analysis_not_found_returns_404(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_analyze_404"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analyze/missing-id",
                headers={"Authorization": f"Bearer {_jwt_for('user-123')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_get_analysis_pending_returns_200(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_analyze_pending"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="PENDING",
                user_id="user-pending",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}",
                headers={"Authorization": f"Bearer {_jwt_for('user-pending')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "PENDING"
    assert payload["trust_score"] is None
    assert payload["claims"] == []
    assert payload["evidence"] == []


def test_get_analysis_completed_returns_full_result(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_analyze_completed"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="user-complete",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
                trust_score=88.0,
                hallucination_risk="LOW",
                critique="No issues.",
                verdict="Mostly trustworthy.",
                completed_at=datetime.now(timezone.utc),
            )
            session.add(analysis)
            await session.flush()

            claim = Claim(
                analysis_id=analysis.id,
                text="Earth orbits the Sun",
                confidence=0.9,
                status="SUPPORTED",
                claim_index=0,
            )
            session.add(claim)
            await session.flush()

            evidence = Evidence(
                claim_id=claim.id,
                snippet="NASA states Earth orbits the Sun.",
                source_url="https://www.nasa.gov",
                source_title="NASA",
                relevance_score=0.93,
                source_type="WEB_SEARCH",
                polarity="FOR",
            )
            session.add(evidence)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}",
                headers={"Authorization": f"Bearer {_jwt_for('user-complete')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "COMPLETED"
    assert payload["trust_score"] == 88.0
    assert payload["hallucination_risk"] == "LOW"
    assert payload["critique"] == "No issues."
    assert payload["verdict"] == "Mostly trustworthy."
    assert len(payload["claims"]) == 1
    assert payload["claims"][0]["text"] == "Earth orbits the Sun"
    assert payload["claims"][0]["status"] == "SUPPORTED"
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["source_type"] == "WEB_SEARCH"


def test_get_analysis_failed_returns_error(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_analyze_failed"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="FAILED",
                user_id="user-failed",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
                error="analysis pipeline failed",
                completed_at=datetime.now(timezone.utc),
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}",
                headers={"Authorization": f"Bearer {_jwt_for('user-failed')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "FAILED"
    assert payload["error"] == "analysis pipeline failed"


def test_get_claims_no_filter(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_claims_no_filter"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="claims-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.flush()

            claim_one = Claim(
                analysis_id=analysis.id,
                text="Claim one",
                confidence=0.8,
                status="SUPPORTED",
                claim_index=0,
            )
            claim_two = Claim(
                analysis_id=analysis.id,
                text="Claim two",
                confidence=0.4,
                status="CONTRADICTED",
                claim_index=1,
            )
            session.add_all([claim_one, claim_two])
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/claims",
                headers={"Authorization": f"Bearer {_jwt_for('claims-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 2
    assert payload[0]["text"] == "Claim one"
    assert payload[1]["text"] == "Claim two"


def test_get_claims_filter_by_status(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_claims_filter_status"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="claims-status-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.flush()

            claim_one = Claim(
                analysis_id=analysis.id,
                text="Supported claim",
                confidence=0.9,
                status="SUPPORTED",
                claim_index=0,
            )
            claim_two = Claim(
                analysis_id=analysis.id,
                text="Unsupported claim",
                confidence=0.3,
                status="UNSUPPORTED",
                claim_index=1,
            )
            session.add_all([claim_one, claim_two])
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/claims?status=SUPPORTED",
                headers={"Authorization": f"Bearer {_jwt_for('claims-status-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["status"] == "SUPPORTED"
    assert payload[0]["text"] == "Supported claim"


def test_get_claims_invalid_status_400(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_claims_invalid_status"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="claims-invalid-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/claims?status=BANANA",
                headers={"Authorization": f"Bearer {_jwt_for('claims-invalid-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid claim status: BANANA"


def test_get_claims_analysis_not_found_404(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_claims_not_found"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/analyze/missing-id/claims",
                headers={"Authorization": f"Bearer {_jwt_for('claims-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_get_evidence_no_filter(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_evidence_no_filter"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> tuple[str, str]:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="evidence-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.flush()

            claim = Claim(
                analysis_id=analysis.id,
                text="Claim one",
                confidence=0.8,
                status="SUPPORTED",
                claim_index=0,
            )
            session.add(claim)
            await session.flush()

            low = Evidence(
                claim_id=claim.id,
                snippet="Lower relevance",
                source_url="https://example.com/low",
                source_title="Low",
                relevance_score=0.40,
                source_type="WEB_SEARCH",
                polarity="FOR",
            )
            high = Evidence(
                claim_id=claim.id,
                snippet="Higher relevance",
                source_url="https://example.com/high",
                source_title="High",
                relevance_score=0.92,
                source_type="WEB_SEARCH",
                polarity="FOR",
            )
            session.add_all([low, high])
            await session.commit()
            await session.refresh(analysis)
            await session.refresh(claim)
            return analysis.id, claim.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id, _ = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/evidence",
                headers={"Authorization": f"Bearer {_jwt_for('evidence-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 2
    assert payload[0]["snippet"] == "Higher relevance"
    assert payload[1]["snippet"] == "Lower relevance"


def test_get_evidence_filter_by_claim_id(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_evidence_filter_claim"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> tuple[str, str]:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="evidence-filter-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.flush()

            claim_one = Claim(
                analysis_id=analysis.id,
                text="Claim one",
                confidence=0.8,
                status="SUPPORTED",
                claim_index=0,
            )
            claim_two = Claim(
                analysis_id=analysis.id,
                text="Claim two",
                confidence=0.4,
                status="UNSUPPORTED",
                claim_index=1,
            )
            session.add_all([claim_one, claim_two])
            await session.flush()

            evidence_one = Evidence(
                claim_id=claim_one.id,
                snippet="Evidence for claim one",
                source_url="https://example.com/one",
                source_title="One",
                relevance_score=0.8,
                source_type="WEB_SEARCH",
                polarity="FOR",
            )
            evidence_two = Evidence(
                claim_id=claim_two.id,
                snippet="Evidence for claim two",
                source_url="https://example.com/two",
                source_title="Two",
                relevance_score=0.7,
                source_type="WEB_SEARCH",
                polarity="AGAINST",
            )
            session.add_all([evidence_one, evidence_two])
            await session.commit()
            await session.refresh(analysis)
            await session.refresh(claim_one)
            return analysis.id, claim_one.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id, claim_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/evidence?claim_id={claim_id}",
                headers={"Authorization": f"Bearer {_jwt_for('evidence-filter-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["claim_id"] == claim_id
    assert payload[0]["snippet"] == "Evidence for claim one"


def test_get_evidence_invalid_claim_uuid_422(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_evidence_invalid_uuid"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="COMPLETED",
                user_id="evidence-invalid-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/evidence?claim_id=not-a-uuid",
                headers={"Authorization": f"Bearer {_jwt_for('evidence-invalid-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_get_timeline_completed_has_five_events(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_timeline_completed"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            timeline = [
                {
                    "agent": "extractor",
                    "started_at": "2026-01-01T00:00:00Z",
                    "completed_at": "2026-01-01T00:00:01Z",
                    "input_summary": "response text",
                    "output_summary": "2 claims",
                },
                {
                    "agent": "retriever",
                    "started_at": "2026-01-01T00:00:01Z",
                    "completed_at": "2026-01-01T00:00:02Z",
                    "input_summary": "2 claims",
                    "output_summary": "4 evidence",
                },
                {
                    "agent": "verifier",
                    "started_at": "2026-01-01T00:00:02Z",
                    "completed_at": "2026-01-01T00:00:03Z",
                    "input_summary": "4 evidence",
                    "output_summary": "2 verdicts",
                },
                {
                    "agent": "critic",
                    "started_at": "2026-01-01T00:00:03Z",
                    "completed_at": "2026-01-01T00:00:04Z",
                    "input_summary": "response + statuses",
                    "output_summary": "critique text",
                },
                {
                    "agent": "judge",
                    "started_at": "2026-01-01T00:00:04Z",
                    "completed_at": "2026-01-01T00:00:05Z",
                    "input_summary": "verified claims + critique",
                    "output_summary": "score + verdict",
                },
            ]
            analysis = Analysis(
                status="COMPLETED",
                user_id="timeline-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
                timeline=__import__("json").dumps(timeline),
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/timeline",
                headers={"Authorization": f"Bearer {_jwt_for('timeline-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 5
    assert [event["agent"] for event in payload] == [
        "extractor",
        "retriever",
        "verifier",
        "critic",
        "judge",
    ]


def test_get_timeline_pending_returns_empty_list(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_timeline_pending"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            analysis = Analysis(
                status="PENDING",
                user_id="timeline-pending-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
                timeline=None,
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/timeline",
                headers={"Authorization": f"Bearer {_jwt_for('timeline-pending-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_get_timeline_event_structure(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "get_timeline_structure"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    async def seed() -> str:
        async with session_factory() as session:
            timeline = [
                {
                    "agent": "extractor",
                    "started_at": "2026-01-01T00:00:00Z",
                    "completed_at": "2026-01-01T00:00:01Z",
                    "input_summary": "response text",
                    "output_summary": "2 claims",
                }
            ]
            analysis = Analysis(
                status="COMPLETED",
                user_id="timeline-structure-user",
                is_guest=False,
                prompt="Prompt",
                response="Response",
                model_name="gemini-3.1-flash-lite",
                timeline=__import__("json").dumps(timeline),
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
            return analysis.id

    __import__("asyncio").run(_init_db(engine))
    analysis_id = __import__("asyncio").run(seed())

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/analyze/{analysis_id}/timeline",
                headers={"Authorization": f"Bearer {_jwt_for('timeline-structure-user')}"},
            )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert len(payload) == 1
    assert set(payload[0].keys()) == {
        "agent",
        "started_at",
        "completed_at",
        "input_summary",
        "output_summary",
    }
