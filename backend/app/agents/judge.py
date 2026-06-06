from __future__ import annotations

from typing import Any

from app.agents.base import SYSTEM_PROMPT_FACTUALITY, get_llm, timed_agent
from app.schemas.agent_state import AgentState
from app.schemas.claim import ClaimStatus


_STATUS_WEIGHTS: dict[str, float] = {
    ClaimStatus.SUPPORTED.value: 1.0,
    ClaimStatus.PARTIALLY_SUPPORTED.value: 0.65,
    ClaimStatus.UNSUPPORTED.value: 0.4,
    ClaimStatus.CONTRADICTED.value: 0.0,
    ClaimStatus.UNVERIFIABLE.value: 0.5,
}


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text.strip()
        return ""
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                continue
            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str):
                chunks.append(text_attr)
        return "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip()).strip()

    text_attr = getattr(content, "text", None)
    if isinstance(text_attr, str):
        return text_attr.strip()
    return ""


def _extract_verified_claims(state: AgentState) -> list[dict[str, Any]]:
    claims = state.get("verified_claims") or state.get("claims") or []
    return [claim for claim in claims if isinstance(claim, dict)]


def _extract_evidence(state: AgentState) -> list[dict[str, Any]]:
    evidence = state.get("evidence") or []
    return [item for item in evidence if isinstance(item, dict)]


def _base_score_from_claims(claims: list[dict[str, Any]]) -> float:
    if not claims:
        return 0.0

    total = 0.0
    for claim in claims:
        status = str(claim.get("status") or ClaimStatus.UNVERIFIABLE.value).strip().upper()
        total += _STATUS_WEIGHTS.get(status, _STATUS_WEIGHTS[ClaimStatus.UNVERIFIABLE.value])

    return (total / len(claims)) * 100.0


def _evidence_adjustment(
    claims: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> float:
    evidence_by_claim: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        claim_id = item.get("claim_id")
        if claim_id is None:
            continue
        evidence_by_claim.setdefault(str(claim_id), []).append(item)

    adjustment = 0.0
    for claim in claims:
        claim_id = claim.get("id")
        if claim_id is None:
            continue

        status = str(claim.get("status") or "").strip().upper()
        claim_evidence = evidence_by_claim.get(str(claim_id), [])

        for_count = sum(
            1
            for item in claim_evidence
            if str(item.get("polarity") or "").strip().upper() == "FOR"
        )
        against_count = sum(
            1
            for item in claim_evidence
            if str(item.get("polarity") or "").strip().upper() == "AGAINST"
        )

        if status in {ClaimStatus.SUPPORTED.value, ClaimStatus.PARTIALLY_SUPPORTED.value}:
            adjustment += float((for_count // 3) * 2)
        if status in {ClaimStatus.CONTRADICTED.value, ClaimStatus.PARTIALLY_SUPPORTED.value}:
            adjustment -= float((against_count // 3) * 2)

    return adjustment


def _count_critic_issues(critique: str | None) -> int:
    if not critique:
        return 0

    content = critique.strip()
    if not content or content == "No logical issues detected.":
        return 0

    lines = [line.strip() for line in content.splitlines()]
    in_logical_section = False
    issue_count = 0

    for line in lines:
        if line.startswith("## "):
            if line == "## Logical Issues":
                in_logical_section = True
                continue
            if in_logical_section:
                break

        if in_logical_section and line.startswith("- "):
            issue_count += 1

    if issue_count > 0:
        return issue_count

    return sum(1 for line in lines if line.startswith("- "))


def _clamp_score(score: float) -> int:
    if score < 0:
        return 0
    if score > 100:
        return 100
    return int(round(score))


def _risk_from_score(score: int) -> str:
    if score >= 80:
        return "LOW"
    if score >= 50:
        return "MEDIUM"
    return "HIGH"


def _top_issues_from_critique(critique: str | None) -> list[str]:
    if not critique:
        return []

    issues: list[str] = []
    for raw_line in critique.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            issues.append(line[2:].strip())
        if len(issues) == 3:
            break
    return issues


def _aggregate_verification_context(
    claims: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {
        ClaimStatus.SUPPORTED.value: 0,
        ClaimStatus.PARTIALLY_SUPPORTED.value: 0,
        ClaimStatus.CONTRADICTED.value: 0,
        ClaimStatus.UNSUPPORTED.value: 0,
        ClaimStatus.UNVERIFIABLE.value: 0,
    }
    for claim in claims:
        status = str(claim.get("status") or ClaimStatus.UNVERIFIABLE.value).strip().upper()
        if status not in status_counts:
            status = ClaimStatus.UNVERIFIABLE.value
        status_counts[status] += 1

    for_count = 0
    against_count = 0
    unknown_count = 0
    for item in evidence_items:
        polarity = str(item.get("polarity") or "").strip().upper()
        if polarity == "FOR":
            for_count += 1
        elif polarity == "AGAINST":
            against_count += 1
        else:
            unknown_count += 1

    return {
        "status_counts": status_counts,
        "evidence_counts": {
            "for": for_count,
            "against": against_count,
            "unknown": unknown_count,
        },
    }


def _fallback_verdict(score: int, risk: str, issues: list[str]) -> str:
    if issues:
        return (
            f"Trust score is {score}/100 with {risk} hallucination risk. "
            f"Top concern: {issues[0]}."
        )
    return (
        f"Trust score is {score}/100 with {risk} hallucination risk. "
        "No major logical issues were highlighted in the critique."
    )


def _enforce_verdict_consistency(
    verdict: str,
    score: int,
    risk: str,
    aggregates: dict[str, Any],
) -> str:
    status_counts = aggregates.get("status_counts") or {}
    evidence_counts = aggregates.get("evidence_counts") or {}
    supported_like = int(status_counts.get(ClaimStatus.SUPPORTED.value, 0)) + int(
        status_counts.get(ClaimStatus.PARTIALLY_SUPPORTED.value, 0)
    )
    contradicted_like = int(status_counts.get(ClaimStatus.CONTRADICTED.value, 0))
    unresolved_like = int(status_counts.get(ClaimStatus.UNSUPPORTED.value, 0)) + int(
        status_counts.get(ClaimStatus.UNVERIFIABLE.value, 0)
    )
    for_count = int(evidence_counts.get("for", 0))
    against_count = int(evidence_counts.get("against", 0))

    lowered = verdict.lower()
    uncertain_phrases = ("insufficient", "cannot verify", "unverifiable", "not enough evidence")
    overpositive_phrases = ("highly trustworthy", "strongly supported", "fully reliable", "no issues")

    if supported_like > (contradicted_like + unresolved_like) and for_count >= against_count:
        if any(phrase in lowered for phrase in uncertain_phrases):
            return (
                f"Trust score is {score}/100 with {risk} hallucination risk. "
                "Most claims are supported by available evidence, with limited contradictory signals."
            )

    if contradicted_like > supported_like and against_count > for_count:
        if any(phrase in lowered for phrase in overpositive_phrases):
            return (
                f"Trust score is {score}/100 with {risk} hallucination risk. "
                "Contradictory evidence outweighs support across the analyzed claims."
            )

    return verdict


def _generate_verdict(
    score: int,
    risk: str,
    issues: list[str],
    aggregates: dict[str, Any],
    model_name: str,
) -> str:
    status_counts = aggregates.get("status_counts") or {}
    evidence_counts = aggregates.get("evidence_counts") or {}
    issue_context = "\n".join(f"- {item}" for item in issues) if issues else "- none"
    prompt = "\n".join(
        [
            f"Trust score: {score}",
            f"Hallucination risk: {risk}",
            f"Claim status counts: {status_counts}",
            f"Evidence polarity counts: {evidence_counts}",
            "Top issues:",
            issue_context,
            "Constraints: Ensure verdict aligns with status and evidence counts.",
            "If SUPPORTED dominates and AGAINST is low, do not claim insufficient information.",
            "Write a concise verdict in 1-3 sentences.",
        ]
    )

    try:
        llm = get_llm(model_name=model_name)
        response = llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        f"{SYSTEM_PROMPT_FACTUALITY} "
                        "Write clear decision-support summaries and avoid absolute claims."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        content = getattr(response, "content", response)
        verdict = _content_to_text(content)
        if verdict:
            return verdict
    except Exception:
        pass

    return _fallback_verdict(score, risk, issues)


@timed_agent("judge")
def judge_analysis(state: AgentState) -> AgentState:
    """Compute trust score/risk and generate a concise verdict summary."""
    claims = _extract_verified_claims(state)
    evidence_items = _extract_evidence(state)

    score = _base_score_from_claims(claims)
    score += _evidence_adjustment(claims, evidence_items)
    score -= float(_count_critic_issues(state.get("critique")) * 5)

    rounded_score = _clamp_score(score)
    risk = _risk_from_score(rounded_score)
    issues = _top_issues_from_critique(state.get("critique"))
    aggregates = _aggregate_verification_context(claims, evidence_items)
    model_name = str(state.get("model_name") or "gemini-3.1-flash-lite")

    state["trust_score"] = float(rounded_score)
    state["hallucination_risk"] = risk
    generated_verdict = _generate_verdict(rounded_score, risk, issues, aggregates, model_name)
    state["verdict"] = _enforce_verdict_consistency(generated_verdict, rounded_score, risk, aggregates)
    return state
