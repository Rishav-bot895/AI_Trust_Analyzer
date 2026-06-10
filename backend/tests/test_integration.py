from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from httpx import AsyncClient


def _jwt_for(user_id: str, *, secret: str = "test-supabase-jwt-secret-32bytes-long") -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        secret,
        algorithm="HS256",
    )


async def _submit_and_wait_for_completion(
    async_client: AsyncClient,
    headers: Mapping[str, str],
    *,
    expect_failed: bool = False,
    prompt: str = "Explain the Apollo 11 mission.",
    response: str = "Apollo 11 landed on the Moon in 1969 and returned safely to Earth.",
) -> dict[str, Any]:
    submit_response = await async_client.post(
        "/api/v1/analyze",
        json={
            "prompt": prompt,
            "response": response,
            "model_name": "gemini-3.1-flash-lite",
            "include_comparison": False,
        },
        headers=dict(headers),
    )
    assert submit_response.status_code == 202

    analysis_id = submit_response.json()["id"]
    for _ in range(20):
        poll_response = await async_client.get(
            f"/api/v1/analyze/{analysis_id}",
            headers=dict(headers),
        )
        assert poll_response.status_code == 200
        payload = poll_response.json()
        if payload["status"] == "COMPLETED":
            return payload
        if payload["status"] == "FAILED":
            if expect_failed:
                return payload
            pytest.fail(f"analysis failed unexpectedly: {payload.get('error')}")
        await asyncio.sleep(0.05)

    pytest.fail("analysis did not complete within timeout")


async def _start_guest_session(async_client: AsyncClient) -> dict[str, str]:
    response = await async_client.post("/api/v1/guest/session/start")
    assert response.status_code == 201
    payload = response.json()
    return {
        "X-Guest-Session-Id": payload["guest_session_id"],
        "X-Guest-Session-Token": payload["guest_session_token"],
    }


@pytest.mark.asyncio
async def test_full_pipeline_happy_path(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    assert result["status"] == "COMPLETED"
    assert 0 <= result["trust_score"] <= 100
    assert result["hallucination_risk"] in {"LOW", "MEDIUM", "HIGH"}
    assert result["claims"]
    assert result["evidence"]
    assert isinstance(result["verdict"], str)
    assert result["verdict"].strip()
    assert mock_llm.calls
    assert mock_tavily_client.queries


@pytest.mark.asyncio
async def test_full_pipeline_all_fields_present(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    expected_fields = {
        "id",
        "status",
        "trust_score",
        "hallucination_risk",
        "claims",
        "evidence",
        "critique",
        "verdict",
        "created_at",
        "completed_at",
        "error",
    }
    assert expected_fields.issubset(result.keys())
    assert result["error"] is None
    assert result["completed_at"] is not None
    assert result["critique"] == "No logical issues detected."

    first_claim = result["claims"][0]
    assert {"id", "text", "confidence", "status", "claim_index", "source_span"}.issubset(
        first_claim.keys()
    )
    assert first_claim["status"] == "SUPPORTED"

    first_evidence = result["evidence"][0]
    assert {
        "id",
        "claim_id",
        "snippet",
        "source_url",
        "source_title",
        "relevance_score",
        "source_type",
        "polarity",
        "retrieved_at",
    }.issubset(first_evidence.keys())
    assert first_evidence["polarity"] == "FOR"


@pytest.mark.asyncio
async def test_full_pipeline_timeline_completeness(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    timeline_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/timeline",
        headers=auth_headers,
    )
    assert timeline_response.status_code == 200

    timeline = timeline_response.json()
    assert [event["agent"] for event in timeline] == [
        "extractor",
        "retriever",
        "verifier",
        "critic",
        "judge",
    ]
    assert len(timeline) == 5
    assert all(event["started_at"] for event in timeline)
    assert all(event["completed_at"] for event in timeline)
    assert all(event["input_summary"] for event in timeline)
    assert all(event["output_summary"] for event in timeline)


@pytest.mark.asyncio
async def test_empty_prompt_returns_422(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await async_client.post(
        "/api/v1/analyze",
        json={
            "prompt": "",
            "response": "Apollo 11 landed on the Moon in 1969.",
            "model_name": "gemini-3.1-flash-lite",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_llm_rate_limit_sets_failed_status(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RaisingLLM:
        def invoke(self, _: object) -> object:
            raise RuntimeError("RateLimitError: model quota exceeded")

    raising_llm = RaisingLLM()
    for path in (
        "app.agents.base.get_llm",
        "app.agents.claim_extractor.get_llm",
        "app.agents.verifier.get_llm",
        "app.agents.critic.get_llm",
        "app.agents.judge.get_llm",
    ):
        monkeypatch.setattr(path, lambda *_, **__: raising_llm)

    result = await _submit_and_wait_for_completion(
        async_client,
        auth_headers,
        expect_failed=True,
    )

    assert result["status"] == "FAILED"
    assert "RateLimitError" in (result["error"] or "")
    assert result["trust_score"] is None


@pytest.mark.asyncio
async def test_no_evidence_completes_without_crash(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # noqa: ANN001
    class EmptyTavilyClient:
        def search(self, query: str, max_results: int = 3) -> dict[str, list[dict[str, Any]]]:
            return {"results": []}

    monkeypatch.setattr("app.agents.retriever._get_tavily_client", lambda: EmptyTavilyClient())

    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    assert result["status"] == "COMPLETED"
    assert result["claims"]
    assert result["evidence"] == []
    assert result["claims"][0]["status"] == "UNSUPPORTED"
    assert 0 <= result["trust_score"] <= 100


@pytest.mark.asyncio
async def test_unknown_id_returns_404(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await async_client.get(
        "/api/v1/analyze/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trust_score_within_bounds(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    assert isinstance(result["trust_score"], int | float)
    assert 0 <= result["trust_score"] <= 100


@pytest.mark.asyncio
async def test_authenticated_user_cannot_access_another_users_analysis(
    async_client: AsyncClient,
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    owner_headers = {"Authorization": f"Bearer {_jwt_for('owner-user')}"}
    other_headers = {"Authorization": f"Bearer {_jwt_for('other-user')}"}

    result = await _submit_and_wait_for_completion(async_client, owner_headers)
    response = await async_client.get(f"/api/v1/analyze/{result['id']}", headers=other_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_guest_user_cannot_access_another_guest_sessions_analysis(
    async_client: AsyncClient,
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    guest_a = await _start_guest_session(async_client)
    guest_b = await _start_guest_session(async_client)

    result = await _submit_and_wait_for_completion(async_client, guest_a)
    response = await async_client.get(f"/api/v1/analyze/{result['id']}", headers=guest_b)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_guest_session_cleanup_deletes_claims_evidence_and_history(
    async_client: AsyncClient,
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    guest_headers = await _start_guest_session(async_client)
    result = await _submit_and_wait_for_completion(async_client, guest_headers)

    claims_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/claims",
        headers=guest_headers,
    )
    evidence_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/evidence",
        headers=guest_headers,
    )
    assert claims_response.status_code == 200
    assert evidence_response.status_code == 200
    assert claims_response.json()
    assert evidence_response.json()

    end_response = await async_client.post(
        "/api/v1/guest/session/end",
        json={"guest_session_id": guest_headers["X-Guest-Session-Id"]},
        headers={"X-Guest-Session-Token": guest_headers["X-Guest-Session-Token"]},
    )
    assert end_response.status_code == 202
    assert end_response.json()["deleted_analyses"] == 1

    deleted_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}",
        headers=guest_headers,
    )
    assert deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_analysis_payload_contract_uses_snake_case(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    mock_llm,
    mock_tavily_client,
) -> None:  # noqa: ANN001
    result = await _submit_and_wait_for_completion(async_client, auth_headers)

    claims_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/claims",
        headers=auth_headers,
    )
    evidence_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/evidence",
        headers=auth_headers,
    )
    timeline_response = await async_client.get(
        f"/api/v1/analyze/{result['id']}/timeline",
        headers=auth_headers,
    )

    assert "trust_score" in result
    assert "trustScore" not in result

    claim = claims_response.json()[0]
    assert "claim_index" in claim
    assert "source_span" in claim
    assert "claimIndex" not in claim

    evidence = evidence_response.json()[0]
    assert "claim_id" in evidence
    assert "source_url" in evidence
    assert "sourceUrl" not in evidence

    timeline = timeline_response.json()[0]
    assert "started_at" in timeline
    assert "completed_at" in timeline
    assert "startedAt" not in timeline


@pytest.mark.asyncio
async def test_supabase_jwt_validation_rejects_invalid_signature_and_accepts_valid_token(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    valid_response = await async_client.get(
        "/api/v1/analyze/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    invalid_response = await async_client.get(
        "/api/v1/analyze/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {_jwt_for('test-user-id', secret='wrong-secret')}"},
    )

    assert valid_response.status_code == 404
    assert invalid_response.status_code == 401
