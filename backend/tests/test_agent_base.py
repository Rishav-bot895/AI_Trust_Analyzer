"""Tests for shared agent utilities (Task 2.1)."""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import base


def test_get_llm_returns_correct_model(monkeypatch: pytest.MonkeyPatch):
    """get_llm should construct ChatGoogleGenerativeAI with requested model."""

    captured: dict[str, object] = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(base, "ChatGoogleGenerativeAI", FakeChatGoogleGenerativeAI)
    monkeypatch.setattr(base.settings, "GEMINI_API_KEY", "fake-key")

    llm = base.get_llm(model_name="gemini-3.1-flash-lite", temperature=0.2)

    assert isinstance(llm, FakeChatGoogleGenerativeAI)
    assert captured["model"] == "gemini-3.1-flash-lite"
    assert captured["temperature"] == 0.2
    assert captured["google_api_key"] == "fake-key"


def test_timed_agent_adds_timeline_entry():
    """timed_agent decorator should add one timeline event with timestamps."""

    @base.timed_agent("extractor")
    def run_agent(state: dict):
        state["claims"] = [{"text": "Example"}]
        return state

    state = {"timeline": [], "claims": []}
    result = run_agent(state)

    assert result is state
    assert len(state["timeline"]) == 1

    event = state["timeline"][0]
    assert event["agent"] == "extractor"
    assert isinstance(event["started_at"], str)
    assert isinstance(event["completed_at"], str)
    assert event["started_at"] != ""
    assert event["completed_at"] != ""


def test_parse_json_response_strips_fences():
    """parse_json_response should remove markdown fences and parse JSON."""

    payload = """```json
{"claims": [{"text": "A"}]}
```"""

    parsed = base.parse_json_response(payload)

    assert isinstance(parsed, dict)
    assert parsed["claims"][0]["text"] == "A"


def test_parse_json_response_invalid_raises():
    """Invalid JSON should raise ValueError/JSONDecodeError from parser."""

    with pytest.raises((json.JSONDecodeError, ValueError)):
        base.parse_json_response("```json\nnot-json\n```")
