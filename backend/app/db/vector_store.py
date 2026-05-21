"""ChromaDB client and helper functions for evidence vector retrieval."""

from __future__ import annotations

from typing import Any, Protocol, cast

from chromadb import PersistentClient
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings


class _EmbeddingCallable(Protocol):
    """Protocol for Chroma embedding functions."""

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        """Return embeddings for the provided input texts."""


class LocalChromaEmbeddingFunction:
    """Adapter to use local sentence-transformers embeddings with ChromaDB."""

    def __init__(self) -> None:
        self._embeddings = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return cast(list[list[float]], self._embeddings(input))


_client: PersistentClient | None = None
_collection: Collection | None = None


def _get_client() -> PersistentClient:
    """Create or return the singleton persistent Chroma client."""
    global _client
    if _client is None:
        _client = PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def _create_collection() -> Collection:
    """Create or return the evidence collection using local embeddings."""
    client = _get_client()
    embedding_function = cast(_EmbeddingCallable, LocalChromaEmbeddingFunction())
    return client.get_or_create_collection(
        name="evidence",
        embedding_function=embedding_function,
    )


def get_collection() -> Collection:
    """Return the lazily initialized evidence collection singleton."""
    global _collection
    if _collection is None:
        _collection = _create_collection()
    return _collection


def add_documents(texts: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> None:
    """Add documents to the evidence collection."""
    if not texts:
        return

    collection = get_collection()
    collection.add(documents=texts, metadatas=metadatas, ids=ids)


def query_similar(query_text: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Query semantically similar evidence snippets from ChromaDB."""
    if not query_text.strip():
        return []

    collection = get_collection()
    raw = collection.query(query_texts=[query_text], n_results=n_results)

    ids = raw.get("ids", [[]])[0] or []
    documents = raw.get("documents", [[]])[0] or []
    metadatas = raw.get("metadatas", [[]])[0] or []
    distances = raw.get("distances", [[]])[0] or []

    results: list[dict[str, Any]] = []
    for index, doc_id in enumerate(ids):
        results.append(
            {
                "id": doc_id,
                "snippet": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
                "distance": distances[index] if index < len(distances) else None,
            }
        )

    return results