"""Tests for POST /api/v1/compare route (Task 3.6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

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


def _base_payload(models: list[str]) -> dict[str, object]:
    return {
        "prompt": "Explain the Apollo program",
        "response": "Apollo 11 landed on the Moon in 1969 and returned safely.",
        "models": models,
    }


def test_compare_two_models_returns_two_analyses(monkeypatch):
    async def fake_run_analysis(*, analysis_id: str, prompt: str, response: str, model_name: str):
        return {
            "analysis_id": analysis_id,
            "prompt": prompt,
            "response": response,
            "model_name": model_name,
            "claims": [],
            "evidence": [],
            "verified_claims": [],
            "critique": "No issues",
            "trust_score": 82.0,
            "hallucination_risk": "LOW",
            "verdict": f"{model_name} verdict",
            "timeline": [],
            "error": None,
        }

    monkeypatch.setattr("app.api.routes.comparison.run_analysis", fake_run_analysis)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/compare",
            json=_base_payload(["gemini-3.1-flash-lite", "gemini-2.0-flash"]),
            headers={"Authorization": f"Bearer {_jwt_for('compare-user')}"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["analyses"]) == 2
    assert payload["analyses"][0]["status"] == "COMPLETED"
    assert payload["analyses"][1]["status"] == "COMPLETED"
    assert payload["analyses"][0]["trust_score"] == 82.0
    assert payload["analyses"][1]["trust_score"] == 82.0


def test_compare_one_model_fails_others_continue(monkeypatch):
    async def fake_run_analysis(*, analysis_id: str, prompt: str, response: str, model_name: str):
        if model_name == "broken-model":
            raise RuntimeError("model unavailable")
        return {
            "analysis_id": analysis_id,
            "prompt": prompt,
            "response": response,
            "model_name": model_name,
            "claims": [],
            "evidence": [],
            "verified_claims": [],
            "critique": "No issues",
            "trust_score": 77.0,
            "hallucination_risk": "MEDIUM",
            "verdict": f"{model_name} verdict",
            "timeline": [],
            "error": None,
        }

    monkeypatch.setattr("app.api.routes.comparison.run_analysis", fake_run_analysis)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/compare",
            json=_base_payload(["gemini-3.1-flash-lite", "broken-model"]),
            headers={"Authorization": f"Bearer {_jwt_for('compare-user')}"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["analyses"]) == 2
    assert payload["analyses"][0]["status"] == "COMPLETED"
    assert payload["analyses"][1]["status"] == "FAILED"
    assert payload["analyses"][1]["error"] == "model unavailable"


def test_compare_concurrent_execution(monkeypatch):
    started: list[str] = []
    finished: list[str] = []

    import asyncio

    all_started = asyncio.Event()

    async def fake_run_analysis(*, analysis_id: str, prompt: str, response: str, model_name: str):
        started.append(model_name)
        if len(started) == 2:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=0.2)
        finished.append(model_name)
        return {
            "analysis_id": analysis_id,
            "prompt": prompt,
            "response": response,
            "model_name": model_name,
            "claims": [],
            "evidence": [],
            "verified_claims": [],
            "critique": "No issues",
            "trust_score": 80.0,
            "hallucination_risk": "LOW",
            "verdict": f"{model_name} verdict",
            "timeline": [],
            "error": None,
        }

    monkeypatch.setattr("app.api.routes.comparison.run_analysis", fake_run_analysis)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/compare",
            json=_base_payload(["model-a", "model-b"]),
            headers={"Authorization": f"Bearer {_jwt_for('compare-user')}"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert [item["status"] for item in payload["analyses"]] == ["COMPLETED", "COMPLETED"]
    assert set(started) == {"model-a", "model-b"}
    assert set(finished) == {"model-a", "model-b"}
