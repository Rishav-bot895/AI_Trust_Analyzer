from __future__ import annotations

from collections import defaultdict
import logging
import math
from typing import Any

from app.agents.base import (
	SYSTEM_PROMPT_FACTUALITY,
	SYSTEM_PROMPT_JSON_ONLY,
	get_llm,
	parse_json_response,
	timed_agent,
)
from app.schemas.agent_state import AgentState
from app.schemas.claim import ClaimStatus
from app.schemas.evidence import EvidencePolarity
from app.services.policy_guardrails import build_policy_observability_snapshot


logger = logging.getLogger(__name__)

VERIFIER_REASON_PARSE_FAILURE = "parse_failure"
VERIFIER_REASON_SCHEMA_MISMATCH = "schema_mismatch"
VERIFIER_REASON_NO_EVIDENCE = "no_evidence"
VERIFIER_REASON_LOW_SIGNAL = "low_signal"


VERIFIER_SYSTEM_PROMPT = "\n".join(
	[
		SYSTEM_PROMPT_FACTUALITY,
		"Compare each claim against its retrieved evidence.",
		"Classify each claim as SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, UNSUPPORTED, or UNVERIFIABLE.",
		"Classify each evidence item as FOR if it supports the claim or AGAINST if it contradicts the claim.",
		"Return JSON with shape: {'verdict': str, 'confidence': float, 'evidence_polarities': [...] }.",
		"Confidence must be a number between 0 and 1, inclusive.",
		SYSTEM_PROMPT_JSON_ONLY,
	]
)

_VERDICT_TO_STATUS: dict[str, ClaimStatus] = {
	"SUPPORTED": ClaimStatus.SUPPORTED,
	"PARTIALLY_SUPPORTED": ClaimStatus.PARTIALLY_SUPPORTED,
	"CONTRADICTED": ClaimStatus.CONTRADICTED,
	"UNSUPPORTED": ClaimStatus.UNSUPPORTED,
	"UNVERIFIABLE": ClaimStatus.UNVERIFIABLE,
}


def _normalize_verdict(raw_verdict: Any) -> ClaimStatus:
	if not isinstance(raw_verdict, str):
		return ClaimStatus.UNVERIFIABLE

	return _VERDICT_TO_STATUS.get(raw_verdict.strip().upper(), ClaimStatus.UNVERIFIABLE)


def _normalize_polarity(raw_polarity: Any) -> EvidencePolarity | None:
	if not isinstance(raw_polarity, str):
		return None

	polarity = raw_polarity.strip().upper()
	if polarity == EvidencePolarity.FOR.value:
		return EvidencePolarity.FOR
	if polarity == EvidencePolarity.AGAINST.value:
		return EvidencePolarity.AGAINST
	if polarity == EvidencePolarity.UNKNOWN.value:
		return EvidencePolarity.UNKNOWN
	return None


def _normalize_confidence(raw_confidence: Any, verdict: ClaimStatus) -> float:
	if isinstance(raw_confidence, str):
		try:
			raw_confidence = float(raw_confidence.strip())
		except ValueError:
			raw_confidence = None

	if isinstance(raw_confidence, (int, float)):
		confidence = float(raw_confidence)
		if confidence != confidence or confidence in (float("inf"), float("-inf")):
			confidence = _fallback_confidence(verdict)
		return max(0.0, min(1.0, confidence))

	return _fallback_confidence(verdict)


def _fallback_confidence(verdict: ClaimStatus) -> float:
	if verdict is ClaimStatus.SUPPORTED:
		return 0.92
	if verdict is ClaimStatus.CONTRADICTED:
		return 0.9
	if verdict is ClaimStatus.PARTIALLY_SUPPORTED:
		return 0.75
	if verdict is ClaimStatus.UNSUPPORTED:
		return 0.4
	return 0.25


def _fallback_polarity(verdict: ClaimStatus) -> EvidencePolarity | None:
	if verdict is ClaimStatus.CONTRADICTED:
		return EvidencePolarity.AGAINST
	if verdict is ClaimStatus.SUPPORTED:
		return EvidencePolarity.FOR
	return EvidencePolarity.UNKNOWN


def _source_authority_weight(evidence_item: dict[str, Any]) -> float:
	if _is_authoritative_source(evidence_item):
		return 1.2
	url = str(evidence_item.get("source_url") or "").lower()
	if any(host in url for host in ("reuters", "apnews", "bbc", "nytimes")):
		return 1.0
	return 0.7


def _token_set(text: str) -> set[str]:
	cleaned = "".join(char.lower() if (char.isalnum() or char.isspace()) else " " for char in text)
	return {token for token in cleaned.split() if len(token) > 2}


def _directness_score(claim_text: str, snippet: str) -> float:
	claim_tokens = _token_set(claim_text)
	if not claim_tokens:
		return 0.3
	snippet_tokens = _token_set(snippet)
	if not snippet_tokens:
		return 0.3
	overlap = len(claim_tokens.intersection(snippet_tokens)) / float(len(claim_tokens))
	return max(0.3, min(1.0, overlap))


def _status_from_weighted_scores(
	weighted_for: float,
	weighted_against: float,
	weighted_unknown: float,
	llm_verdict: ClaimStatus,
) -> ClaimStatus:
	total_signal = weighted_for + weighted_against
	total_weight = total_signal + weighted_unknown

	if total_weight < 0.05:
		if llm_verdict is ClaimStatus.UNVERIFIABLE:
			return ClaimStatus.UNVERIFIABLE
		return ClaimStatus.UNSUPPORTED

	if total_signal < 0.2 and weighted_unknown >= 0.3:
		return ClaimStatus.UNVERIFIABLE
	if total_signal <= 1e-6 and llm_verdict is ClaimStatus.UNVERIFIABLE:
		return ClaimStatus.UNVERIFIABLE

	if weighted_for >= 0.6 and weighted_against <= 0.05:
		return ClaimStatus.SUPPORTED
	if weighted_against >= 0.6 and weighted_for < 0.35:
		return ClaimStatus.CONTRADICTED
	if weighted_for >= 0.45 and weighted_against < 0.6:
		return ClaimStatus.PARTIALLY_SUPPORTED
	if total_signal < 0.35:
		if llm_verdict in {ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED} and weighted_for > 0.0:
			return ClaimStatus.PARTIALLY_SUPPORTED
		if llm_verdict is ClaimStatus.CONTRADICTED and weighted_against > 0.0:
			return ClaimStatus.CONTRADICTED
		return ClaimStatus.UNSUPPORTED
	if weighted_against > weighted_for:
		return ClaimStatus.CONTRADICTED
	return ClaimStatus.PARTIALLY_SUPPORTED


def _calibrated_confidence(
	status: ClaimStatus,
	weighted_for: float,
	weighted_against: float,
	weighted_unknown: float,
	relevance_mean: float,
	authority_mean: float,
	directness_mean: float,
	high_authority_support_count: int,
	llm_confidence: float,
) -> float:
	total_signal = weighted_for + weighted_against
	total_weight = total_signal + weighted_unknown
	agreement = 0.0
	if total_signal > 0:
		agreement = abs(weighted_for - weighted_against) / total_signal
	contradiction_penalty = 0.0
	if total_weight > 0:
		contradiction_penalty = weighted_against / total_weight
	authority_normalized = max(0.0, min(1.0, (authority_mean - 0.6) / 0.6))

	raw = (
		0.45 * agreement
		+ 0.25 * authority_normalized
		+ 0.20 * directness_mean
		+ 0.10 * relevance_mean
		- 0.35 * contradiction_penalty
	)
	calibrated = 1.0 / (1.0 + math.exp(-4.0 * (raw - 0.4)))
	confidence = (0.75 * calibrated) + (0.25 * llm_confidence)

	if status is ClaimStatus.SUPPORTED and high_authority_support_count >= 2 and weighted_against < 0.2:
		confidence = max(confidence, 0.78)
	if status is ClaimStatus.CONTRADICTED and weighted_against >= 0.6:
		confidence = max(confidence, 0.75)
	if status is ClaimStatus.UNVERIFIABLE:
		confidence = min(confidence, 0.55)
	if status is ClaimStatus.UNSUPPORTED:
		confidence = min(confidence, 0.50)

	return max(0.05, min(0.99, confidence))


def _normalize_payload(raw_content: Any) -> tuple[dict[str, Any], str | None]:
	"""Normalize model output into a payload dict and return an optional fallback reason."""
	if isinstance(raw_content, dict):
		return raw_content, None

	try:
		return parse_json_response(raw_content), None
	except Exception:
		text_attr = getattr(raw_content, "text", None)
		if isinstance(text_attr, str):
			try:
				return parse_json_response(text_attr), None
			except Exception:
				return {}, "json_parse_failed"
		return {}, "json_parse_failed"


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
	return any(phrase in text for phrase in phrases)


def _deterministic_polarity_sanity_check(claim_text: str, snippet: str) -> EvidencePolarity | None:
	"""Apply deterministic lexical cues as a safety net for polarity assignment."""
	normalized = f"{claim_text} {snippet}".lower()
	against_cues = (
		" did not ",
		" not ",
		" never ",
		" no evidence",
		" false",
		" incorrect",
		" debunk",
		" contradict",
	)
	for_cues = (
		" confirms ",
		" confirmed ",
		" according to ",
		" evidence shows ",
		" reports ",
		" official record ",
		" documented ",
	)

	if _contains_any(normalized, against_cues):
		return EvidencePolarity.AGAINST
	if _contains_any(normalized, for_cues):
		return EvidencePolarity.FOR
	return None


def _is_authoritative_source(evidence_item: dict[str, Any]) -> bool:
	url = str(evidence_item.get("source_url") or "").lower()
	title = str(evidence_item.get("source_title") or "").lower()
	if ".gov" in url or ".edu" in url:
		return True
	known = ("nasa", "who", "cdc", "nih", "britannica", "wikipedia")
	return any(token in url or token in title for token in known)


def _group_evidence_by_claim(evidence_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
	grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
	for item in evidence_items:
		claim_id = item.get("claim_id")
		if claim_id is None:
			continue
		grouped[str(claim_id)].append(item)
	return grouped


def _format_evidence_context(evidence_items: list[dict[str, Any]]) -> str:
	if not evidence_items:
		return "No evidence retrieved."

	lines: list[str] = []
	for index, item in enumerate(evidence_items, start=1):
		snippet = str(item.get("snippet") or "").strip()
		title = str(item.get("source_title") or "").strip()
		url = str(item.get("source_url") or "").strip()
		parts = [f"{index}.", snippet]
		if title:
			parts.append(f"[title: {title}]")
		if url:
			parts.append(f"[url: {url}]")
		lines.append(" ".join(part for part in parts if part))
	return "\n".join(lines)


def _extract_evidence_polarities(
	payload: dict[str, Any],
	evidence_items: list[dict[str, Any]],
) -> dict[int, EvidencePolarity]:
	explicit: dict[int, EvidencePolarity] = {}
	raw_polarities = payload.get("evidence_polarities")

	if isinstance(raw_polarities, dict):
		for key, value in raw_polarities.items():
			polarity = _normalize_polarity(value)
			if polarity is None:
				continue
			try:
				explicit[int(key)] = polarity
			except (TypeError, ValueError):
				continue
	elif isinstance(raw_polarities, list):
		for index, entry in enumerate(raw_polarities):
			if isinstance(entry, dict):
				polarity = _normalize_polarity(entry.get("polarity") or entry.get("label"))
				if polarity is None:
					continue

				evidence_index = entry.get("evidence_index", entry.get("index"))
				evidence_id = entry.get("evidence_id")
				if evidence_index is not None:
					try:
						explicit[int(evidence_index)] = polarity
					except (TypeError, ValueError):
						pass
					continue

				if evidence_id is not None:
					for item_index, evidence_item in enumerate(evidence_items):
						if str(evidence_item.get("id")) == str(evidence_id):
							explicit[item_index] = polarity
							break
					continue

				explicit[index] = polarity
			else:
				polarity = _normalize_polarity(entry)
				if polarity is not None:
					explicit[index] = polarity

	return explicit


@timed_agent("verifier")
def verify_claims(state: AgentState) -> AgentState:
	"""Compare claims against evidence and assign claim verdicts plus evidence polarity."""
	claims = list(state.get("claims") or [])
	evidence_items = list(state.get("evidence") or [])
	reason_code_counts: dict[str, int] = defaultdict(int)

	if not claims:
		state["verified_claims"] = []
		state["claims"] = []
		state["evidence"] = evidence_items
		state["verifier_reason_codes"] = []
		state["verifier_metrics"] = {
			"total_claims": 0,
			"supported_with_all_against_polarity_count": 0,
			"contradicted_with_all_for_polarity_count": 0,
		}
		return state

	grouped_evidence = _group_evidence_by_claim(evidence_items)
	llm = get_llm(model_name=state.get("model_name") or "gemini-3.1-flash-lite")
	normalized_evidence = [dict(item) for item in evidence_items]
	verified_claims: list[dict[str, Any]] = []

	for claim in claims:
		if not isinstance(claim, dict):
			continue

		claim_copy = dict(claim)
		claim_reason_codes: set[str] = set()
		verification_trace: dict[str, Any] = {
			"raw_verdict_source": "fallback",
			"fallback_reason": None,
			"polarity_source": "fallback",
			"reason_codes": [],
		}
		claim_id = claim_copy.get("id")
		claim_key = str(claim_id) if claim_id is not None else ""
		claim_evidence = grouped_evidence.get(claim_key, [])

		if not claim_key:
			claim_reason_codes.add(VERIFIER_REASON_SCHEMA_MISMATCH)
			claim_copy["status"] = ClaimStatus.UNVERIFIABLE.value
			claim_copy["confidence"] = _fallback_confidence(ClaimStatus.UNVERIFIABLE)
			verification_trace["fallback_reason"] = "missing_claim_id"
			verification_trace["reason_codes"] = sorted(claim_reason_codes)
			claim_copy["verification_trace"] = verification_trace
			for reason_code in claim_reason_codes:
				reason_code_counts[reason_code] += 1
			verified_claims.append(claim_copy)
			continue

		if not claim_evidence:
			claim_reason_codes.add(VERIFIER_REASON_NO_EVIDENCE)
			claim_copy["status"] = ClaimStatus.UNSUPPORTED.value
			claim_copy["confidence"] = _fallback_confidence(ClaimStatus.UNSUPPORTED)
			verification_trace["fallback_reason"] = "no_evidence"
			verification_trace["reason_codes"] = sorted(claim_reason_codes)
			claim_copy["verification_trace"] = verification_trace
			for reason_code in claim_reason_codes:
				reason_code_counts[reason_code] += 1
			verified_claims.append(claim_copy)
			continue

		prompt = "\n".join(
			[
				f"Claim: {claim_copy.get('text', '')}",
				"Evidence:",
				_format_evidence_context(claim_evidence),
				"Return JSON with a verdict field and an optional evidence_polarities field.",
				"Use FOR for supporting evidence and AGAINST for contradicting evidence.",
			]
		)

		response = llm.invoke(
			[
				{"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
				{"role": "user", "content": prompt},
			]
		)
		raw_content = getattr(response, "content", response)

		payload: dict[str, Any] = {}
		payload, normalize_error = _normalize_payload(raw_content)
		is_structured_payload = bool(payload)
		if normalize_error is not None:
			claim_reason_codes.add(VERIFIER_REASON_PARSE_FAILURE)
			verification_trace["fallback_reason"] = normalize_error
		elif not isinstance(payload, dict):
			claim_reason_codes.add(VERIFIER_REASON_SCHEMA_MISMATCH)
			verification_trace["fallback_reason"] = "unsupported_content_type"
			payload = {}

		llm_verdict = _normalize_verdict(payload.get("verdict"))

		if llm_verdict is ClaimStatus.UNVERIFIABLE and isinstance(payload.get("verdict"), str):
			llm_verdict = _normalize_verdict(payload.get("verdict"))
			if payload.get("verdict", "").strip().upper() not in _VERDICT_TO_STATUS:
				claim_reason_codes.add(VERIFIER_REASON_SCHEMA_MISMATCH)
				verification_trace["fallback_reason"] = "invalid_verdict_label"

		if llm_verdict is ClaimStatus.UNVERIFIABLE and claim_evidence:
			claim_reason_codes.add(VERIFIER_REASON_LOW_SIGNAL)
			if verification_trace["fallback_reason"] is None:
				verification_trace["fallback_reason"] = "insufficient_signal"

		llm_confidence = _normalize_confidence(payload.get("confidence"), llm_verdict)
		claim_copy["status"] = llm_verdict.value
		claim_copy["confidence"] = llm_confidence
		verification_trace["raw_verdict_source"] = "payload" if is_structured_payload and payload else "fallback"
		verified_claims.append(claim_copy)

		polarity_map = _extract_evidence_polarities(payload, claim_evidence)
		explicit_polarity_count = 0
		fallback_polarity_count = 0
		deterministic_override_count = 0
		claim_for_count = 0
		claim_against_count = 0
		claim_unknown_count = 0
		high_authority_support_count = 0
		has_high_conflict = False
		weighted_for = 0.0
		weighted_against = 0.0
		weighted_unknown = 0.0
		relevance_total = 0.0
		authority_total = 0.0
		directness_total = 0.0
		for index, evidence_item in enumerate(claim_evidence):
			evidence_id = str(evidence_item.get("id") or "")
			claim_text = str(claim_copy.get("text") or "")
			snippet = str(evidence_item.get("snippet") or "")
			deterministic_polarity = _deterministic_polarity_sanity_check(claim_text, snippet)
			has_explicit = index in polarity_map
			if index in polarity_map:
				polarity = polarity_map[index]
				explicit_polarity_count += 1
			else:
				polarity = _fallback_polarity(llm_verdict)
				fallback_polarity_count += 1

			if deterministic_polarity is not None and polarity is not None and deterministic_polarity is not polarity:
				polarity = deterministic_polarity
				deterministic_override_count += 1
			if deterministic_polarity is not None and polarity is None:
				polarity = deterministic_polarity
				deterministic_override_count += 1

			relevance = float(evidence_item.get("relevance_score") or 0.0)
			relevance = max(0.0, min(1.0, relevance))
			authority = _source_authority_weight(evidence_item)
			directness = _directness_score(claim_text, snippet)
			weight = relevance * authority * directness
			relevance_total += relevance
			authority_total += authority
			directness_total += directness
			if polarity is EvidencePolarity.FOR:
				claim_for_count += 1
				weighted_for += weight
				if relevance >= 0.75 and _is_authoritative_source(evidence_item):
					high_authority_support_count += 1
			elif polarity is EvidencePolarity.AGAINST:
				claim_against_count += 1
				weighted_against += weight
				if relevance >= 0.7:
					has_high_conflict = True
			else:
				claim_unknown_count += 1
				weighted_unknown += weight

			for normalized_item in normalized_evidence:
				if str(normalized_item.get("id") or "") == evidence_id:
					normalized_item["polarity"] = polarity.value if polarity is not None else None
					if deterministic_polarity is not None and (not has_explicit or deterministic_polarity is polarity):
						normalized_item["polarity_source"] = "deterministic"
					else:
						normalized_item["polarity_source"] = "explicit" if has_explicit else "fallback"
					break

		status = _status_from_weighted_scores(weighted_for, weighted_against, weighted_unknown, llm_verdict)
		if status is ClaimStatus.UNVERIFIABLE and not has_high_conflict and high_authority_support_count >= 2:
			status = ClaimStatus.SUPPORTED if claim_against_count == 0 else ClaimStatus.PARTIALLY_SUPPORTED
			verification_trace["fallback_reason"] = None
			claim_reason_codes.discard(VERIFIER_REASON_LOW_SIGNAL)

		evidence_count = len(claim_evidence) if claim_evidence else 1
		relevance_mean = relevance_total / float(evidence_count)
		authority_mean = authority_total / float(evidence_count)
		directness_mean = directness_total / float(evidence_count)
		confidence = _calibrated_confidence(
			status=status,
			weighted_for=weighted_for,
			weighted_against=weighted_against,
			weighted_unknown=weighted_unknown,
			relevance_mean=relevance_mean,
			authority_mean=authority_mean,
			directness_mean=directness_mean,
			high_authority_support_count=high_authority_support_count,
			llm_confidence=llm_confidence,
		)
		claim_copy["status"] = status.value
		claim_copy["confidence"] = confidence

		if fallback_polarity_count and explicit_polarity_count:
			polarity_source = "mixed"
		elif fallback_polarity_count:
			polarity_source = "fallback"
		elif deterministic_override_count:
			polarity_source = "deterministic"
		else:
			polarity_source = "explicit"
		verification_trace["polarity_source"] = polarity_source
		verification_trace["reason_codes"] = sorted(claim_reason_codes)
		verification_trace["polarity_source_counts"] = {
			"explicit": explicit_polarity_count,
			"fallback": fallback_polarity_count,
			"deterministic_overrides": deterministic_override_count,
		}
		verification_trace["support_summary"] = {
			"for_count": claim_for_count,
			"against_count": claim_against_count,
			"unknown_count": claim_unknown_count,
			"high_authority_support_count": high_authority_support_count,
			"weighted_for": round(weighted_for, 4),
			"weighted_against": round(weighted_against, 4),
			"weighted_unknown": round(weighted_unknown, 4),
			"relevance_mean": round(relevance_mean, 4),
			"authority_mean": round(authority_mean, 4),
			"directness_mean": round(directness_mean, 4),
			"llm_confidence": round(llm_confidence, 4),
			"calibrated_confidence": round(confidence, 4),
		}
		claim_copy["verification_trace"] = verification_trace
		for reason_code in claim_reason_codes:
			reason_code_counts[reason_code] += 1

	state["verified_claims"] = verified_claims
	state["claims"] = verified_claims
	state["evidence"] = normalized_evidence

	supported_with_all_against = 0
	contradicted_with_all_for = 0
	status_by_claim_id = {
		str(claim.get("id")): str(claim.get("status")) for claim in verified_claims if claim.get("id") is not None
	}
	polarities_by_claim_id: dict[str, list[str]] = defaultdict(list)
	for evidence in normalized_evidence:
		claim_id = evidence.get("claim_id")
		polarity = evidence.get("polarity")
		if claim_id is None or polarity is None:
			continue
		polarities_by_claim_id[str(claim_id)].append(str(polarity))

	for claim_id, claim_status in status_by_claim_id.items():
		claim_polarities = polarities_by_claim_id.get(claim_id, [])
		if claim_status == ClaimStatus.SUPPORTED.value and claim_polarities and all(
			polarity == EvidencePolarity.AGAINST.value for polarity in claim_polarities
		):
			supported_with_all_against += 1
		if claim_status == ClaimStatus.CONTRADICTED.value and claim_polarities and all(
			polarity == EvidencePolarity.FOR.value for polarity in claim_polarities
		):
			contradicted_with_all_for += 1

	reason_codes = sorted(reason_code_counts.keys())
	metrics = {
		"total_claims": len(verified_claims),
		"supported_with_all_against_polarity_count": supported_with_all_against,
		"contradicted_with_all_for_polarity_count": contradicted_with_all_for,
	}
	metrics.update(
		build_policy_observability_snapshot(
			claims=verified_claims,
			evidence_items=normalized_evidence,
			reason_codes=reason_codes,
		)
	)
	state["verifier_reason_codes"] = reason_codes
	state["verifier_metrics"] = metrics
	if metrics.get("alerts"):
		logger.warning(
			"verifier_policy_alerts analysis_id=%s alerts=%s metrics=%s",
			state.get("analysis_id"),
			metrics["alerts"],
			metrics,
		)
	logger.info(
		"verifier_monitoring_metrics analysis_id=%s reason_codes=%s metrics=%s",
		state.get("analysis_id"),
		dict(reason_code_counts),
		metrics,
	)
	return state
