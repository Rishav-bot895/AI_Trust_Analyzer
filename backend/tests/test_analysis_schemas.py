"""Tests for analysis schemas (Task 1.6)."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
)
from app.schemas.claim import Claim, ClaimStatus
from app.schemas.evidence import Evidence, EvidencePolarity, EvidenceSource


def _sample_claim() -> Claim:
    """Create a valid sample claim for nested response tests."""
    return Claim(
        id=uuid4(),
        text="The Earth orbits the Sun.",
        confidence=0.93,
        status=ClaimStatus.SUPPORTED,
        claim_index=0,
        source_span="The Earth orbits the Sun every year.",
    )


def _sample_evidence(claim_id):
    """Create a valid sample evidence item for nested response tests."""
    return Evidence(
        id=uuid4(),
        claim_id=claim_id,
        snippet="NASA states Earth revolves around the Sun.",
        source_url="https://www.nasa.gov/",
        source_title="NASA",
        relevance_score=0.95,
        source_type=EvidenceSource.WEB_SEARCH,
        polarity=EvidencePolarity.FOR,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_analysis_request_empty_prompt_raises():
    """Empty prompt should fail request validation."""
    with pytest.raises(ValidationError):
        AnalysisRequest(prompt="", response="Valid response")


def test_analysis_request_response_too_long_raises():
    """Response longer than 10000 chars should fail validation."""
    with pytest.raises(ValidationError):
        AnalysisRequest(prompt="Valid prompt", response="x" * 10001)


def test_analysis_request_default_model_name():
    """Default model name should align with Gemini architecture baseline."""
    request = AnalysisRequest(prompt="Valid prompt", response="Valid response")
    assert request.model_name == "gemini-3.1-flash-lite"


def test_analysis_response_serializes_nested():
    """AnalysisResponse should serialize nested Claim and Evidence models."""
    claim = _sample_claim()
    evidence = _sample_evidence(claim.id)

    response = AnalysisResponse(
        id=uuid4(),
        status=AnalysisStatus.COMPLETED,
        trust_score=88.0,
        hallucination_risk="LOW",
        claims=[claim],
        evidence=[evidence],
        critique="No major logical issues found.",
        verdict="The answer is reliable.",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        error=None,
    )

    payload = json.loads(response.model_dump_json())

    assert payload["status"] == "COMPLETED"
    assert payload["trust_score"] == 88.0
    assert len(payload["claims"]) == 1
    assert payload["claims"][0]["text"] == claim.text
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["claim_id"] == str(claim.id)
    assert payload["evidence"][0]["source_type"] == "WEB_SEARCH"
    assert payload["evidence"][0]["polarity"] == "FOR"


def test_analysis_status_enum():
    """AnalysisStatus enum should expose expected values."""
    assert {status.value for status in AnalysisStatus} == {
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
    }


def test_analysis_response_serializes_pgvector_evidence():
    """AnalysisResponse nested evidence should preserve PGVECTOR source type."""
    claim = _sample_claim()
    evidence = Evidence(
        id=uuid4(),
        claim_id=claim.id,
        snippet="Local vector match snippet",
        source_url=None,
        source_title="Vector KB",
        relevance_score=0.77,
        source_type=EvidenceSource.PGVECTOR,
        polarity=None,
        retrieved_at=datetime.now(timezone.utc),
    )

    response = AnalysisResponse(
        id=uuid4(),
        status=AnalysisStatus.COMPLETED,
        trust_score=61.0,
        hallucination_risk="MEDIUM",
        claims=[claim],
        evidence=[evidence],
        critique="Mixed support from retrieval.",
        verdict="Partially reliable.",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        error=None,
    )

    payload = json.loads(response.model_dump_json())

    assert payload["evidence"][0]["source_type"] == "PGVECTOR"
    assert payload["evidence"][0]["source_url"] is None