"""Tests for LangGraph workflow setup (Task 2.13)."""

from __future__ import annotations

import inspect
import os
from typing import Any

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import workflow


def _base_state() -> dict[str, Any]:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": "Response",
        "model_name": "gemini-3.1-flash-lite",
        "claims": [],
        "evidence": [],
        "verified_claims": [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
    }


def test_workflow_compiles():
    assert workflow.workflow is not None


def test_workflow_executes_all_nodes(monkeypatch):
    order: list[str] = []

    def _make_node(name: str):
        def _node(state: dict[str, Any]):
            order.append(name)
            state.setdefault("node_order", []).append(name)
            return state

        return _node

    monkeypatch.setattr(workflow, "extractor", _make_node("extractor"))
    monkeypatch.setattr(workflow, "retriever_node", _make_node("retriever"))
    monkeypatch.setattr(workflow, "verifier_node", _make_node("verifier"))
    monkeypatch.setattr(workflow, "critic_node", _make_node("critic"))
    monkeypatch.setattr(workflow, "judge_node", _make_node("judge"))

    result = workflow.workflow.invoke(_base_state())

    assert order == ["extractor", "retriever", "verifier", "critic", "judge"]
    assert len(result["timeline"]) == 5


def test_workflow_timeline_has_five_entries(monkeypatch):
    def _identity_node(state: dict[str, Any]):
        return state

    monkeypatch.setattr(workflow, "extractor", _identity_node)
    monkeypatch.setattr(workflow, "retriever_node", _identity_node)
    monkeypatch.setattr(workflow, "verifier_node", _identity_node)
    monkeypatch.setattr(workflow, "critic_node", _identity_node)
    monkeypatch.setattr(workflow, "judge_node", _identity_node)

    result = workflow.workflow.invoke(_base_state())

    assert len(result["timeline"]) == 5
    assert [event["agent"] for event in result["timeline"]] == [
        "extractor",
        "retriever",
        "verifier",
        "critic",
        "judge",
    ]


def test_workflow_edge_order(monkeypatch):
    order: list[str] = []

    def _make_node(name: str):
        def _node(state: dict[str, Any]):
            order.append(name)
            return state

        return _node

    monkeypatch.setattr(workflow, "extractor", _make_node("extractor"))
    monkeypatch.setattr(workflow, "retriever_node", _make_node("retriever"))
    monkeypatch.setattr(workflow, "verifier_node", _make_node("verifier"))
    monkeypatch.setattr(workflow, "critic_node", _make_node("critic"))
    monkeypatch.setattr(workflow, "judge_node", _make_node("judge"))

    workflow.workflow.invoke(_base_state())

    assert order == ["extractor", "retriever", "verifier", "critic", "judge"]


def test_workflow_short_circuits_on_extractor_error(monkeypatch):
    order: list[str] = []

    def _extractor(state: dict[str, Any]):
        order.append("extractor")
        state["error"] = "Extractor failed"
        return state

    def _should_not_run(state: dict[str, Any]):
        order.append("downstream")
        return state

    monkeypatch.setattr(workflow, "extractor", _extractor)
    monkeypatch.setattr(workflow, "retriever_node", _should_not_run)
    monkeypatch.setattr(workflow, "verifier_node", _should_not_run)
    monkeypatch.setattr(workflow, "critic_node", _should_not_run)
    monkeypatch.setattr(workflow, "judge_node", _should_not_run)

    result = workflow.workflow.invoke(_base_state())

    assert order == ["extractor"]
    assert result["error"] == "Extractor failed"
    assert result["trust_score"] is None
    assert result["hallucination_risk"] == "UNKNOWN"
    assert [event["agent"] for event in result["timeline"]] == ["extractor"]


def test_workflow_short_circuits_on_retriever_error(monkeypatch):
    order: list[str] = []

    def _extractor(state: dict[str, Any]):
        order.append("extractor")
        return state

    def _retriever(state: dict[str, Any]):
        order.append("retriever")
        state["error"] = "Retriever failed"
        return state

    def _should_not_run(state: dict[str, Any]):
        order.append("downstream")
        return state

    monkeypatch.setattr(workflow, "extractor", _extractor)
    monkeypatch.setattr(workflow, "retriever_node", _retriever)
    monkeypatch.setattr(workflow, "verifier_node", _should_not_run)
    monkeypatch.setattr(workflow, "critic_node", _should_not_run)
    monkeypatch.setattr(workflow, "judge_node", _should_not_run)

    result = workflow.workflow.invoke(_base_state())

    assert order == ["extractor", "retriever"]
    assert result["error"] == "Retriever failed"
    assert result["trust_score"] is None
    assert result["hallucination_risk"] == "UNKNOWN"
    assert [event["agent"] for event in result["timeline"]] == ["extractor", "retriever"]


def test_workflow_error_state_has_none_score(monkeypatch):
    def _extractor(state: dict[str, Any]):
        state["error"] = "Extractor failed"
        return state

    monkeypatch.setattr(workflow, "extractor", _extractor)
    monkeypatch.setattr(workflow, "retriever_node", lambda state: state)
    monkeypatch.setattr(workflow, "verifier_node", lambda state: state)
    monkeypatch.setattr(workflow, "critic_node", lambda state: state)
    monkeypatch.setattr(workflow, "judge_node", lambda state: state)

    result = workflow.workflow.invoke(_base_state())

    assert result["error"] == "Extractor failed"
    assert result["trust_score"] is None
    assert result["hallucination_risk"] == "UNKNOWN"


def test_workflow_partial_timeline_on_error(monkeypatch):
    def _extractor(state: dict[str, Any]):
        return state

    def _retriever(state: dict[str, Any]):
        state["error"] = "Retriever failed"
        return state

    monkeypatch.setattr(workflow, "extractor", _extractor)
    monkeypatch.setattr(workflow, "retriever_node", _retriever)
    monkeypatch.setattr(workflow, "verifier_node", lambda state: state)
    monkeypatch.setattr(workflow, "critic_node", lambda state: state)
    monkeypatch.setattr(workflow, "judge_node", lambda state: state)

    result = workflow.workflow.invoke(_base_state())

    assert [event["agent"] for event in result["timeline"]] == ["extractor", "retriever"]


def test_run_analysis_is_async():
    assert inspect.iscoroutinefunction(workflow.run_analysis)


def test_run_analysis_returns_agent_state(monkeypatch):
    captured_initial_state: dict[str, Any] = {}

    async def _fake_ainvoke(initial_state: dict[str, Any]):
        captured_initial_state.update(initial_state)
        return {
            **initial_state,
            "claims": [{"id": "claim-1"}],
            "timeline": [{"agent": "extractor"}],
        }

    monkeypatch.setattr(workflow.workflow, "ainvoke", _fake_ainvoke)

    result = __import__("asyncio").run(
        workflow.run_analysis(
            analysis_id="analysis-123",
            prompt="Prompt",
            response="Response",
            model_name="gemini-3.1-flash-lite",
        )
    )

    assert result["analysis_id"] == "analysis-123"
    assert result["prompt"] == "Prompt"
    assert result["response"] == "Response"
    assert result["model_name"] == "gemini-3.1-flash-lite"
    assert result["claims"] == [{"id": "claim-1"}]
    assert result["timeline"] == [{"agent": "extractor"}]
    assert captured_initial_state["analysis_id"] == "analysis-123"
    assert captured_initial_state["timeline"] == []


def test_run_analysis_id_preserved(monkeypatch):
    async def _fake_ainvoke(initial_state: dict[str, Any]):
        return {**initial_state, "verdict": "Final verdict"}

    monkeypatch.setattr(workflow.workflow, "ainvoke", _fake_ainvoke)

    result = __import__("asyncio").run(
        workflow.run_analysis(
            analysis_id="analysis-xyz",
            prompt="Prompt",
            response="Response",
            model_name="gemini-3.1-flash-lite",
        )
    )

    assert result["analysis_id"] == "analysis-xyz"
    assert result["verdict"] == "Final verdict"
