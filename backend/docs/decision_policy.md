# Decision Policy Contract

This backend treats claim verification, verdict generation, persistence, and observability as one contract.

## Claim and Evidence Rules

- `SUPPORTED` claims must have at least one `FOR` evidence item and no `AGAINST` evidence items.
- `PARTIALLY_SUPPORTED` claims must have mixed evidence with at least one `FOR` and one `AGAINST` item.
- `CONTRADICTED` claims must have at least one `AGAINST` evidence item and no `FOR` evidence items.
- `UNSUPPORTED` and `UNVERIFIABLE` claims must not persist polarized evidence.

## Verdict Rules

- The Judge rejects verdict text that conflicts with the aggregate claim and evidence distribution.
- Conflicting verdicts are regenerated once with explicit conflict reasons.
- If regeneration still conflicts, the Judge falls back to a deterministic verdict summary.

## Observability Rules

- Track contradiction ratio, fallback usage rate, and parse failure rate for verifier output.
- Alert thresholds:
  - contradiction ratio `>= 0.25`
  - fallback usage rate `>= 0.25`
  - parse failure rate `>= 0.10`

## Release Canary Coverage

- Keep the golden Apollo mission fixture in sync with the policy contract.
- Keep the canary suite in `backend/tests/test_release_canaries.py` aligned with verifier and judge invariants.