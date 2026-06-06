from __future__ import annotations

import logging
from typing import Any, Callable, cast

from langgraph.graph import END, StateGraph

from app.agents import claim_extractor, critic, judge, retriever, verifier
from app.agents.base import timed_agent
from app.schemas.agent_state import AgentState


logger = logging.getLogger(__name__)


def _unwrap_agent(func: Callable[[AgentState], AgentState]) -> Callable[[AgentState], AgentState]:
    return cast(Callable[[AgentState], AgentState], getattr(func, "__wrapped__", func))


def _apply_error_defaults(state: AgentState) -> AgentState:
    if state.get("error"):
        state["trust_score"] = None
        state["hallucination_risk"] = "UNKNOWN"
    return state


# Default node callables reference the underlying unwrapped implementations so the
# graph can be monkeypatched in tests without double-recording timeline entries.
extractor = _unwrap_agent(claim_extractor.extract_claims)
retriever_node = _unwrap_agent(retriever.retrieve_evidence)
verifier_node = _unwrap_agent(verifier.verify_claims)
critic_node = _unwrap_agent(critic.critique_response)
judge_node = _unwrap_agent(judge.judge_analysis)


@timed_agent("extractor")
def _extractor_node(state: AgentState) -> AgentState:
    return _apply_error_defaults(extractor(state))


@timed_agent("retriever")
def _retriever_node(state: AgentState) -> AgentState:
    return _apply_error_defaults(retriever_node(state))


@timed_agent("verifier")
def _verifier_node(state: AgentState) -> AgentState:
    return _apply_error_defaults(verifier_node(state))


@timed_agent("critic")
def _critic_node(state: AgentState) -> AgentState:
    return _apply_error_defaults(critic_node(state))


@timed_agent("judge")
def _judge_node(state: AgentState) -> AgentState:
    return _apply_error_defaults(judge_node(state))


def check_error(state: AgentState) -> str:
    """Route to END when an upstream node has set an error."""
    if state.get("error"):
        timeline = state.get("timeline") or []
        triggering_agent = "unknown"
        if isinstance(timeline, list) and timeline:
            last_event = timeline[-1]
            if isinstance(last_event, dict):
                triggering_agent = str(last_event.get("agent") or "unknown")

        logger.error("Workflow stopped after %s: %s", triggering_agent, state.get("error"))
        state["trust_score"] = None
        state["hallucination_risk"] = "UNKNOWN"
        return "end"

    return "continue"


graph = StateGraph(AgentState)
graph.add_node("extractor", _extractor_node)
graph.add_node("retriever", _retriever_node)
graph.add_node("verifier", _verifier_node)
graph.add_node("critic", _critic_node)
graph.add_node("judge", _judge_node)

graph.add_conditional_edges(
    "extractor",
    check_error,
    {
        "continue": "retriever",
        "end": END,
    },
)
graph.add_conditional_edges(
    "retriever",
    check_error,
    {
        "continue": "verifier",
        "end": END,
    },
)
graph.add_conditional_edges(
    "verifier",
    check_error,
    {
        "continue": "critic",
        "end": END,
    },
)
graph.add_conditional_edges(
    "critic",
    check_error,
    {
        "continue": "judge",
        "end": END,
    },
)
graph.add_conditional_edges(
    "judge",
    check_error,
    {
        "continue": END,
        "end": END,
    },
)
graph.set_entry_point("extractor")

workflow = graph.compile()


def build_initial_state(
    analysis_id: str,
    prompt: str,
    response: str,
    model_name: str,
) -> AgentState:
    return {
        "analysis_id": analysis_id,
        "prompt": prompt,
        "response": response,
        "model_name": model_name,
        "claims": [],
        "evidence": [],
        "verified_claims": [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
        "verifier_reason_codes": [],
        "verifier_metrics": {},
    }


async def run_analysis(
    analysis_id: str,
    prompt: str,
    response: str,
    model_name: str,
) -> AgentState:
    """Run the full five-node workflow asynchronously and return the final state."""
    initial_state = build_initial_state(analysis_id, prompt, response, model_name)
    final_state = await workflow.ainvoke(initial_state)
    return cast(AgentState, final_state)
