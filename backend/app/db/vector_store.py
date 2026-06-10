"""PostgreSQL pgvector helpers for evidence vector retrieval."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


_engine: Engine | None = None
_embedder: "SentenceTransformer | None" = None


def _sync_database_url() -> str:
    """Convert async SQLAlchemy URL into a sync URL for SQL execution."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return url


def _get_engine() -> Engine:
    """Create or return singleton SQLAlchemy sync engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(_sync_database_url(), future=True)
    return _engine


def _get_embedder() -> "SentenceTransformer":
    """Create or return singleton embedding model."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _vector_literal(values: list[float]) -> str:
    """Render vector values to pgvector literal format."""
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text snippets using local sentence-transformers."""
    if not texts:
        return []

    model = _get_embedder()
    vectors = model.encode(texts, convert_to_numpy=False, normalize_embeddings=True)

    normalized: list[list[float]] = []
    for vector in vectors:
        normalized.append([float(value) for value in vector])
    return normalized


def _validate_owner_scope(
    *,
    user_id: str | None,
    guest_session_id: str | None,
    is_guest: bool,
) -> bool:
    if is_guest:
        return bool(guest_session_id) and not user_id
    return bool(user_id) and not guest_session_id


def add_documents(
    texts: list[str],
    metadatas: list[dict[str, Any]],
    ids: list[str],
    *,
    user_id: str | None,
    guest_session_id: str | None,
    is_guest: bool,
    evidence_ids: list[str] | None = None,
) -> None:
    """Add documents and their embeddings to the ownership-scoped pgvector table."""
    if not texts:
        return

    if len(texts) != len(ids):
        raise ValueError("texts and ids must have the same length")

    if metadatas and len(metadatas) != len(texts):
        raise ValueError("metadatas must match texts length when provided")

    if evidence_ids and len(evidence_ids) != len(texts):
        raise ValueError("evidence_ids must match texts length when provided")

    if not _validate_owner_scope(user_id=user_id, guest_session_id=guest_session_id, is_guest=is_guest):
        raise ValueError("Vector documents must be stored with a valid owner scope")

    metadata_rows = metadatas if metadatas else [{} for _ in texts]
    resolved_evidence_ids = evidence_ids or [None for _ in texts]
    vectors = _embed_texts(texts)

    engine = _get_engine()
    with engine.begin() as conn:
        for idx, doc_id in enumerate(ids):
            conn.execute(
                text(
                    """
                    INSERT INTO evidence_embeddings (
                        id,
                        evidence_id,
                        snippet,
                        metadata,
                        user_id,
                        guest_session_id,
                        is_guest,
                        embedding
                    )
                    VALUES (
                        :id,
                        :evidence_id,
                        :snippet,
                        CAST(:metadata AS jsonb),
                        :user_id,
                        :guest_session_id,
                        :is_guest,
                        CAST(:embedding AS vector)
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET evidence_id = EXCLUDED.evidence_id,
                        user_id = EXCLUDED.user_id,
                        guest_session_id = EXCLUDED.guest_session_id,
                        is_guest = EXCLUDED.is_guest,
                        snippet = EXCLUDED.snippet,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """
                ),
                {
                    "id": doc_id,
                    "evidence_id": resolved_evidence_ids[idx],
                    "snippet": texts[idx],
                    "metadata": json.dumps(metadata_rows[idx]),
                    "user_id": user_id,
                    "guest_session_id": guest_session_id,
                    "is_guest": bool(is_guest),
                    "embedding": _vector_literal(vectors[idx]),
                },
            )


def query_similar(
    query_text: str,
    n_results: int = 5,
    *,
    user_id: str | None,
    guest_session_id: str | None,
    is_guest: bool,
) -> list[dict[str, Any]]:
    """Query semantically similar evidence snippets from pgvector within owner scope."""
    if not query_text.strip() or n_results <= 0:
        return []

    if not _validate_owner_scope(user_id=user_id, guest_session_id=guest_session_id, is_guest=is_guest):
        return []

    query_vector = _embed_texts([query_text])[0]
    engine = _get_engine()

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    evidence_id,
                    snippet,
                    metadata,
                    (embedding <=> CAST(:query_embedding AS vector)) AS distance
                FROM evidence_embeddings
                WHERE is_guest = :is_guest
                  AND (
                        (:is_guest = TRUE AND guest_session_id = :guest_session_id)
                        OR
                        (:is_guest = FALSE AND user_id = :user_id)
                  )
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :n_results
                """
            ),
            {
                "query_embedding": _vector_literal(query_vector),
                "n_results": int(n_results),
                "is_guest": bool(is_guest),
                "user_id": user_id,
                "guest_session_id": guest_session_id,
            },
        ).mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        metadata = row.get("metadata")
        if metadata is None:
            parsed_metadata: dict[str, Any] = {}
        elif isinstance(metadata, dict):
            parsed_metadata = metadata
        elif isinstance(metadata, str):
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                parsed_metadata = {}
        else:
            parsed_metadata = dict(metadata)

        results.append(
            {
                "id": row.get("id"),
                "evidence_id": row.get("evidence_id"),
                "snippet": row.get("snippet") or "",
                "metadata": parsed_metadata,
                "distance": row.get("distance"),
            }
        )

    return results
