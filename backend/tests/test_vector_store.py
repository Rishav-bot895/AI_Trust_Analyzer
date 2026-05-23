"""Tests for pgvector vector store utilities (Task 1.10)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeConnection:
    def __init__(self, state: dict):
        self._state = state

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}

        if "INSERT INTO evidence_embeddings" in sql:
            self._state["rows"][params["id"]] = {
                "id": params["id"],
                "snippet": params["snippet"],
                "metadata": params["metadata"],
                "distance": 0.1,
            }
            return _FakeResult([])

        if "SELECT" in sql and "FROM evidence_embeddings" in sql:
            rows = list(self._state["rows"].values())[: int(params.get("n_results", 5))]
            return _FakeResult(rows)

        self._state["ddl_calls"].append(sql)
        return _FakeResult([])


class _FakeBeginContext:
    def __init__(self, state: dict):
        self._state = state

    def __enter__(self):
        return _FakeConnection(self._state)

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self):
        self.state = {"rows": {}, "ddl_calls": []}

    def begin(self):
        return _FakeBeginContext(self.state)


def _reload_vector_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Reload module with controlled env values and isolated import state."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")

    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.db.vector_store", None)
    return importlib.import_module("app.db.vector_store")


def test_collection_created_on_first_use(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Vector store should not run runtime DDL (migration-managed schema)."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_engine = _FakeEngine()

    monkeypatch.setattr(vector_store, "_get_engine", lambda: fake_engine)
    monkeypatch.setattr(vector_store, "_embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])

    vector_store.add_documents(
        texts=["Doc 1"],
        metadatas=[{"source": "test"}],
        ids=["doc-1"],
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )
    vector_store.add_documents(
        texts=["Doc 2"],
        metadatas=[{"source": "test"}],
        ids=["doc-2"],
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )

    assert fake_engine.state["ddl_calls"] == []


def test_add_and_query_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Added documents should be retrievable via similarity query helper."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_engine = _FakeEngine()

    monkeypatch.setattr(vector_store, "_get_engine", lambda: fake_engine)
    monkeypatch.setattr(vector_store, "_embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])

    vector_store.add_documents(
        texts=["Mars is the fourth planet from the Sun."],
        metadatas=[{"source": "test"}],
        ids=["doc-1"],
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )

    results = vector_store.query_similar(
        "Mars",
        n_results=5,
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )

    assert len(results) == 1
    assert results[0]["id"] == "doc-1"
    assert "Mars" in results[0]["snippet"]


def test_query_returns_n_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """query_similar should return at most n_results items."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_engine = _FakeEngine()

    monkeypatch.setattr(vector_store, "_get_engine", lambda: fake_engine)
    monkeypatch.setattr(vector_store, "_embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])

    vector_store.add_documents(
        texts=["Doc A", "Doc B", "Doc C"],
        metadatas=[{"k": "a"}, {"k": "b"}, {"k": "c"}],
        ids=["a", "b", "c"],
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )

    results = vector_store.query_similar(
        "Doc",
        n_results=2,
        user_id=None,
        guest_session_id="guest-a",
        is_guest=True,
    )
    assert len(results) == 2
