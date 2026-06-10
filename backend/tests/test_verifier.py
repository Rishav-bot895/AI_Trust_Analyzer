"""Tests for verifier agent claim/evidence comparison (Task 2.7)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import verifier


class _FakeLLM:
    def __init__(self, responses: list[Any]):
        self.responses = responses
        self.calls: list[list[dict[str, str]]] = []

    def invoke(self, messages: list[dict[str, str]]):
        self.calls.append(messages)
        content = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        return type("LLMResult", (), {"content": content})()


class _TextOnlyContent:
    def __init__(self, text: str):
        self.text = text


def _base_state(claims: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": "Response",
        "model_name": "gemini-3.1-flash-lite",
        "claims": claims,
        "evidence": evidence,
        "verified_claims": [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
        "verifier_reason_codes": [],
        "verifier_metrics": {},
        "is_guest": True,
        "guest_session_id": "guest-test",
        "user_id": None,
    }


def test_verifier_supported_claim(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"SUPPORTED","evidence_polarities":[{"evidence_id":"22222222-2222-2222-2222-222222222222","polarity":"FOR"}]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Earth orbits the Sun", "confidence": 0.8, "claim_index": 0}],
        evidence=[
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "claim_id": claim_id,
                "snippet": "NASA says Earth orbits the Sun.",
                "source_url": "https://example.com/earth",
                "source_title": "Earth facts",
                "relevance_score": 0.95,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] == "SUPPORTED"
    assert result["evidence"][0]["polarity"] == "FOR"


def test_verifier_partially_supported_claim(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"PARTIALLY_SUPPORTED","evidence_polarities":[{"evidence_index":0,"polarity":"FOR"},{"evidence_index":1,"polarity":"AGAINST"}]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Mars is a planet", "confidence": 0.7, "claim_index": 0}],
        evidence=[
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "claim_id": claim_id,
                "snippet": "Mars is a planet in our solar system.",
                "source_url": "https://example.com/mars-1",
                "source_title": "Mars planet",
                "relevance_score": 0.92,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "claim_id": claim_id,
                "snippet": "Mars has liquid water today.",
                "source_url": "https://example.com/mars-2",
                "source_title": "Mars water",
                "relevance_score": 0.55,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] == "PARTIALLY_SUPPORTED"
    assert [item["polarity"] for item in result["evidence"]] == ["FOR", "AGAINST"]


def test_verifier_contradicted_claim(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"CONTRADICTED","evidence_polarities":[{"evidence_index":0,"polarity":"AGAINST"}]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The moon is made of cheese", "confidence": 0.2, "claim_index": 0}],
        evidence=[
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "claim_id": claim_id,
                "snippet": "Apollo samples show the moon is made of rock.",
                "source_url": "https://example.com/moon",
                "source_title": "Moon facts",
                "relevance_score": 0.99,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] == "CONTRADICTED"
    assert result["evidence"][0]["polarity"] == "AGAINST"


def test_verifier_mixed_polarity_claim_is_not_contradicted(monkeypatch):
    claim_id = "12121212-1212-1212-1212-121212121212"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"CONTRADICTED","evidence_polarities":[{"evidence_index":0,"polarity":"AGAINST"},{"evidence_index":1,"polarity":"FOR"}]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim with mixed evidence", "confidence": 0.4, "claim_index": 0}],
        evidence=[
            {
                "id": "13131313-1313-1313-1313-131313131313",
                "claim_id": claim_id,
                "snippet": "Official records say this is not true.",
                "source_url": "https://example.com/against",
                "source_title": "Against source",
                "relevance_score": 0.95,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "14141414-1414-1414-1414-141414141414",
                "claim_id": claim_id,
                "snippet": "Another source supports part of the claim.",
                "source_url": "https://example.com/for",
                "source_title": "For source",
                "relevance_score": 0.2,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
        ],
    )

    result = verifier.verify_claims(state)

    assert [item["polarity"] for item in result["evidence"]] == ["AGAINST", "FOR"]
    assert result["verified_claims"][0]["status"] == "PARTIALLY_SUPPORTED"


def test_verifier_no_evidence_returns_unsupported(monkeypatch):
    fake_llm = _FakeLLM([])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[
            {"id": "11111111-1111-1111-1111-111111111111", "text": "Claim with no evidence", "confidence": 0.5, "claim_index": 0}
        ],
        evidence=[],
    )

    result = verifier.verify_claims(state)

    assert fake_llm.calls == []
    assert result["verified_claims"][0]["status"] == "UNSUPPORTED"


def test_verifier_invalid_verdict_defaults_to_unverifiable(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(['''{"verdict":"BANANA"}'''])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim with weird verdict", "confidence": 0.5, "claim_index": 0}],
        evidence=[
            {
                "id": "66666666-6666-6666-6666-666666666666",
                "claim_id": claim_id,
                "snippet": "Some unrelated evidence.",
                "source_url": "https://example.com/unrelated",
                "source_title": "Unrelated",
                "relevance_score": 0.4,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] == "UNVERIFIABLE"
    assert result["evidence"][0]["polarity"] == "UNKNOWN"


def test_verifier_classifies_evidence_polarity_for(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(['''{"verdict":"SUPPORTED","evidence_polarities":["FOR"]}'''])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Water is wet", "confidence": 0.9, "claim_index": 0}],
        evidence=[
            {
                "id": "77777777-7777-7777-7777-777777777777",
                "claim_id": claim_id,
                "snippet": "Water is wet.",
                "source_url": "https://example.com/water",
                "source_title": "Water",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["evidence"][0]["polarity"] == "FOR"


def test_verifier_classifies_evidence_polarity_against(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(['''{"verdict":"CONTRADICTED","evidence_polarities":["AGAINST"]}'''])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The Earth is flat", "confidence": 0.1, "claim_index": 0}],
        evidence=[
            {
                "id": "88888888-8888-8888-8888-888888888888",
                "claim_id": claim_id,
                "snippet": "Satellite imagery shows the Earth is round.",
                "source_url": "https://example.com/earth",
                "source_title": "Earth shape",
                "relevance_score": 0.98,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["evidence"][0]["polarity"] == "AGAINST"


def test_verifier_timeline_entry_added(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(['''{"verdict":"SUPPORTED","evidence_polarities":["FOR"]}'''])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The sky is blue", "confidence": 0.9, "claim_index": 0}],
        evidence=[
            {
                "id": "99999999-9999-9999-9999-999999999999",
                "claim_id": claim_id,
                "snippet": "The sky appears blue because of Rayleigh scattering.",
                "source_url": "https://example.com/sky",
                "source_title": "Sky",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert len(result["timeline"]) == 1
    event = result["timeline"][0]
    assert event["agent"] == "verifier"
    assert event["started_at"]
    assert event["completed_at"]


def test_verifier_updates_confidence(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"SUPPORTED","confidence":0.87,"evidence_polarities":["FOR"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The sky is blue", "confidence": 0.12, "claim_index": 0}],
        evidence=[
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "claim_id": claim_id,
                "snippet": "The sky appears blue because of Rayleigh scattering.",
                "source_url": "https://example.com/sky",
                "source_title": "Sky",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert isinstance(result["verified_claims"][0]["confidence"], float)
    assert 0.0 <= result["verified_claims"][0]["confidence"] <= 1.0
    assert result["verified_claims"][0]["confidence"] != 0.12


def test_verifier_clamps_confidence_out_of_range(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"SUPPORTED","confidence":1.3,"evidence_polarities":["FOR"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The sky is blue", "confidence": 0.12, "claim_index": 0}],
        evidence=[
            {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "claim_id": claim_id,
                "snippet": "The sky appears blue because of Rayleigh scattering.",
                "source_url": "https://example.com/sky",
                "source_title": "Sky",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert 0.0 <= result["verified_claims"][0]["confidence"] <= 0.99
    assert result["verified_claims"][0]["confidence"] >= 0.75


def test_verifier_confidence_is_float(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"PARTIALLY_SUPPORTED","confidence":"0.66","evidence_polarities":["FOR"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "The sky is blue", "confidence": 0.12, "claim_index": 0}],
        evidence=[
            {
                "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "claim_id": claim_id,
                "snippet": "The sky appears blue because of Rayleigh scattering.",
                "source_url": "https://example.com/sky",
                "source_title": "Sky",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert isinstance(result["verified_claims"][0]["confidence"], float)
    assert 0.0 <= result["verified_claims"][0]["confidence"] <= 1.0


def test_verifier_records_no_evidence_reason_code(monkeypatch):
    fake_llm = _FakeLLM([])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": "11111111-1111-1111-1111-111111111111", "text": "No evidence claim", "confidence": 0.4, "claim_index": 0}],
        evidence=[],
    )

    result = verifier.verify_claims(state)

    assert "no_evidence" in result["verifier_reason_codes"]
    trace = result["verified_claims"][0]["verification_trace"]
    assert "no_evidence" in trace["reason_codes"]
    assert trace["fallback_reason"] == "no_evidence"


def test_verifier_records_parse_failure_reason_code(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(["not json at all"])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim with parse failure", "confidence": 0.4, "claim_index": 0}],
        evidence=[
            {
                "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "claim_id": claim_id,
                "snippet": "Potentially relevant snippet",
                "source_url": "https://example.com/parse",
                "source_title": "Parse",
                "relevance_score": 0.6,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert "parse_failure" in result["verifier_reason_codes"]
    trace = result["verified_claims"][0]["verification_trace"]
    assert "parse_failure" in trace["reason_codes"]
    assert trace["fallback_reason"] == "json_parse_failed"


def test_verifier_tracks_polarity_source_and_metrics(monkeypatch, caplog):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"SUPPORTED","evidence_polarities":["AGAINST"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim with contradictory polarity", "confidence": 0.7, "claim_index": 0}],
        evidence=[
            {
                "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "claim_id": claim_id,
                "snippet": "Snippet marked as against",
                "source_url": "https://example.com/polarity",
                "source_title": "Polarity",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    with caplog.at_level("INFO"):
        result = verifier.verify_claims(state)

    trace = result["verified_claims"][0]["verification_trace"]
    assert trace["polarity_source"] == "explicit"
    assert trace["polarity_source_counts"]["explicit"] == 1
    assert result["evidence"][0]["polarity"] == "AGAINST"
    assert result["verifier_metrics"]["supported_with_all_against_polarity_count"] == 0
    assert any("verifier_monitoring_metrics" in record.message for record in caplog.records)


def test_verifier_normalizes_list_content_payload(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            [
                {"text": '{"verdict":"SUPPORTED","confidence":0.83,"evidence_polarities":["FOR"]}'},
            ]
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim from list content", "confidence": 0.3, "claim_index": 0}],
        evidence=[
            {
                "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "claim_id": claim_id,
                "snippet": "Official record confirms this claim.",
                "source_url": "https://example.com/list-content",
                "source_title": "List Content",
                "relevance_score": 0.8,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert result["verified_claims"][0]["confidence"] >= 0.5
    assert result["evidence"][0]["polarity"] == "FOR"


def test_verifier_normalizes_dict_content_payload(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            {
                "verdict": "SUPPORTED",
                "confidence": 0.84,
                "evidence_polarities": ["FOR"],
            }
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim from dict content", "confidence": 0.2, "claim_index": 0}],
        evidence=[
            {
                "id": "12341234-1234-1234-1234-123412341234",
                "claim_id": claim_id,
                "snippet": "Official records confirm this claim.",
                "source_url": "https://example.com/dict-content",
                "source_title": "Dict Content",
                "relevance_score": 0.88,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert result["evidence"][0]["polarity"] == "FOR"
    assert "parse_failure" not in result["verifier_reason_codes"]


def test_verifier_normalizes_object_content_payload(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            _TextOnlyContent(
                '{"verdict":"SUPPORTED","confidence":0.82,"evidence_polarities":["FOR"]}'
            )
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Claim from object payload", "confidence": 0.3, "claim_index": 0}],
        evidence=[
            {
                "id": "56785678-5678-5678-5678-567856785678",
                "claim_id": claim_id,
                "snippet": "Authoritative source confirms this statement.",
                "source_url": "https://example.com/object-content",
                "source_title": "Object Content",
                "relevance_score": 0.86,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert result["evidence"][0]["polarity"] == "FOR"
    assert "parse_failure" not in result["verifier_reason_codes"]


def test_verifier_unresolved_verdict_uses_neutral_fallback_polarity(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM([
        '{"verdict":"UNVERIFIABLE","confidence":0.2}'
    ])
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Unresolved claim", "confidence": 0.1, "claim_index": 0}],
        evidence=[
            {
                "id": "90ab90ab-90ab-90ab-90ab-90ab90ab90ab",
                "claim_id": claim_id,
                "snippet": "Evidence is vague and non-committal.",
                "source_url": "https://example.com/unresolved",
                "source_title": "Unresolved",
                "relevance_score": 0.25,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] == "UNVERIFIABLE"
    assert result["evidence"][0]["polarity"] == "UNKNOWN"
    assert result["evidence"][0]["polarity"] != "AGAINST"


def test_verifier_deterministic_sanity_overrides_explicit_polarity(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"SUPPORTED","evidence_polarities":["FOR"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Apollo 13 landed on Mars", "confidence": 0.4, "claim_index": 0}],
        evidence=[
            {
                "id": "abababab-abab-abab-abab-abababababab",
                "claim_id": claim_id,
                "snippet": "Mission logs say Apollo 13 did not land on any planet.",
                "source_url": "https://example.com/apollo13",
                "source_title": "Apollo 13",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    result = verifier.verify_claims(state)

    assert result["evidence"][0]["polarity"] == "AGAINST"
    assert result["evidence"][0]["polarity_source"] == "deterministic"


def test_verifier_guardrail_prevents_unverifiable_with_strong_authority_support(monkeypatch):
    claim_id = "11111111-1111-1111-1111-111111111111"
    fake_llm = _FakeLLM(
        [
            '''{"verdict":"UNVERIFIABLE","confidence":0.2,"evidence_polarities":["FOR","FOR"]}'''
        ]
    )
    monkeypatch.setattr(
        verifier,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state(
        claims=[{"id": claim_id, "text": "Apollo 11 landed on the Moon in 1969", "confidence": 0.2, "claim_index": 0}],
        evidence=[
            {
                "id": "acacacac-acac-acac-acac-acacacacacac",
                "claim_id": claim_id,
                "snippet": "NASA confirms Apollo 11 landed on the Moon in 1969.",
                "source_url": "https://www.nasa.gov/mission/apollo-11/",
                "source_title": "Apollo 11 - NASA",
                "relevance_score": 0.95,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "adadadad-adad-adad-adad-adadadadadad",
                "claim_id": claim_id,
                "snippet": "Official record documented the successful moon landing.",
                "source_url": "https://history.nasa.gov/ap11ann/introduction.htm",
                "source_title": "Apollo 11 archive",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": None,
                "retrieved_at": "2026-01-01T00:00:00Z",
            },
        ],
    )

    result = verifier.verify_claims(state)

    assert result["verified_claims"][0]["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert result["verified_claims"][0]["status"] != "UNVERIFIABLE"
    assert result["verified_claims"][0]["confidence"] >= 0.75