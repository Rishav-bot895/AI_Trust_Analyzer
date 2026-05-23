"""Tests for evidence schemas (Task 1.5)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.evidence import Evidence, EvidenceCreate, EvidencePolarity, EvidenceSource


def _make_evidence_create_data() -> dict:
    """Build valid EvidenceCreate payload for tests."""
    return {
        "claim_id": uuid4(),
        "snippet": "Evidence snippet about a factual statement.",
        "source_url": "https://example.com/source",
        "source_title": "Example Source",
        "relevance_score": 0.83,
        "source_type": EvidenceSource.WEB_SEARCH,
        "polarity": EvidencePolarity.FOR,
        "retrieved_at": datetime.now(timezone.utc),
    }


def test_evidence_valid_construction():
    """Evidence model validates and stores all fields correctly."""
    evidence_id = uuid4()
    claim_id = uuid4()
    retrieved_at = datetime.now(timezone.utc)

    evidence = Evidence(
        id=evidence_id,
        claim_id=claim_id,
        snippet="A valid snippet",
        source_url="https://example.com",
        source_title="Example",
        relevance_score=0.9,
        source_type=EvidenceSource.WEB_SEARCH,
        polarity=EvidencePolarity.FOR,
        retrieved_at=retrieved_at,
    )

    assert evidence.id == evidence_id
    assert evidence.claim_id == claim_id
    assert evidence.snippet == "A valid snippet"
    assert str(evidence.source_url) == "https://example.com/"
    assert evidence.source_title == "Example"
    assert evidence.relevance_score == 0.9
    assert evidence.source_type == EvidenceSource.WEB_SEARCH
    assert evidence.polarity == EvidencePolarity.FOR
    assert evidence.retrieved_at == retrieved_at


def test_evidence_invalid_url_raises():
    """Invalid source_url values should raise ValidationError."""
    data = _make_evidence_create_data()
    data["source_url"] = "not-a-valid-url"

    with pytest.raises(ValidationError):
        EvidenceCreate(**data)


def test_evidence_none_url_allowed():
    """source_url may be None for vector store evidence."""
    data = _make_evidence_create_data()
    data["source_url"] = None
    data["source_type"] = EvidenceSource.PGVECTOR

    evidence = EvidenceCreate(**data)
    assert evidence.source_url is None
    assert evidence.source_type == EvidenceSource.PGVECTOR


def test_evidence_source_enum():
    """EvidenceSource enum exposes expected values."""
    assert {member.value for member in EvidenceSource} == {"WEB_SEARCH", "PGVECTOR"}


def test_evidence_polarity_enum():
    """EvidencePolarity enum exposes expected values."""
    assert {member.value for member in EvidencePolarity} == {"FOR", "AGAINST"}


def test_evidence_polarity_none_allowed():
    """EvidenceCreate should allow null polarity before verification."""
    data = _make_evidence_create_data()
    data["polarity"] = None

    evidence = EvidenceCreate(**data)
    assert evidence.polarity is None