"""Pydantic schemas for retrieved evidence and verification polarity."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class EvidenceSource(str, Enum):
    """Enumeration of evidence source types."""

    WEB_SEARCH = "WEB_SEARCH"
    """Evidence retrieved from web search providers."""

    VECTOR_STORE = "VECTOR_STORE"
    """Evidence retrieved from vector similarity search."""


class EvidencePolarity(str, Enum):
    """Enumeration of evidence polarity after claim verification."""

    FOR = "FOR"
    """Evidence supports the associated claim."""

    AGAINST = "AGAINST"
    """Evidence contradicts the associated claim."""


class EvidenceCreate(BaseModel):
    """Schema for creating evidence before persistence."""

    claim_id: UUID = Field(..., description="Identifier of the claim this evidence belongs to")
    """Identifier of the claim this evidence belongs to."""

    snippet: str = Field(..., min_length=1, description="Evidence snippet text")
    """Short evidence snippet used for verification."""

    source_url: AnyHttpUrl | None = Field(
        default=None,
        description="Source URL when available; may be null for vector store entries",
    )
    """Source URL when available; may be null for vector store entries."""

    source_title: str | None = Field(default=None, description="Optional source title")
    """Optional source title for display in the UI."""

    relevance_score: float = Field(..., description="Relevance score of this evidence")
    """Relevance score from retrieval, typically in the range 0 to 1."""

    source_type: EvidenceSource = Field(..., description="Origin of this evidence")
    """Origin of this evidence: web search or vector store."""

    polarity: EvidencePolarity | None = Field(
        default=None,
        description="Polarity assigned by the verifier: FOR, AGAINST, or null before verification",
    )
    """Polarity assigned by the verifier: FOR, AGAINST, or null before verification."""

    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this evidence was retrieved",
    )
    """Timestamp when this evidence was retrieved."""


class Evidence(EvidenceCreate):
    """Schema for persisted evidence with a unique identifier."""

    id: UUID = Field(..., description="Unique identifier for the evidence item")
    """Unique identifier assigned to this evidence item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "6b76e8d5-4e87-4ce0-aaf0-a0326848116f",
                "claim_id": "550e8400-e29b-41d4-a716-446655440000",
                "snippet": "NASA confirms that Earth orbits the Sun once every year.",
                "source_url": "https://www.nasa.gov/",
                "source_title": "NASA",
                "relevance_score": 0.92,
                "source_type": "WEB_SEARCH",
                "polarity": "FOR",
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        }
    )