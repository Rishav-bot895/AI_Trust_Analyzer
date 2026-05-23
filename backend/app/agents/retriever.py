from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.agents.base import timed_agent
from app.core.config import settings
from app.db.vector_store import query_similar
from app.schemas.agent_state import AgentState
from app.schemas.evidence import EvidenceCreate, EvidenceSource

try:
    from tavily import TavilyClient
except Exception:  # pragma: no cover - dependency/import safety for local test environments
    TavilyClient = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


def _get_tavily_client() -> Any:
    if TavilyClient is None:
        raise RuntimeError("tavily-python is not available. Install dependencies from requirements.txt")
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


def _coerce_relevance(raw_score: Any) -> float:
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def _distance_to_relevance(distance: Any) -> float:
    """Convert vector distance into a bounded relevance score in 0..1."""
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0

    relevance = 1.0 - value
    if relevance < 0.0:
        return 0.0
    if relevance > 1.0:
        return 1.0
    return relevance


def _finalize_evidence(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply per-claim dedupe/ranking/cap and assign final evidence UUIDs."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        claim_id = item.get("claim_id")
        if claim_id is None:
            continue
        claim_key = str(claim_id)
        grouped.setdefault(claim_key, []).append(item)

    finalized: list[dict[str, Any]] = []
    for claim_key, claim_items in grouped.items():
        with_url: dict[str, dict[str, Any]] = {}
        without_url: list[dict[str, Any]] = []

        for item in claim_items:
            source_url = item.get("source_url")
            if source_url:
                url_key = str(source_url)
                existing = with_url.get(url_key)
                if existing is None or _coerce_relevance(item.get("relevance_score")) > _coerce_relevance(
                    existing.get("relevance_score")
                ):
                    with_url[url_key] = item
            else:
                without_url.append(item)

        merged = list(with_url.values()) + without_url
        merged.sort(key=lambda row: _coerce_relevance(row.get("relevance_score")), reverse=True)
        top_items = merged[:10]

        for row in top_items:
            normalized = dict(row)
            normalized["claim_id"] = claim_key
            normalized["id"] = str(uuid4())
            finalized.append(normalized)

    finalized.sort(key=lambda row: _coerce_relevance(row.get("relevance_score")), reverse=True)
    return finalized


@timed_agent("retriever")
def retrieve_evidence(state: AgentState) -> AgentState:
    """Retrieve candidate evidence from Tavily and pgvector for each claim."""
    claims = state.get("claims") or []
    if not claims:
        state["evidence"] = state.get("evidence") or []
        return state

    client = _get_tavily_client()
    evidence: list[dict[str, Any]] = list(state.get("evidence") or [])
    owner_user_id = state.get("user_id")
    owner_guest_session_id = state.get("guest_session_id")
    owner_is_guest = bool(state.get("is_guest", bool(owner_guest_session_id and not owner_user_id)))

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        claim_text = str(claim.get("text") or "").strip()
        claim_id = claim.get("id")
        if not claim_text or not claim_id:
            continue

        try:
            search_response = client.search(query=claim_text, max_results=3)
        except Exception as exc:  # pragma: no cover - behavior validated via tests
            logger.warning("Tavily search failed for claim %s: %s", claim_id, exc)
            continue

        raw_results = search_response.get("results", []) if isinstance(search_response, dict) else []
        if not isinstance(raw_results, list):
            continue

        for result in raw_results:
            if not isinstance(result, dict):
                continue

            snippet = str(result.get("content") or result.get("snippet") or "").strip()
            if not snippet:
                continue

            try:
                candidate = EvidenceCreate(
                    claim_id=claim_id,
                    snippet=snippet,
                    source_url=result.get("url"),
                    source_title=result.get("title"),
                    relevance_score=_coerce_relevance(result.get("score")),
                    source_type=EvidenceSource.WEB_SEARCH,
                )
            except Exception:
                continue

            evidence.append(candidate.model_dump(mode="json"))

        vector_results: list[dict[str, Any]] = []
        if (owner_is_guest and owner_guest_session_id) or ((not owner_is_guest) and owner_user_id):
            try:
                vector_results = query_similar(
                    claim_text,
                    n_results=3,
                    user_id=str(owner_user_id) if owner_user_id else None,
                    guest_session_id=str(owner_guest_session_id) if owner_guest_session_id else None,
                    is_guest=owner_is_guest,
                )
            except Exception as exc:  # pragma: no cover - behavior validated via tests
                logger.warning("Vector store query failed for claim %s: %s", claim_id, exc)
                continue

        for vector_item in vector_results:
            if not isinstance(vector_item, dict):
                continue

            snippet = str(vector_item.get("snippet") or "").strip()
            if not snippet:
                continue

            metadata = vector_item.get("metadata")
            source_title: str | None = None
            if isinstance(metadata, dict):
                metadata_title = metadata.get("title")
                if metadata_title is not None:
                    source_title = str(metadata_title)

            try:
                candidate = EvidenceCreate(
                    claim_id=claim_id,
                    snippet=snippet,
                    source_url=None,
                    source_title=source_title,
                    relevance_score=_distance_to_relevance(vector_item.get("distance")),
                    source_type=EvidenceSource.PGVECTOR,
                )
            except Exception:
                continue

            evidence.append(candidate.model_dump(mode="json"))

    state["evidence"] = _finalize_evidence(evidence)
    return state
