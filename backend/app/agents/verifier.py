from __future__ import annotations

from collections import defaultdict
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


def _fallback_polarity(verdict: ClaimStatus) -> EvidencePolarity:
	if verdict in {ClaimStatus.CONTRADICTED, ClaimStatus.UNSUPPORTED, ClaimStatus.UNVERIFIABLE}:
		return EvidencePolarity.AGAINST
	return EvidencePolarity.FOR


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
	verdict: ClaimStatus,
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

	fallback = _fallback_polarity(verdict)
	return {index: explicit.get(index, fallback) for index in range(len(evidence_items))}


@timed_agent("verifier")
def verify_claims(state: AgentState) -> AgentState:
	"""Compare claims against evidence and assign claim verdicts plus evidence polarity."""
	claims = list(state.get("claims") or [])
	evidence_items = list(state.get("evidence") or [])

	if not claims:
		state["verified_claims"] = []
		state["claims"] = []
		state["evidence"] = evidence_items
		return state

	grouped_evidence = _group_evidence_by_claim(evidence_items)
	llm = get_llm(model_name=state.get("model_name") or "gemini-3.1-flash-lite")
	normalized_evidence = [dict(item) for item in evidence_items]
	verified_claims: list[dict[str, Any]] = []

	for claim in claims:
		if not isinstance(claim, dict):
			continue

		claim_copy = dict(claim)
		claim_id = claim_copy.get("id")
		claim_key = str(claim_id) if claim_id is not None else ""
		claim_evidence = grouped_evidence.get(claim_key, [])

		if not claim_key:
			claim_copy["status"] = ClaimStatus.UNVERIFIABLE.value
			claim_copy["confidence"] = _fallback_confidence(ClaimStatus.UNVERIFIABLE)
			verified_claims.append(claim_copy)
			continue

		if not claim_evidence:
			claim_copy["status"] = ClaimStatus.UNSUPPORTED.value
			claim_copy["confidence"] = _fallback_confidence(ClaimStatus.UNSUPPORTED)
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
		verdict = ClaimStatus.UNVERIFIABLE
		if isinstance(raw_content, str):
			try:
				payload = parse_json_response(raw_content)
				verdict = _normalize_verdict(payload.get("verdict"))
			except Exception:
				payload = {}
				verdict = ClaimStatus.UNVERIFIABLE
		elif isinstance(raw_content, dict):
			payload = raw_content
			verdict = _normalize_verdict(payload.get("verdict"))

		if verdict is ClaimStatus.UNVERIFIABLE and isinstance(payload.get("verdict"), str):
			verdict = _normalize_verdict(payload.get("verdict"))

		claim_copy["status"] = verdict.value
		claim_copy["confidence"] = _normalize_confidence(payload.get("confidence"), verdict)
		verified_claims.append(claim_copy)

		polarity_map = _extract_evidence_polarities(payload, claim_evidence, verdict)
		for index, evidence_item in enumerate(claim_evidence):
			evidence_id = str(evidence_item.get("id") or "")
			polarity = polarity_map.get(index, _fallback_polarity(verdict))
			for normalized_item in normalized_evidence:
				if str(normalized_item.get("id") or "") == evidence_id:
					normalized_item["polarity"] = polarity.value
					break

	state["verified_claims"] = verified_claims
	state["claims"] = verified_claims
	state["evidence"] = normalized_evidence
	return state
