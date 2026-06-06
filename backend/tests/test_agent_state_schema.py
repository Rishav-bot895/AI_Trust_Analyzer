"""Tests for agent state typed schemas (Task 1.7)."""

from app.schemas.agent_state import AgentState, TimelineEvent


def test_agent_state_typeddict_keys():
    """AgentState exposes exactly the required workflow keys."""
    expected_keys = {
        "analysis_id",
        "prompt",
        "response",
        "model_name",
        "claims",
        "evidence",
        "verified_claims",
        "critique",
        "trust_score",
        "hallucination_risk",
        "verdict",
        "timeline",
        "error",
        "verifier_reason_codes",
        "verifier_metrics",
    }

    assert set(AgentState.__annotations__.keys()) == expected_keys
    assert AgentState.__required_keys__ == expected_keys


def test_timeline_event_structure():
    """TimelineEvent schema includes all expected event fields."""
    expected_keys = {
        "agent",
        "started_at",
        "completed_at",
        "input_summary",
        "output_summary",
    }

    assert set(TimelineEvent.__annotations__.keys()) == expected_keys
    assert TimelineEvent.__required_keys__ == expected_keys

    event: TimelineEvent = {
        "agent": "extractor",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:00:01Z",
        "input_summary": "Input response text",
        "output_summary": "Extracted 3 claims",
    }

    assert event["agent"] == "extractor"