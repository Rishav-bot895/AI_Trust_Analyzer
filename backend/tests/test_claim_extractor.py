"""Tests for claim extractor agent (Task 2.2)."""

from __future__ import annotations

import os
from uuid import UUID

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import claim_extractor


class _FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.captured_messages = None

    def invoke(self, messages):
        self.captured_messages = messages
        return _FakeLLMResponse(self.content)


def _base_state(response: str) -> dict:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": response,
        "model_name": "gemini-3.1-flash-lite",
        "claims": [],
        "evidence": [],
        "verified_claims": [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
    }


def test_extractor_extracts_claims(monkeypatch):
    """Given factual text, extractor returns parsed claims with confidence values."""
    fake_json = (
        '{"claims": ['
        '{"text": "Water boils at 100C at sea level", "confidence": 0.98}, '
        '{"text": "The moon orbits Earth", "confidence": 0.95}, '
        '{"text": "Paris is in France", "confidence": 0.99}'
        ']}'
    )
    fake_llm = _FakeLLM(fake_json)
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state(
        "Water boils at 100C at sea level. The moon orbits Earth. Paris is in France."
    )
    result = claim_extractor.extract_claims(state)

    assert len(result["claims"]) >= 3
    assert all(isinstance(claim["text"], str) and claim["text"] for claim in result["claims"])
    assert all(isinstance(claim["confidence"], float) for claim in result["claims"])


def test_extractor_empty_response_returns_empty_list(monkeypatch):
    """Empty response should skip LLM call and return an empty claims list."""

    monkeypatch.setattr(
        claim_extractor,
        "get_llm",
        lambda model_name: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    state = _base_state("   ")
    result = claim_extractor.extract_claims(state)

    assert result["claims"] == []


def test_extractor_opinion_only_returns_empty(monkeypatch):
    """Opinion-only input should be allowed to return no claims without error."""
    fake_llm = _FakeLLM('{"claims": []}')
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state("I think this is great and probably the best approach.")
    result = claim_extractor.extract_claims(state)

    assert result["claims"] == []
    assert result["error"] is None


def test_extractor_timeline_entry_added(monkeypatch):
    """Timed decorator should record a timeline entry for claim_extractor."""
    fake_llm = _FakeLLM('{"claims": [{"text": "A factual claim", "confidence": 0.9}]}')
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state("A factual claim.")
    result = claim_extractor.extract_claims(state)

    assert len(result["timeline"]) == 1
    event = result["timeline"][0]
    assert event["agent"] == "claim_extractor"
    assert event["started_at"]
    assert event["completed_at"]


def test_extractor_assigns_uuids(monkeypatch):
    """Extractor should assign a UUID string to every valid claim."""
    fake_llm = _FakeLLM(
        '{"claims": ['
        '{"text": "Fact A", "confidence": 0.91}, '
        '{"text": "Fact B", "confidence": 0.88}'
        ']}'
    )
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state("Fact A. Fact B.")
    result = claim_extractor.extract_claims(state)

    assert len(result["claims"]) == 2
    for claim in result["claims"]:
        UUID(claim["id"])


def test_extractor_truncates_at_max_claims(monkeypatch):
    """Extractor should truncate claims to settings.MAX_CLAIMS."""
    fake_llm = _FakeLLM(
        '{"claims": ['
        '{"text": "Fact 1", "confidence": 0.9}, '
        '{"text": "Fact 2", "confidence": 0.9}, '
        '{"text": "Fact 3", "confidence": 0.9}'
        ']}'
    )
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)
    monkeypatch.setattr(claim_extractor.settings, "MAX_CLAIMS", 2)

    state = _base_state("Fact 1. Fact 2. Fact 3.")
    result = claim_extractor.extract_claims(state)

    assert len(result["claims"]) == 2


def test_extractor_malformed_json_sets_error(monkeypatch):
    """Malformed model output should set state['error'] instead of raising."""
    fake_llm = _FakeLLM("```json\nnot-json\n```")
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state("Some response text")
    result = claim_extractor.extract_claims(state)

    assert result["claims"] == []
    assert isinstance(result["error"], str)
    assert result["error"].startswith("Claim extraction failed:")


def test_extractor_validates_confidence_range(monkeypatch):
    """Claims with confidence outside 0..1 should be dropped by schema validation."""
    fake_llm = _FakeLLM(
        '{"claims": ['
        '{"text": "Invalid confidence", "confidence": 1.5}, '
        '{"text": "Valid confidence", "confidence": 0.75}'
        ']}'
    )
    monkeypatch.setattr(claim_extractor, "get_llm", lambda model_name: fake_llm)

    state = _base_state("Invalid confidence. Valid confidence.")
    result = claim_extractor.extract_claims(state)

    assert len(result["claims"]) == 1
    assert result["claims"][0]["text"] == "Valid confidence"
    assert result["claims"][0]["confidence"] == 0.75
