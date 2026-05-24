"""Tests for critic agent logical fallacy and quality analysis (Task 2.9)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import critic


class _FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.calls: list[list[dict[str, str]]] = []

    def invoke(self, messages: list[dict[str, str]]):
        self.calls.append(messages)
        return type("LLMResult", (), {"content": self.content})()


def _base_state(response: str, claims: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": response,
        "model_name": "gemini-3.1-flash-lite",
        "claims": claims or [],
        "evidence": [],
        "verified_claims": claims or [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
    }


def test_critic_detects_hasty_generalization(monkeypatch):
    fake_llm = _FakeLLM(
        '{"issues": [{"type": "HASTY_GENERALIZATION", "quote": "All startups fail", "explanation": "It infers a universal claim from limited examples."}], "overall_assessment": "Contains overgeneralization."}'
    )
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(
        _base_state(
            "All startups fail within a year.",
            [{"id": "c1", "text": "All startups fail", "status": "CONTRADICTED"}],
        )
    )

    assert "HASTY_GENERALIZATION" in result["critique"]
    assert "All startups fail" in result["critique"]


def test_critic_empty_issues_valid(monkeypatch):
    fake_llm = _FakeLLM('{"issues": [], "overall_assessment": "No obvious logical fallacies."}')
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(_base_state("A neutral and bounded factual summary."))

    assert "No logical issues detected." in result["critique"]


def test_critic_stores_critique_string(monkeypatch):
    fake_llm = _FakeLLM(
        '{"issues": [{"type": "APPEAL_TO_AUTHORITY", "quote": "Experts say", "explanation": "No primary evidence is cited."}], "overall_assessment": "Some reasoning risks."}'
    )
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(_base_state("Experts say this must be true."))

    assert isinstance(result["critique"], str)
    assert result["critique"].strip()


def test_critic_detects_hedging_language(monkeypatch):
    fake_llm = _FakeLLM('{"issues": [], "overall_assessment": "Mostly cautious language."}')
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(
        _base_state("This treatment might improve outcomes and could reduce costs.")
    )

    assert "LOW_CONFIDENCE_LANGUAGE" in result["critique"]


def test_critic_timeline_entry_added(monkeypatch):
    fake_llm = _FakeLLM('{"issues": [], "overall_assessment": "No major issues."}')
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    state = _base_state("A concise factual answer.")
    result = critic.critique_response(state)

    assert len(result["timeline"]) == 1
    event = result["timeline"][0]
    assert event["agent"] == "critic"
    assert event["started_at"]
    assert event["completed_at"]


def test_critic_output_is_markdown(monkeypatch):
    fake_llm = _FakeLLM(
        '{"issues": [{"type": "HASTY_GENERALIZATION", "quote": "Everyone does this", "explanation": "It extrapolates from a narrow sample."}], "overall_assessment": "Needs stronger evidence."}'
    )
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(_base_state("Everyone does this in all markets."))

    critique = result["critique"]
    assert "## Logical Issues" in critique
    assert "## Overall Assessment" in critique
    assert '"Everyone does this"' in critique


def test_critic_groups_by_issue_type(monkeypatch):
    fake_llm = _FakeLLM(
        """
        {
          "issues": [
            {"type": "HASTY_GENERALIZATION", "quote": "All teams fail", "explanation": "Overgeneralizes from anecdotes."},
            {"type": "HASTY_GENERALIZATION", "quote": "No launch works", "explanation": "Universal statement without support."},
            {"type": "POST_HOC", "quote": "After X, therefore because of X", "explanation": "Assumes causation from sequence."}
          ],
          "overall_assessment": "Multiple logic errors present."
        }
        """
    )
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(_base_state("All teams fail. No launch works. After X, because X."))

    critique = result["critique"]
    assert critique.count("### Hasty Generalization") == 1
    assert '"All teams fail"' in critique
    assert '"No launch works"' in critique
    assert "### Post Hoc" in critique


def test_critic_zero_issues_message(monkeypatch):
    fake_llm = _FakeLLM('{"issues": [], "overall_assessment": "No concerns."}')
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda model_name="gemini-3.1-flash-lite", temperature=0.0: fake_llm,
    )

    result = critic.critique_response(_base_state("This answer only reports measured facts."))

    assert result["critique"] == "No logical issues detected."
