"""Pydantic schemas for analysis API requests and responses."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .claim import Claim
from .evidence import Evidence


class AnalysisStatus(str, Enum):
    """Enumeration of analysis lifecycle statuses."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisRequest(BaseModel):
    """Request payload sent by the frontend to start an analysis."""

    prompt: str = Field(
        ..., min_length=1, max_length=2000, description="Original user prompt"
    )
    """Original user prompt text, required and capped at 2000 characters."""

    response: str = Field(
        ..., min_length=1, max_length=10000, description="AI-generated response to analyze"
    )
    """AI-generated response text, required and capped at 10000 characters."""

    model_name: str = Field(
        default="gpt-4o-mini", description="Model used for analysis execution"
    )
    """Model used to run the analysis pipeline."""

    include_comparison: bool = Field(
        default=False, description="Whether to include multi-model comparison"
    )
    """Whether to include model comparison in the analysis workflow."""


class AnalysisResponse(BaseModel):
    """Full analysis response returned by polling and detail endpoints."""

    id: UUID = Field(..., description="Unique identifier for the analysis")
    """Unique identifier for the analysis."""

    status: AnalysisStatus = Field(..., description="Current analysis execution status")
    """Current analysis execution status."""

    trust_score: float | None = Field(
        default=None, description="Overall trust score in the range 0-100"
    )
    """Overall trust score in the range 0-100 when completed."""

    hallucination_risk: str | None = Field(
        default=None, description="Categorical hallucination risk label"
    )
    """Categorical hallucination risk label derived from trust score."""

    claims: list[Claim] = Field(default_factory=list, description="Extracted claims")
    """Extracted and verified claims for this analysis."""

    evidence: list[Evidence] = Field(
        default_factory=list, description="Retrieved evidence items"
    )
    """Retrieved evidence items linked to claims."""

    critique: str | None = Field(
        default=None, description="Critic agent narrative assessment"
    )
    """Critic agent narrative assessment."""

    verdict: str | None = Field(
        default=None, description="Final judge verdict summary"
    )
    """Final judge verdict summary."""

    created_at: datetime = Field(..., description="Timestamp when analysis was created")
    """Timestamp when analysis was created."""

    completed_at: datetime | None = Field(
        default=None, description="Timestamp when analysis completed"
    )
    """Timestamp when analysis completed, if finished."""

    error: str | None = Field(default=None, description="Error message when analysis fails")
    """Error message when analysis fails."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "COMPLETED",
                "trust_score": 81.0,
                "hallucination_risk": "LOW",
                "claims": [],
                "evidence": [],
                "critique": "No major logical issues detected.",
                "verdict": "The response appears mostly trustworthy.",
                "created_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:00:03Z",
                "error": None,
            }
        }
    )


class AnalysisListItem(BaseModel):
    """Summary analysis model used for list endpoints without nested payloads."""

    id: UUID = Field(..., description="Unique identifier for the analysis")
    """Unique identifier for the analysis."""

    status: AnalysisStatus = Field(..., description="Current analysis execution status")
    """Current analysis execution status."""

    trust_score: float | None = Field(
        default=None, description="Overall trust score in the range 0-100"
    )
    """Overall trust score in the range 0-100 when completed."""

    hallucination_risk: str | None = Field(
        default=None, description="Categorical hallucination risk label"
    )
    """Categorical hallucination risk label derived from trust score."""

    created_at: datetime = Field(..., description="Timestamp when analysis was created")
    """Timestamp when analysis was created."""

    completed_at: datetime | None = Field(
        default=None, description="Timestamp when analysis completed"
    )
    """Timestamp when analysis completed, if finished."""

    error: str | None = Field(default=None, description="Error message when analysis fails")
    """Error message when analysis fails."""