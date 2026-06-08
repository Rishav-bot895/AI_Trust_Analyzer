from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.schemas.claim import ClaimStatus
from app.schemas.evidence import EvidencePolarity


FALLBACK_REASON_CODES: frozenset[str] = frozenset(
    {
        "parse_failure",
        "no_evidence",
        "low_signal",
        "schema_mismatch",
    }
)

VERDICT_UNCERTAIN_PHRASES: tuple[str, ...] = (
    "insufficient evidence",
    "cannot verify",
    "unverifiable",
    "not enough evidence",
    "too little evidence",
)

VERDICT_OVERPOSITIVE_PHRASES: tuple[str, ...] = (
    "highly trustworthy",
    "strongly supported",
    "fully reliable",
    "no issues",
    "perfectly accurate",
)

PERSISTENCE_VIOLATION_PREFIX = "policy_guardrail_violation"


def _claim_status(value: Any) -> str:
    status = str(value or ClaimStatus.UNVERIFIABLE.value).strip().upper()
    if status in {item.value for item in ClaimStatus}:
        return status
    return ClaimStatus.UNVERIFIABLE.value


def _evidence_polarity(value: Any) -> str:
    polarity = str(value or "").strip().upper()
    if polarity in {item.value for item in EvidencePolarity}:
        return polarity
    if polarity in {"SUPPORTING", "SUPPORTS", "SUPPORT"}:
        return EvidencePolarity.FOR.value
    if polarity in {"CONTRADICTING", "CONTRADICTS", "AGAINST"}:
        return EvidencePolarity.AGAINST.value
    return "UNKNOWN"


def group_evidence_by_claim(evidence_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        if claim_id is None:
            continue
        grouped[str(claim_id)].append(item)
    return grouped


def validate_persistable_analysis_state(state: dict[str, Any]) -> list[str]:
    """Return human-readable violations that would make persisted state contradictory."""
    claims = state.get("verified_claims") or state.get("claims") or []
    evidence_items = [item for item in (state.get("evidence") or []) if isinstance(item, dict)]
    grouped_evidence = group_evidence_by_claim(evidence_items)
    violations: list[str] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        claim_id = str(claim.get("id") or "")
        status = _claim_status(claim.get("status"))
        claim_evidence = grouped_evidence.get(claim_id, [])
        for_count = sum(
            1
            for item in claim_evidence
            if _evidence_polarity(item.get("polarity")) == EvidencePolarity.FOR.value
        )
        against_count = sum(
            1
            for item in claim_evidence
            if _evidence_polarity(item.get("polarity")) == EvidencePolarity.AGAINST.value
        )
        unknown_count = sum(
            1
            for item in claim_evidence
            if _evidence_polarity(item.get("polarity")) == EvidencePolarity.UNKNOWN.value
        )

        if status == ClaimStatus.SUPPORTED.value:
            if for_count == 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is SUPPORTED but has no FOR evidence"
                )
            if against_count > 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is SUPPORTED but has AGAINST evidence"
                )
        elif status == ClaimStatus.PARTIALLY_SUPPORTED.value:
            if for_count == 0 or against_count == 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is PARTIALLY_SUPPORTED but evidence is not mixed (FOR={for_count}, AGAINST={against_count}, UNKNOWN={unknown_count})"
                )
        elif status == ClaimStatus.CONTRADICTED.value:
            if against_count == 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is CONTRADICTED but has no AGAINST evidence"
                )
            if for_count > 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is CONTRADICTED but has FOR evidence"
                )
        elif status == ClaimStatus.UNSUPPORTED.value:
            if for_count > 0 or against_count > 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is UNSUPPORTED but has polarized evidence (FOR={for_count}, AGAINST={against_count})"
                )
        elif status == ClaimStatus.UNVERIFIABLE.value:
            if for_count > 0 or against_count > 0:
                violations.append(
                    f"{PERSISTENCE_VIOLATION_PREFIX}: claim {claim_id or '<unknown>'} is UNVERIFIABLE but has polarized evidence (FOR={for_count}, AGAINST={against_count})"
                )

    return violations


def assert_persistable_analysis_state(state: dict[str, Any]) -> None:
    violations = validate_persistable_analysis_state(state)
    if violations:
        raise ValueError("; ".join(violations))


def verdict_conflict_reasons(verdict: str | None, aggregates: dict[str, Any]) -> list[str]:
    if not isinstance(verdict, str) or not verdict.strip():
        return ["empty_verdict"]

    lowered = verdict.lower()
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

    reasons: list[str] = []
    if supported_like > (contradicted_like + unresolved_like) and for_count >= against_count:
        if any(phrase in lowered for phrase in VERDICT_UNCERTAIN_PHRASES):
            reasons.append("verdict_too_uncertain_for_supported_distribution")

    if contradicted_like > supported_like and against_count > for_count:
        if any(phrase in lowered for phrase in VERDICT_OVERPOSITIVE_PHRASES):
            reasons.append("verdict_too_positive_for_contradicted_distribution")

    return reasons


def build_verdict_regeneration_prompt(
    *,
    score: int,
    risk: str,
    issues: list[str],
    aggregates: dict[str, Any],
    conflict_reasons: list[str],
    previous_verdict: str,
) -> str:
    status_counts = aggregates.get("status_counts") or {}
    evidence_counts = aggregates.get("evidence_counts") or {}
    issue_context = "\n".join(f"- {item}" for item in issues) if issues else "- none"
    conflict_context = "\n".join(f"- {item}" for item in conflict_reasons)
    return "\n".join(
        [
            f"Trust score: {score}",
            f"Hallucination risk: {risk}",
            f"Claim status counts: {status_counts}",
            f"Evidence polarity counts: {evidence_counts}",
            "Top issues:",
            issue_context,
            "Rejected prior verdict because it conflicted with the aggregated evidence distribution:",
            conflict_context,
            f"Previous verdict: {previous_verdict}",
            "Constraints: generate a verdict that aligns with the status and evidence counts.",
            "If SUPPORTED dominates and AGAINST is low, do not claim insufficient information.",
            "Write a concise verdict in 1-3 sentences.",
        ]
    )


def build_policy_observability_snapshot(
    *,
    claims: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
    reason_codes: list[str],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {
        ClaimStatus.SUPPORTED.value: 0,
        ClaimStatus.PARTIALLY_SUPPORTED.value: 0,
        ClaimStatus.CONTRADICTED.value: 0,
        ClaimStatus.UNSUPPORTED.value: 0,
        ClaimStatus.UNVERIFIABLE.value: 0,
    }
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        status = _claim_status(claim.get("status"))
        status_counts[status] += 1

    evidence_counts: dict[str, int] = {"for": 0, "against": 0, "unknown": 0}
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        polarity = _evidence_polarity(item.get("polarity"))
        if polarity == EvidencePolarity.FOR.value:
            evidence_counts["for"] += 1
        elif polarity == EvidencePolarity.AGAINST.value:
            evidence_counts["against"] += 1
        else:
            evidence_counts["unknown"] += 1

    total_claims = sum(status_counts.values())
    parse_failure_count = reason_codes.count("parse_failure")
    fallback_usage_count = sum(1 for code in reason_codes if code in FALLBACK_REASON_CODES)
    contradicted_count = status_counts[ClaimStatus.CONTRADICTED.value]

    contradiction_ratio = contradicted_count / total_claims if total_claims else 0.0
    fallback_usage_rate = fallback_usage_count / total_claims if total_claims else 0.0
    parse_failure_rate = parse_failure_count / total_claims if total_claims else 0.0

    alerts: list[str] = []
    if total_claims and contradiction_ratio >= 0.25:
        alerts.append("contradiction_ratio_high")
    if total_claims and fallback_usage_rate >= 0.25:
        alerts.append("fallback_usage_high")
    if total_claims and parse_failure_rate >= 0.10:
        alerts.append("parse_failure_rate_high")

    return {
        "status_counts": status_counts,
        "evidence_counts": evidence_counts,
        "contradiction_ratio": round(contradiction_ratio, 4),
        "fallback_usage_rate": round(fallback_usage_rate, 4),
        "parse_failure_rate": round(parse_failure_rate, 4),
        "alerts": alerts,
    }