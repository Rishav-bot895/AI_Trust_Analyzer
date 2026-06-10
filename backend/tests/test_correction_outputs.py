"""Correction-task regression and API contract snapshot tests (D1-D3)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Analysis, Base, Claim, Evidence
from app.db.session import get_db
from app.main import app


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden" / "apollo_mission_golden_output.json"


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


async def _seed_completed_analysis(session: AsyncSession, user_id: str) -> str:
    analysis = Analysis(
        status="COMPLETED",
        user_id=user_id,
        is_guest=False,
        prompt="Explain the Apollo program",
        response="Apollo 11 landed on the Moon in 1969 and returned safely.",
        model_name="gemini-3.1-flash-lite",
        trust_score=92.0,
        hallucination_risk="LOW",
        critique="## Logical Issues\nNo logical issues detected.",
        verdict="Both claims are well supported by authoritative Apollo mission records.",
        completed_at=datetime.now(timezone.utc),
        timeline=json.dumps(
            [
                {
                    "agent": "extractor",
                    "started_at": "2026-06-06T10:13:01Z",
                    "completed_at": "2026-06-06T10:13:10Z",
                    "input_summary": "response text received",
                    "output_summary": "2 claims extracted",
                },
                {
                    "agent": "retriever",
                    "started_at": "2026-06-06T10:13:10Z",
                    "completed_at": "2026-06-06T10:13:35Z",
                    "input_summary": "2 claims",
                    "output_summary": "4 evidence items",
                },
            ]
        ),
    )
    session.add(analysis)
    await session.flush()

    claim_1 = Claim(
        analysis_id=analysis.id,
        text="Apollo 11 landed on the Moon in 1969.",
        confidence=0.91,
        status="SUPPORTED",
        claim_index=0,
    )
    claim_2 = Claim(
        analysis_id=analysis.id,
        text="Apollo 11 returned safely.",
        confidence=0.88,
        status="SUPPORTED",
        claim_index=1,
    )
    session.add_all([claim_1, claim_2])
    await session.flush()

    evidence_rows = [
        Evidence(
            claim_id=claim_1.id,
            snippet="NASA confirms Apollo 11 landed in July 1969.",
            source_url="https://www.nasa.gov/mission/apollo-11/",
            source_title="Apollo 11 - NASA",
            relevance_score=0.96,
            source_type="WEB_SEARCH",
            polarity="FOR",
        ),
        Evidence(
            claim_id=claim_2.id,
            snippet="Apollo 11 safely returned to Earth after lunar mission completion.",
            source_url="https://www.history.com/this-day-in-history/apollo-11-returns-to-earth",
            source_title="Apollo 11 safely returns to Earth | HISTORY",
            relevance_score=0.91,
            source_type="WEB_SEARCH",
            polarity="FOR",
        ),
    ]
    session.add_all(evidence_rows)
    await session.commit()
    return analysis.id


def test_golden_fixture_apollo_is_present_and_well_formed():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)

    assert fixture["case_id"] == "apollo_mission_known_facts"
    assert fixture["expected"]["hallucination_risk"] == "LOW"
    assert fixture["expected"]["trust_score_min"] >= 80.0
    assert len(fixture["expected"]["claims"]) >= 2
    assert all(item["status"] == "SUPPORTED" for item in fixture["expected"]["claims"])


def test_regression_targets_match_apollo_golden_fixture():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)

    expected = fixture["expected"]
    assert expected["status"] == "COMPLETED"
    assert expected["trust_score_min"] >= 80.0
    assert expected["hallucination_risk"] == "LOW"

    assert all(claim["status"] != "UNVERIFIABLE" for claim in expected["claims"])

    supportive_titles = {item["source_title"] for item in expected["evidence"]}
    assert "Apollo 11 - NASA" in supportive_titles
    assert "Apollo 11 safely returns to Earth | HISTORY" in supportive_titles
    assert all(item["polarity"] == "FOR" for item in expected["evidence"])


def test_analysis_api_snapshot_contract_keys(tmp_path: Path):
    engine = create_async_engine(_db_url(tmp_path, "correction_snapshot_contract"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    seeded = {"analysis_id": None}

    async def override_get_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            if seeded["analysis_id"] is None:
                seeded["analysis_id"] = await _seed_completed_analysis(session, "snapshot-user")
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {_jwt_for('snapshot-user')}"}
            analysis_id = str(seeded["analysis_id"] or "")
            if not analysis_id:
                response = client.get("/api/v1/analyze/history", headers=headers)
                assert response.status_code == 200
                analysis_id = response.json()[0]["id"]

            analysis_response = client.get(f"/api/v1/analyze/{analysis_id}", headers=headers)
            claims_response = client.get(f"/api/v1/analyze/{analysis_id}/claims", headers=headers)
            evidence_response = client.get(f"/api/v1/analyze/{analysis_id}/evidence", headers=headers)
            timeline_response = client.get(f"/api/v1/analyze/{analysis_id}/timeline", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert analysis_response.status_code == 200
    assert claims_response.status_code == 200
    assert evidence_response.status_code == 200
    assert timeline_response.status_code == 200

    analysis_payload = analysis_response.json()
    claim_item = claims_response.json()[0]
    evidence_item = evidence_response.json()[0]
    timeline_item = timeline_response.json()[0]

    assert set(analysis_payload.keys()) == {
        "id",
        "status",
        "prompt",
        "response",
        "model_name",
        "trust_score",
        "hallucination_risk",
        "claims",
        "evidence",
        "timeline",
        "critique",
        "verdict",
        "created_at",
        "completed_at",
        "error",
    }

    assert set(claim_item.keys()) == {
        "id",
        "text",
        "confidence",
        "status",
        "claim_index",
        "source_span",
    }

    assert set(evidence_item.keys()) == {
        "id",
        "claim_id",
        "snippet",
        "source_url",
        "source_title",
        "relevance_score",
        "source_type",
        "polarity",
        "retrieved_at",
    }

    assert set(timeline_item.keys()) == {
        "agent",
        "started_at",
        "completed_at",
        "input_summary",
        "output_summary",
    }

    verdict_text = analysis_payload["verdict"]
    assert isinstance(verdict_text, str)
    assert verdict_text.strip()
    assert "{" not in verdict_text
    assert "[" not in verdict_text
