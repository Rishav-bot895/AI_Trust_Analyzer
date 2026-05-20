"""Tests for ChromaDB vector store utilities (Task 1.10)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


class _FakeCollection:
    """In-memory fake Chroma collection for unit tests."""

    def __init__(self) -> None:
        self._rows: list[dict] = []

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
        for idx, doc_id in enumerate(ids):
            self._rows.append(
                {
                    "id": doc_id,
                    "document": documents[idx],
                    "metadata": metadatas[idx],
                }
            )

    def query(self, query_texts: list[str], n_results: int) -> dict:
        _ = query_texts
        rows = self._rows[:n_results]
        return {
            "ids": [[row["id"] for row in rows]],
            "documents": [[row["document"] for row in rows]],
            "metadatas": [[row["metadata"] for row in rows]],
            "distances": [[0.1 for _ in rows]],
        }


def _reload_vector_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Reload module with controlled env values and isolated import state."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test_task_1_10.db")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))

    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.db.vector_store", None)
    return importlib.import_module("app.db.vector_store")


def test_collection_created_on_first_use(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Collection should be initialized lazily and only once."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_collection = _FakeCollection()
    call_count = {"count": 0}

    def _fake_create_collection():
        call_count["count"] += 1
        return fake_collection

    monkeypatch.setattr(vector_store, "_create_collection", _fake_create_collection)

    first = vector_store.get_collection()
    second = vector_store.get_collection()

    assert first is fake_collection
    assert second is fake_collection
    assert call_count["count"] == 1


def test_add_and_query_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Added documents should be retrievable via similarity query helper."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_collection = _FakeCollection()
    monkeypatch.setattr(vector_store, "_create_collection", lambda: fake_collection)

    vector_store.add_documents(
        texts=["Mars is the fourth planet from the Sun."],
        metadatas=[{"source": "test"}],
        ids=["doc-1"],
    )

    results = vector_store.query_similar("Mars", n_results=5)

    assert len(results) == 1
    assert results[0]["id"] == "doc-1"
    assert "Mars" in results[0]["snippet"]


def test_query_returns_n_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """query_similar should return at most n_results items."""
    vector_store = _reload_vector_store(monkeypatch, tmp_path)
    fake_collection = _FakeCollection()
    monkeypatch.setattr(vector_store, "_create_collection", lambda: fake_collection)

    vector_store.add_documents(
        texts=["Doc A", "Doc B", "Doc C"],
        metadatas=[{"k": "a"}, {"k": "b"}, {"k": "c"}],
        ids=["a", "b", "c"],
    )

    results = vector_store.query_similar("Doc", n_results=2)
    assert len(results) == 2