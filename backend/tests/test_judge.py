"""Tests for judge agent trust score calculation (Task 2.11)."""

from __future__ import annotations

import os
from typing import Any

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import judge


class _FakeLLM:
    def __init__(self, content: str = "Verdict sentence one. Verdict sentence two."):
        self.content = content

    def invoke(self, messages: list[dict[str, str]]):
        return type("LLMResult", (), {"content": self.content})()


@pytest.fixture(autouse=True)
def _mock_judge_llm(monkeypatch):
    monkeypatch.setattr(
        judge,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: _FakeLLM(),
    )


def _base_state(
    verified_claims: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None = None,
    critique: str | None = None,
) -> dict[str, Any]:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": "Response",
        "model_name": "gemini-3.1-flash-lite",
        "claims": verified_claims,
        "evidence": evidence or [],
        "verified_claims": verified_claims,
        "critique": critique,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
    }


def test_judge_all_supported_high_score():
    claims = [
        {"id": "c1", "text": "A", "status": "SUPPORTED"},
        {"id": "c2", "text": "B", "status": "SUPPORTED"},
    ]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert result["trust_score"] >= 95


def test_judge_all_partially_supported_mid_score():
    claims = [
        {"id": "c1", "text": "A", "status": "PARTIALLY_SUPPORTED"},
        {"id": "c2", "text": "B", "status": "PARTIALLY_SUPPORTED"},
    ]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert result["trust_score"] == 65


def test_judge_all_contradicted_low_score():
    claims = [
        {"id": "c1", "text": "A", "status": "CONTRADICTED"},
        {"id": "c2", "text": "B", "status": "CONTRADICTED"},
    ]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert result["trust_score"] <= 5


def test_judge_score_clamped_to_0_100():
    claims = [{"id": "c1", "text": "A", "status": "SUPPORTED"}]
    evidence = [
        {"id": f"e{i}", "claim_id": "c1", "polarity": "FOR"}
        for i in range(1, 40)
    ]

    result_high = judge.judge_analysis(_base_state(claims, evidence=evidence, critique="No logical issues detected."))
    assert result_high["trust_score"] == 100

    low_critique = "## Logical Issues\n" + "\n".join(
        [f'- "q{i}" - bad logic' for i in range(30)]
    ) + "\n\n## Overall Assessment\nvery poor"
    result_low = judge.judge_analysis(_base_state(claims, critique=low_critique))
    assert result_low["trust_score"] == 0


def test_judge_critic_penalty_applied():
    claims = [{"id": "c1", "text": "A", "status": "SUPPORTED"}]
    critique = (
        "## Logical Issues\n"
        '- "Quote 1" - issue one\n'
        '- "Quote 2" - issue two\n'
        "\n## Overall Assessment\nProblems found."
    )

    result = judge.judge_analysis(_base_state(claims, critique=critique))

    assert result["trust_score"] == 90


def test_judge_single_unsupported_claim():
    claims = [{"id": "c1", "text": "A", "status": "UNSUPPORTED"}]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert result["trust_score"] == 40


def test_judge_evidence_polarity_boosts_supported():
    claims = [{"id": "c1", "text": "A", "status": "SUPPORTED"}]
    evidence = [
        {"id": "e1", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e2", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e3", "claim_id": "c1", "polarity": "FOR"},
    ]

    result = judge.judge_analysis(_base_state(claims, evidence=evidence, critique="No logical issues detected."))

    assert result["trust_score"] == 100


def test_judge_evidence_polarity_reduces_contradicted():
    claims = [{"id": "c1", "text": "A", "status": "CONTRADICTED"}]
    evidence = [
        {"id": "e1", "claim_id": "c1", "polarity": "AGAINST"},
        {"id": "e2", "claim_id": "c1", "polarity": "AGAINST"},
        {"id": "e3", "claim_id": "c1", "polarity": "AGAINST"},
    ]

    result = judge.judge_analysis(_base_state(claims, evidence=evidence, critique="No logical issues detected."))

    assert result["trust_score"] == 0


def test_judge_mixed_evidence_counts_toward_partial_support():
    claims = [{"id": "c1", "text": "A", "status": "PARTIALLY_SUPPORTED"}]
    evidence = [
        {"id": "e1", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e2", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e3", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e4", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e5", "claim_id": "c1", "polarity": "FOR"},
        {"id": "e6", "claim_id": "c1", "polarity": "AGAINST"},
    ]

    result = judge.judge_analysis(_base_state(claims, evidence=evidence, critique="No logical issues detected."))

    assert result["trust_score"] == 67


def test_judge_risk_low_threshold():
    claims = [{"id": "c1", "text": "A", "status": "SUPPORTED"}]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert result["trust_score"] == 100
    assert result["hallucination_risk"] == "LOW"


def test_judge_risk_high_threshold():
    claims = [{"id": "c1", "text": "A", "status": "UNSUPPORTED"}]
    critique = (
        "## Logical Issues\n"
        '- "Issue 1" - detail\n'
        '- "Issue 2" - detail\n'
        "\n## Overall Assessment\nPoor reliability."
    )

    result = judge.judge_analysis(_base_state(claims, critique=critique))

    assert result["trust_score"] == 30
    assert result["hallucination_risk"] == "HIGH"


def test_judge_verdict_non_empty():
    claims = [{"id": "c1", "text": "A", "status": "PARTIALLY_SUPPORTED"}]

    result = judge.judge_analysis(_base_state(claims, critique="No logical issues detected."))

    assert isinstance(result["verdict"], str)
    assert result["verdict"].strip()


def test_judge_timeline_entry_added():
    claims = [{"id": "c1", "text": "A", "status": "SUPPORTED"}]

    state = _base_state(claims, critique="No logical issues detected.")
    result = judge.judge_analysis(state)

    assert len(result["timeline"]) == 1
    event = result["timeline"][0]
    assert event["agent"] == "judge"
    assert event["started_at"]
    assert event["completed_at"]
