from __future__ import annotations

from uuid import uuid4
from typing import Any

from app.agents.base import (
    SYSTEM_PROMPT_FACTUALITY,
    SYSTEM_PROMPT_JSON_ONLY,
    get_llm,
    parse_json_response,
    timed_agent,
)
from app.core.config import settings
from app.schemas.agent_state import AgentState
from app.schemas.claim import ClaimCreate


EXTRACTION_SYSTEM_PROMPT = "\n".join(
    [
        SYSTEM_PROMPT_FACTUALITY,
        "Extract only atomic factual claims from the provided AI response.",
        "Ignore opinions, preferences, and stylistic language.",
        "Return JSON with shape: {'claims': [{'text': str, 'confidence': float}]}.",
        SYSTEM_PROMPT_JSON_ONLY,
    ]
)


@timed_agent("claim_extractor")
def extract_claims(state: AgentState) -> AgentState:
    """Extract atomic factual claims from the response text into state['claims']."""
    response_text = (state.get("response") or "").strip()
    if not response_text:
        state["claims"] = []
        return state

    llm = get_llm(model_name=state.get("model_name") or "gemini-3.1-flash-lite")
    messages: list[dict[str, str]] = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": response_text},
    ]
    llm_response = llm.invoke(messages)
    raw_content = getattr(llm_response, "content", "")

    try:
        parsed = parse_json_response(raw_content)
    except Exception as exc:
        state["claims"] = []
        state["error"] = f"Claim extraction failed: {exc}"
        return state

    claims = parsed.get("claims", [])
    if not isinstance(claims, list):
        claims = []

    normalized_claims: list[dict[str, Any]] = []
    for idx, item in enumerate(claims):
        if not isinstance(item, dict):
            continue

        text = item.get("text")
        confidence_raw = item.get("confidence")
        if text is None or confidence_raw is None:
            continue

        try:
            candidate = ClaimCreate(
                text=str(text).strip(),
                confidence=float(confidence_raw),
                claim_index=idx,
            )
        except Exception:
            continue

        normalized_claims.append(
            {
                "id": str(uuid4()),
                "text": candidate.text,
                "confidence": candidate.confidence,
                "claim_index": candidate.claim_index,
                "source_span": candidate.source_span,
            }
        )

    if len(normalized_claims) > settings.MAX_CLAIMS:
        normalized_claims = normalized_claims[: settings.MAX_CLAIMS]

    state["claims"] = normalized_claims
    return state
