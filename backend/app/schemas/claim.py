"""Pydantic schemas for claim extraction and verification."""

from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ClaimStatus(str, Enum):
    """Enumeration of possible claim verification statuses."""

    SUPPORTED = "SUPPORTED"
    """Claim is fully verified by evidence."""

    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    """Claim is mostly correct but has some inaccuracies or incomplete parts."""

    CONTRADICTED = "CONTRADICTED"
    """Evidence directly contradicts the claim."""

    UNSUPPORTED = "UNSUPPORTED"
    """No evidence found to verify or contradict the claim."""

    UNVERIFIABLE = "UNVERIFIABLE"
    """Claim is definitional, subjective, or about future events."""


class ClaimCreate(BaseModel):
    """Schema for creating a new claim (used by agents before DB persistence)."""

    text: str = Field(
        ..., min_length=1, max_length=2000, description="The claim text to verify"
    )
    """The claim text to verify. Must be non-empty and under 2000 characters."""

    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score from 0 to 1"
    )
    """Initial confidence score from the extraction agent, between 0 and 1."""

    claim_index: int = Field(
        default=0, ge=0, description="Zero-indexed position in the extracted claims list"
    )
    """Zero-indexed position in the extracted claims list."""

    source_span: str | None = Field(
        default=None, description="Optional source text span from the original response"
    )
    """Optional span of text from the original AI response that contains this claim."""


class Claim(ClaimCreate):
    """Schema for a claim with persistence metadata and verification status."""

    id: UUID = Field(..., description="Unique identifier for the claim")
    """Unique identifier assigned to this claim."""

    status: ClaimStatus = Field(
        default=ClaimStatus.UNVERIFIABLE, description="Verification status of the claim"
    )
    """Current verification status: SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, UNSUPPORTED, or UNVERIFIABLE."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "text": "The Earth orbits the Sun",
                "confidence": 0.95,
                "status": "SUPPORTED",
                "claim_index": 0,
                "source_span": "The Earth orbits the Sun every 365 days",
            }
        }
    )
