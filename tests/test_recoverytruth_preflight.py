from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bailiff.domain import Decision
from bailiff.evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from bailiff.state_resolution import (
    CanonicalFinancialState,
    ResolutionAction,
    StateHypothesis,
    evaluate_recovery_preflight,
)

NOW = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)


def item(
    evidence_id: str,
    source: EvidenceSource,
    state: str,
    *,
    minutes: int,
    entity_id: str = "entity_1",
    trust: TrustTier | None = None,
) -> EvidenceItem:
    if trust is None:
        trust = (
            TrustTier.PROVIDER_CURRENT
            if source in {EvidenceSource.PAYMENT_API, EvidenceSource.SUBSCRIPTION_API, EvidenceSource.MANDATE_API}
            else TrustTier.PROVIDER_EVENT
        )
    observed = NOW + timedelta(minutes=minutes)
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        entity_id=entity_id,
        observed_state=state,
        observed_at=observed,
        fetched_at=observed + timedelta(seconds=1),
        raw_hash=f"sha256:{evidence_id}",
        trust_tier=trust,
    )


def bundle(*items: EvidenceItem) -> EvidenceBundle:
    return EvidenceBundle(
        recovery_case_id="case_rt_1",
        correlation_id="corr_rt_1",
        items=tuple(items),
    )


def recoverable(*supporting: str, confidence: float = 0.92) -> StateHypothesis:
    return StateHypothesis(
        state=CanonicalFinancialState.RECOVERABLE_FAILURE,
        confidence=confidence,
        supporting_evidence=tuple(supporting),
    )


def test_newer_captured_payment_overrides_older_failed_webhook_and_blocks_recovery():
    evidence = bundle(
        item("E1", EvidenceSource.WEBHOOK, "failed", minutes=0),
        item("E2", EvidenceSource.PAYMENT_API, "captured", minutes=4),
        item("E3", EvidenceSource.MANDATE_API, "active", minutes=4),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2"))

    assert verdict.decision is Decision.STOP
    assert verdict.state is CanonicalFinancialState.MONEY_ALREADY_MOVED
    assert verdict.resolution_action is ResolutionAction.STOP_RECOVERY
    assert verdict.recovery_action_allowed is False
    assert "MONEY_ALREADY_MOVED" in verdict.reason_codes


def test_captured_payment_with_inactive_entitlement_routes_reconciliation_not_recovery():
    evidence = bundle(
        item("E1", EvidenceSource.WEBHOOK, "failed", minutes=0),
        item("E2", EvidenceSource.PAYMENT_API, "captured", minutes=4),
        item("E3", EvidenceSource.SUBSCRIPTION_API, "awaiting_authorization", minutes=4),
        item(
            "E4",
            EvidenceSource.MERCHANT_ENTITLEMENT,
            "not_activated",
            minutes=4,
            trust=TrustTier.MERCHANT_STATE,
        ),
        item("E5", EvidenceSource.MANDATE_API, "active", minutes=4),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2", "E3", "E4"))

    assert verdict.decision is Decision.DENY
    assert verdict.state is CanonicalFinancialState.ENTITLEMENT_MISMATCH
    assert verdict.resolution_action is ResolutionAction.RECONCILE_ENTITLEMENT
    assert verdict.recovery_action_allowed is False
    assert verdict.reason_codes == ("MONEY_ALREADY_MOVED", "ENTITLEMENT_NOT_CONVERGED")


def test_current_failed_payment_active_mandate_and_high_confidence_hypothesis_allows_handoff():
    evidence = bundle(
        item("E1", EvidenceSource.WEBHOOK, "failed", minutes=0),
        item("E2", EvidenceSource.PAYMENT_API, "failed", minutes=3),
        item("E3", EvidenceSource.MANDATE_API, "active", minutes=3),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E2", "E3"))

    assert verdict.decision is Decision.ALLOW
    assert verdict.state is CanonicalFinancialState.RECOVERABLE_FAILURE
    assert verdict.resolution_action is ResolutionAction.PROCEED_TO_RECOVERY
    assert verdict.recovery_action_allowed is True


def test_low_confidence_hypothesis_abstains_and_cannot_reach_money_boundary():
    evidence = bundle(
        item("E1", EvidenceSource.PAYMENT_API, "failed", minutes=3),
        item("E2", EvidenceSource.MANDATE_API, "active", minutes=3),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2", confidence=0.51))

    assert verdict.decision is Decision.ABSTAIN
    assert verdict.resolution_action is ResolutionAction.HUMAN_REVIEW
    assert verdict.recovery_action_allowed is False
    assert verdict.reason_codes == ("AI_CONFIDENCE_BELOW_THRESHOLD",)


def test_missing_current_payment_state_abstains_instead_of_trusting_failure_webhook():
    evidence = bundle(
        item("E1", EvidenceSource.WEBHOOK, "failed", minutes=0),
        item("E2", EvidenceSource.MANDATE_API, "active", minutes=2),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1"))

    assert verdict.decision is Decision.ABSTAIN
    assert verdict.resolution_action is ResolutionAction.POLL_PROVIDER
    assert verdict.recovery_action_allowed is False
    assert verdict.reason_codes == ("CURRENT_PAYMENT_STATE_MISSING",)


def test_revoked_mandate_blocks_recovery_even_if_model_is_max_confident():
    evidence = bundle(
        item("E1", EvidenceSource.PAYMENT_API, "failed", minutes=3),
        item("E2", EvidenceSource.MANDATE_API, "revoked", minutes=4),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2", confidence=1.0))

    assert verdict.decision is Decision.DENY
    assert verdict.state is CanonicalFinancialState.MANDATE_NOT_ACTIONABLE
    assert verdict.recovery_action_allowed is False


def test_model_cannot_override_captured_payment_even_at_max_confidence():
    evidence = bundle(
        item("E1", EvidenceSource.PAYMENT_API, "captured", minutes=4),
        item("E2", EvidenceSource.MANDATE_API, "active", minutes=4),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2", confidence=1.0))

    assert verdict.decision is not Decision.ALLOW
    assert verdict.recovery_action_allowed is False


def test_hypothesis_cannot_invent_evidence_references():
    evidence = bundle(
        item("E1", EvidenceSource.PAYMENT_API, "failed", minutes=3),
        item("E2", EvidenceSource.MANDATE_API, "active", minutes=3),
    )
    hypothesis = recoverable("E1", "E404")

    with pytest.raises(ValueError, match="unknown evidence IDs"):
        evaluate_recovery_preflight(evidence, hypothesis)


def test_duplicate_evidence_ids_are_rejected():
    first = item("E1", EvidenceSource.WEBHOOK, "failed", minutes=0)
    second = item("E1", EvidenceSource.PAYMENT_API, "failed", minutes=1)

    with pytest.raises(ValueError, match="evidence IDs must be unique"):
        bundle(first, second)


def test_latest_item_per_source_is_used_not_first_arrival():
    evidence = bundle(
        item("E1", EvidenceSource.PAYMENT_API, "failed", minutes=1),
        item("E2", EvidenceSource.PAYMENT_API, "captured", minutes=5),
        item("E3", EvidenceSource.MANDATE_API, "active", minutes=5),
    )
    verdict = evaluate_recovery_preflight(evidence, recoverable("E1", "E2", "E3"))

    assert verdict.decision is Decision.STOP
    assert verdict.state is CanonicalFinancialState.MONEY_ALREADY_MOVED
    assert verdict.recovery_action_allowed is False
