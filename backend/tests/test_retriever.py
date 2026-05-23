"""Tests for retriever agent Tavily integration (Task 2.4)."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.agents import retriever


class _FakeTavilyClient:
    def __init__(self, responses_by_query: dict[str, Any], failing_queries: set[str] | None = None):
        self.responses_by_query = responses_by_query
        self.failing_queries = failing_queries or set()
        self.calls: list[dict[str, Any]] = []

    def search(self, query: str, max_results: int):
        self.calls.append({"query": query, "max_results": max_results})
        if query in self.failing_queries:
            raise RuntimeError("Tavily temporary failure")
        return self.responses_by_query.get(query, {"results": []})


def _base_state(claims: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "analysis_id": "a1",
        "prompt": "Prompt",
        "response": "Response",
        "model_name": "gemini-3.1-flash-lite",
        "claims": claims,
        "evidence": [],
        "verified_claims": [],
        "critique": None,
        "trust_score": None,
        "hallucination_risk": None,
        "verdict": None,
        "timeline": [],
        "error": None,
    }


def test_retriever_calls_tavily_per_claim(monkeypatch):
    """Retriever should perform one Tavily search per claim with max_results=3."""
    claims = [
        {"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"},
        {"id": "22222222-2222-2222-2222-222222222222", "text": "Claim B"},
        {"id": "33333333-3333-3333-3333-333333333333", "text": "Claim C"},
    ]
    fake_client = _FakeTavilyClient(
        {
            "Claim A": {"results": []},
            "Claim B": {"results": []},
            "Claim C": {"results": []},
        }
    )
    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)

    state = _base_state(claims)
    retriever.retrieve_evidence(state)

    assert len(fake_client.calls) == 3
    assert all(call["max_results"] == 3 for call in fake_client.calls)


def test_retriever_maps_tavily_result_to_evidence(monkeypatch):
    """Retriever should map Tavily search results to EvidenceCreate-shaped dicts."""
    claim_id = "11111111-1111-1111-1111-111111111111"
    claims = [{"id": claim_id, "text": "Water boils at 100C"}]
    fake_client = _FakeTavilyClient(
        {
            "Water boils at 100C": {
                "results": [
                    {
                        "content": "At sea level, water boils at around 100C.",
                        "url": "https://example.com/water",
                        "title": "Water boiling point",
                        "score": 0.91,
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(result["evidence"]) == 1
    item = result["evidence"][0]
    assert item["claim_id"] == claim_id
    assert item["snippet"] == "At sea level, water boils at around 100C."
    assert item["source_url"] == "https://example.com/water"
    assert item["source_title"] == "Water boiling point"
    assert item["relevance_score"] == 0.91
    assert item["source_type"] == "WEB_SEARCH"
    assert item["polarity"] is None
    assert item["retrieved_at"]


def test_retriever_partial_failure_continues(monkeypatch):
    """A Tavily failure on one claim should not stop retrieval for other claims."""
    claims = [
        {"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"},
        {"id": "22222222-2222-2222-2222-222222222222", "text": "Claim B"},
    ]
    fake_client = _FakeTavilyClient(
        {
            "Claim B": {
                "results": [
                    {
                        "content": "Evidence for claim B.",
                        "url": "https://example.com/b",
                        "title": "B",
                        "score": 0.7,
                    }
                ]
            }
        },
        failing_queries={"Claim A"},
    )
    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(fake_client.calls) == 2
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["snippet"] == "Evidence for claim B."


def test_retriever_timeline_entry_added(monkeypatch):
    """Timed decorator should record a timeline entry for retriever."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient({"Claim A": {"results": []}})
    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(result["timeline"]) == 1
    event = result["timeline"][0]
    assert event["agent"] == "retriever"
    assert event["started_at"]
    assert event["completed_at"]


def test_retriever_queries_vector_store(monkeypatch):
    """Retriever should query vector store once per claim with n_results=3."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient({"Claim A": {"results": []}})
    vector_calls: list[dict[str, Any]] = []

    def _fake_query_similar(query_text: str, n_results: int = 5):
        vector_calls.append({"query_text": query_text, "n_results": n_results})
        return [
            {
                "id": "v1",
                "snippet": "Vector evidence for claim A.",
                "metadata": {"title": "Knowledge base"},
                "distance": 0.2,
            }
        ]

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", _fake_query_similar)

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(vector_calls) == 1
    assert vector_calls[0]["query_text"] == "Claim A"
    assert vector_calls[0]["n_results"] == 3
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["source_type"] == "VECTOR_STORE"
    assert result["evidence"][0]["source_url"] is None


def test_retriever_empty_vector_store_ok(monkeypatch):
    """Empty vector store results should merge cleanly without errors."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient({"Claim A": {"results": []}})

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", lambda query_text, n_results=3: [])

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert result["error"] is None
    assert result["evidence"] == []


def test_retriever_merges_both_sources(monkeypatch):
    """Retriever should return both Tavily and vector store evidence in one list."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient(
        {
            "Claim A": {
                "results": [
                    {
                        "content": "Web evidence for claim A.",
                        "url": "https://example.com/a",
                        "title": "Web A",
                        "score": 0.83,
                    }
                ]
            }
        }
    )

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(
        retriever,
        "query_similar",
        lambda query_text, n_results=3: [
            {
                "id": "vec-1",
                "snippet": "Vector evidence for claim A.",
                "metadata": {"title": "Vector A"},
                "distance": 0.1,
            }
        ],
    )

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(result["evidence"]) == 2
    source_types = {item["source_type"] for item in result["evidence"]}
    assert source_types == {"WEB_SEARCH", "VECTOR_STORE"}


def test_retriever_deduplicates_by_url(monkeypatch):
    """Duplicate source URLs per claim should be deduplicated in final evidence list."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient(
        {
            "Claim A": {
                "results": [
                    {
                        "content": "Lower score duplicate",
                        "url": "https://example.com/same",
                        "title": "Same URL",
                        "score": 0.4,
                    },
                    {
                        "content": "Higher score duplicate",
                        "url": "https://example.com/same",
                        "title": "Same URL",
                        "score": 0.8,
                    },
                ]
            }
        }
    )

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", lambda query_text, n_results=3: [])

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["source_url"] == "https://example.com/same"


def test_retriever_keeps_highest_relevance_on_dupe(monkeypatch):
    """When duplicate URLs occur, retriever should keep the highest relevance entry."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient(
        {
            "Claim A": {
                "results": [
                    {
                        "content": "Low relevance",
                        "url": "https://example.com/dupe",
                        "title": "Dupe",
                        "score": 0.2,
                    },
                    {
                        "content": "High relevance",
                        "url": "https://example.com/dupe",
                        "title": "Dupe",
                        "score": 0.9,
                    },
                ]
            }
        }
    )

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", lambda query_text, n_results=3: [])

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["snippet"] == "High relevance"
    assert result["evidence"][0]["relevance_score"] == 0.9


def test_retriever_sorts_by_relevance(monkeypatch):
    """Final evidence should be sorted by relevance score descending."""
    claims = [{"id": "11111111-1111-1111-1111-111111111111", "text": "Claim A"}]
    fake_client = _FakeTavilyClient(
        {
            "Claim A": {
                "results": [
                    {
                        "content": "mid",
                        "url": "https://example.com/mid",
                        "title": "mid",
                        "score": 0.5,
                    },
                    {
                        "content": "high",
                        "url": "https://example.com/high",
                        "title": "high",
                        "score": 0.9,
                    },
                    {
                        "content": "low",
                        "url": "https://example.com/low",
                        "title": "low",
                        "score": 0.2,
                    },
                ]
            }
        }
    )

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", lambda query_text, n_results=3: [])

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    scores = [item["relevance_score"] for item in result["evidence"]]
    assert scores == sorted(scores, reverse=True)


def test_retriever_caps_per_claim(monkeypatch):
    """Retriever should keep at most 10 evidence items per claim and assign UUID ids."""
    claim_id = "11111111-1111-1111-1111-111111111111"
    claims = [{"id": claim_id, "text": "Claim A"}]
    fake_client = _FakeTavilyClient({"Claim A": {"results": []}})

    def _fake_vector_results(query_text: str, n_results: int = 3):
        _ = query_text
        _ = n_results
        rows = []
        for idx in range(12):
            rows.append(
                {
                    "id": f"v{idx}",
                    "snippet": f"Vector evidence {idx}",
                    "metadata": {"title": f"Row {idx}"},
                    "distance": 0.01 * idx,
                }
            )
        return rows

    monkeypatch.setattr(retriever, "_get_tavily_client", lambda: fake_client)
    monkeypatch.setattr(retriever, "query_similar", _fake_vector_results)

    state = _base_state(claims)
    result = retriever.retrieve_evidence(state)

    claim_items = [item for item in result["evidence"] if item["claim_id"] == claim_id]
    assert len(claim_items) == 10
    for item in claim_items:
        UUID(item["id"])
