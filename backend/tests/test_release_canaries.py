"""Release-gate canary suite for policy contract invariants."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.policy_guardrails import (
    assert_persistable_analysis_state,
    build_policy_observability_snapshot,
    verdict_conflict_reasons,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden" / "apollo_mission_golden_output.json"


def test_release_canary_apollo_fixture_is_policy_aligned():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)

    expected = fixture["expected"]
    snapshot = build_policy_observability_snapshot(
        claims=expected["claims"],
        evidence_items=expected["evidence"],
        reason_codes=[],
    )

    assert fixture["case_id"] == "apollo_mission_known_facts"
    assert expected["status"] == "COMPLETED"
    assert expected["hallucination_risk"] == "LOW"
    assert all(item["status"] == "SUPPORTED" for item in expected["claims"])
    assert all(item["polarity"] == "FOR" for item in expected["evidence"])
    assert snapshot["alerts"] == []
    assert verdict_conflict_reasons(
        "Most claims are supported by available evidence.",
        {
            "status_counts": {
                "SUPPORTED": 2,
                "PARTIALLY_SUPPORTED": 0,
                "CONTRADICTED": 0,
                "UNSUPPORTED": 0,
                "UNVERIFIABLE": 0,
            },
            "evidence_counts": {"for": 2, "against": 0, "unknown": 0},
        },
    ) == []
    assert_persistable_analysis_state(
        {
            "verified_claims": [
                {
                    "id": "c-1",
                    "status": "SUPPORTED",
                }
            ],
            "evidence": [
                {
                    "claim_id": "c-1",
                    "polarity": "FOR",
                }
            ],
        }
    )


def test_release_canary_observability_flags_policy_regressions():
    snapshot = build_policy_observability_snapshot(
        claims=[
            {"id": "c-1", "status": "CONTRADICTED"},
            {"id": "c-2", "status": "CONTRADICTED"},
        ],
        evidence_items=[
            {"claim_id": "c-1", "polarity": "AGAINST"},
            {"claim_id": "c-2", "polarity": "AGAINST"},
        ],
        reason_codes=["parse_failure", "no_evidence"],
    )

    assert snapshot["contradiction_ratio"] == 1.0
    assert snapshot["fallback_usage_rate"] == 1.0
    assert snapshot["parse_failure_rate"] == 0.5
    assert "contradiction_ratio_high" in snapshot["alerts"]
    assert "fallback_usage_high" in snapshot["alerts"]


def test_release_canary_rejects_contradictory_persistence_state():
    contradictory_state = {
        "verified_claims": [
            {"id": "c-1", "status": "SUPPORTED"},
        ],
        "evidence": [
            {"claim_id": "c-1", "polarity": "AGAINST"},
        ],
    }

    with pytest.raises(ValueError, match="policy_guardrail_violation"):
        assert_persistable_analysis_state(contradictory_state)