from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from app.agents.base import (
    SYSTEM_PROMPT_FACTUALITY,
    SYSTEM_PROMPT_JSON_ONLY,
    get_llm,
    parse_json_response,
    timed_agent,
)
from app.schemas.agent_state import AgentState


SUPPORTED_FALLACY_TYPES: tuple[str, ...] = (
    "AD_HOMINEM",
    "FALSE_DICHOTOMY",
    "HASTY_GENERALIZATION",
    "CIRCULAR_REASONING",
    "APPEAL_TO_AUTHORITY",
    "POST_HOC",
    "STRAW_MAN",
    "SLIPPERY_SLOPE",
    "LOW_CONFIDENCE_LANGUAGE",
)

CRITIC_SYSTEM_PROMPT = "\n".join(
    [
        SYSTEM_PROMPT_FACTUALITY,
        "Analyze the full response for logical issues and rhetorical quality risks.",
        "Detect these fallacy categories when present: AD_HOMINEM, FALSE_DICHOTOMY, HASTY_GENERALIZATION, CIRCULAR_REASONING, APPEAL_TO_AUTHORITY, POST_HOC, STRAW_MAN, SLIPPERY_SLOPE.",
        "If uncertain language appears, flag LOW_CONFIDENCE_LANGUAGE.",
        "Return JSON with shape: {'issues': [{'type': str, 'quote': str, 'explanation': str}], 'overall_assessment': str}.",
        SYSTEM_PROMPT_JSON_ONLY,
    ]
)

_HEDGING_PATTERN = re.compile(r"\b(may|might|could)\b", re.IGNORECASE)


def _build_claim_status_summary(state: AgentState) -> str:
    claims = list(state.get("verified_claims") or state.get("claims") or [])
    if not claims:
        return "No claim-level verification results were provided."

    lines: list[str] = []
    for idx, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text") or "").strip()
        status = str(claim.get("status") or "UNVERIFIED").strip()
        if text:
            lines.append(f"{idx}. [{status}] {text}")

    return "\n".join(lines) if lines else "No claim-level verification results were provided."


def _parse_critic_payload(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content
    if isinstance(raw_content, str):
        return parse_json_response(raw_content)
    raise ValueError("Critic response must be a JSON string or object")


def _normalize_issues(raw_issues: Any) -> list[dict[str, str]]:
    if not isinstance(raw_issues, list):
        return []

    issues: list[dict[str, str]] = []
    for item in raw_issues:
        if not isinstance(item, dict):
            continue

        issue_type = str(item.get("type") or "UNKNOWN").strip() or "UNKNOWN"
        quote = str(item.get("quote") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        if not explanation:
            continue

        issues.append(
            {
                "type": issue_type,
                "quote": quote,
                "explanation": explanation,
            }
        )

    return issues


def _extract_hedging_issue(response_text: str) -> dict[str, str] | None:
    match = _HEDGING_PATTERN.search(response_text)
    if not match:
        return None

    sentence = _extract_sentence_containing(response_text, match.start())
    return {
        "type": "LOW_CONFIDENCE_LANGUAGE",
        "quote": sentence,
        "explanation": "Response uses hedging language that lowers factual confidence.",
    }


def _extract_sentence_containing(text: str, index: int) -> str:
    if not text:
        return ""

    left = text.rfind(".", 0, index)
    right = text.find(".", index)

    start = 0 if left < 0 else left + 1
    end = len(text) if right < 0 else right + 1
    sentence = text[start:end].strip()
    return sentence or text[:200].strip()


def _format_critique(overall_assessment: str, issues: list[dict[str, str]]) -> str:
    safe_overall = overall_assessment.strip() or "No overall assessment provided."
    if not issues:
        return "No logical issues detected."

    grouped: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for issue in issues:
        issue_type = issue.get("type", "UNKNOWN")
        grouped.setdefault(issue_type, []).append(issue)

    lines: list[str] = ["## Logical Issues"]
    for issue_type, grouped_issues in grouped.items():
        pretty_type = _format_issue_type(issue_type)
        canonical_type = issue_type.strip().upper() or "UNKNOWN"
        lines.append(f"### {pretty_type} ({canonical_type})")
        for issue in grouped_issues:
            quote = issue.get("quote", "").strip() or "(no quote provided)"
            explanation = issue.get("explanation", "").strip()
            lines.append(f'- "{quote}" - {explanation}')

    lines.extend(["", "## Overall Assessment", safe_overall])
    return "\n".join(lines)


def _format_issue_type(issue_type: str) -> str:
    normalized = issue_type.replace("_", " ").strip()
    return normalized.title() if normalized else "Unknown"


@timed_agent("critic")
def critique_response(state: AgentState) -> AgentState:
    """Analyze response quality/fallacies and store a critique summary in state['critique']."""
    response_text = str(state.get("response") or "").strip()
    claim_summary = _build_claim_status_summary(state)

    llm = get_llm(model_name=state.get("model_name") or "gemini-3.1-flash-lite")
    prompt = "\n\n".join(
        [
            "Response to critique:",
            response_text or "(empty response)",
            "Claim verification summary:",
            claim_summary,
        ]
    )

    raw_payload: dict[str, Any] = {"issues": [], "overall_assessment": ""}
    try:
        llm_response = llm.invoke(
            [
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        raw_payload = _parse_critic_payload(getattr(llm_response, "content", llm_response))
    except Exception as exc:
        raw_payload = {
            "issues": [],
            "overall_assessment": f"Critic analysis failed: {exc}",
        }

    issues = _normalize_issues(raw_payload.get("issues"))
    hedging_issue = _extract_hedging_issue(response_text)
    if hedging_issue is not None and all(
        issue.get("type", "").upper() != "LOW_CONFIDENCE_LANGUAGE" for issue in issues
    ):
        issues.append(hedging_issue)

    overall_assessment = str(raw_payload.get("overall_assessment") or "").strip()
    state["critique"] = _format_critique(overall_assessment, issues)
    return state
