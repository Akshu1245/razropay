from datetime import datetime, timezone

from bailiff.domain import Decision
from bailiff.evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from bailiff.state_resolution import (
    CanonicalFinancialState,
    ResolutionAction,
    StateHypothesis,
    evaluate_recovery_preflight,
)

NOW = datetime(2026, 8, 26, tzinfo=timezone.utc)


def evidence(evidence_id: str, source: EvidenceSource, state: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        entity_id=evidence_id,
        observed_state=state,
        observed_at=NOW,
        fetched_at=NOW,
        raw_hash=f"sha256:{evidence_id}",
        trust_tier=TrustTier.PROVIDER_CURRENT,
    )


def test_high_confidence_terminal_failure_can_stop_but_never_authorize_money():
    bundle = EvidenceBundle(
        "case_terminal",
        "corr_terminal",
        (
            evidence("E1", EvidenceSource.PAYMENT_API, "failed"),
            evidence("E2", EvidenceSource.MANDATE_API, "active"),
        ),
    )
    hypothesis = StateHypothesis(
        state=CanonicalFinancialState.TERMINAL_FAILURE,
        confidence=0.94,
        supporting_evidence=("E1",),
    )

    verdict = evaluate_recovery_preflight(bundle, hypothesis)

    assert verdict.decision is Decision.STOP
    assert verdict.state is CanonicalFinancialState.TERMINAL_FAILURE
    assert verdict.resolution_action is ResolutionAction.STOP_RECOVERY
    assert verdict.recovery_action_allowed is False
    assert verdict.reason_codes == ("AI_TERMINAL_FAILURE",)


def test_low_confidence_terminal_interpretation_abstains_instead_of_permanent_stop():
    bundle = EvidenceBundle(
        "case_terminal_low",
        "corr_terminal_low",
        (
            evidence("E1", EvidenceSource.PAYMENT_API, "failed"),
            evidence("E2", EvidenceSource.MANDATE_API, "active"),
        ),
    )
    hypothesis = StateHypothesis(
        state=CanonicalFinancialState.TERMINAL_FAILURE,
        confidence=0.55,
        supporting_evidence=("E1",),
        unknowns=("issuer_semantics",),
    )

    verdict = evaluate_recovery_preflight(bundle, hypothesis)

    assert verdict.decision is Decision.ABSTAIN
    assert verdict.resolution_action is ResolutionAction.HUMAN_REVIEW
    assert verdict.recovery_action_allowed is False
