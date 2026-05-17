"""Typed state schemas shared across LangGraph agent nodes."""

from typing import TypedDict


class TimelineEvent(TypedDict):
    """Single timeline event recorded for an agent execution."""

    agent: str
    started_at: str
    completed_at: str
    input_summary: str
    output_summary: str


class AgentState(TypedDict):
    """Shared workflow state passed between all LangGraph nodes."""

    analysis_id: str
    prompt: str
    response: str
    model_name: str
    claims: list[dict]
    evidence: list[dict]
    verified_claims: list[dict]
    critique: str | None
    trust_score: float | None
    hallucination_risk: str | None
    verdict: str | None
    timeline: list[dict]
    error: str | None