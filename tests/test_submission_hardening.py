from __future__ import annotations

from pathlib import Path

from bailiff.claims import ClaimStatus, assert_required_claims, evaluate_claims
from bailiff.hardening import interpreter_ablation, refusal_regret


ROOT = Path(__file__).resolve().parents[1]


def metric(value: float) -> dict[str, float]:
    return {"mean": value}


def test_required_claims_resolve_from_committed_frozen_artifacts() -> None:
    results = assert_required_claims(ROOT)
    required = [result for result in results if result.required_for_release]
    assert required
    assert all(result.status is ClaimStatus.HELD for result in required)


def test_interpreter_ablation_compares_same_guarded_boundary() -> None:
    aggregate = [
        {
            "regime": "R3_AMBIGUOUS",
            "arm": "B2",
            "incremental_recovered_inr": metric(100.0),
            "legitimate_recovery_forgone_inr": metric(70.0),
            "provider_calls": metric(10.0),
            "human_reviews": metric(8.0),
            "abstention_rate": metric(0.0),
            "bounded_interpreter_influence_count": metric(0.0),
            "realized_harm_inr": metric(0.0),
            "prohibited_execution_rate": metric(0.0),
        },
        {
            "regime": "R3_AMBIGUOUS",
            "arm": "B3",
            "incremental_recovered_inr": metric(112.5),
            "legitimate_recovery_forgone_inr": metric(60.0),
            "provider_calls": metric(11.0),
            "human_reviews": metric(9.0),
            "abstention_rate": metric(0.12),
            "bounded_interpreter_influence_count": metric(20.0),
            "realized_harm_inr": metric(0.0),
            "prohibited_execution_rate": metric(0.0),
        },
    ]
    rows = interpreter_ablation(aggregate)
    assert len(rows) == 1
    row = rows[0]
    assert row["delta_recovered_inr"] == 12.5
    assert row["interpreter_adds_recovery"] is True
    assert row["safety_bound_unchanged"] is True
    assert row["b3_abstention_rate"] == 0.12


def test_refusal_regret_prices_each_non_provider_row_once() -> None:
    evidence = [
        {
            "provider_call_made": False,
            "decision": "abstain",
            "reason_codes": ["ABSTAIN", "INTERPRETER_CONFIDENCE_BELOW_THRESHOLD"],
            "legitimate_recovery_forgone_inr": 10.0,
            "protected_value_by_denial_inr": 15.0,
        },
        {
            "provider_call_made": False,
            "decision": "stop",
            "reason_codes": ["MANDATE_NOT_ACTIVE"],
            "legitimate_recovery_forgone_inr": 0.0,
            "protected_value_by_denial_inr": 25.0,
        },
        {
            "provider_call_made": True,
            "decision": "allow",
            "reason_codes": ["ALLOWED"],
            "legitimate_recovery_forgone_inr": 999.0,
            "protected_value_by_denial_inr": 999.0,
        },
    ]
    report = refusal_regret(evidence)
    assert report["non_provider_rows"] == 2
    assert report["legitimate_recovery_forgone_inr"] == 10.0
    assert report["protected_value_by_denial_inr"] == 40.0
    assert report["net_protection_minus_regret_inr"] == 30.0
    assert sum(item["rows"] for item in report["breakdown"]) == 2


def test_optional_provider_claims_are_not_fabricated_when_artifacts_are_absent() -> None:
    results = evaluate_claims(ROOT)
    optional = [result for result in results if not result.required_for_release]
    assert optional
    # In a checkout before the sanitized Test Mode artifacts are committed,
    # optional provider claims must remain MISSING rather than being inferred
    # from docs or simulator evidence. Once artifacts exist they resolve from
    # those files instead.
    for result in optional:
        assert result.status in {ClaimStatus.MISSING, ClaimStatus.HELD, ClaimStatus.REFUTED}
