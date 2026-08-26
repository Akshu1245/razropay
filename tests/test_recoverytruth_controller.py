from __future__ import annotations

from datetime import datetime, timezone

from bailiff.domain import ConsentState, Decision, RecoveryEvent
from bailiff.evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from bailiff.recoverytruth import RecoveryTruthController
from bailiff.replay import CommonOutcomeLedger
from bailiff.resolver import DeterministicStateResolver

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def event(**changes) -> RecoveryEvent:
    base = dict(
        event_id="evt_rt",
        merchant_id="merchant",
        customer_id="customer",
        mandate_id="mandate_rt",
        scheduled_execution_id="scheduled_rt",
        recovery_case_id="case_rt",
        correlation_id="corr_rt",
        amount_minor=249900,
        currency="INR",
        failure_code="U30",
        mandate_state="active",
        attempt_count=1,
        pre_debit_state="valid",
        event_time=NOW,
        failure_payload={"error_reason": "insufficient_funds"},
        mcc="5817",
        consent=ConsentState(email=True),
        normalized_failure_reason="INSUFFICIENT_FUNDS",
        proposed_execution_at=datetime(2026, 1, 2, 3, tzinfo=timezone.utc),
    )
    base.update(changes)
    return RecoveryEvent(**base)


def evidence(evidence_id: str, source: EvidenceSource, state: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        entity_id=f"entity:{evidence_id}",
        observed_state=state,
        observed_at=NOW,
        fetched_at=NOW,
        raw_hash=f"sha256:{evidence_id}",
        trust_tier=(
            TrustTier.PROVIDER_CURRENT
            if source in {EvidenceSource.PAYMENT_API, EvidenceSource.MANDATE_API}
            else TrustTier.PROVIDER_EVENT
        ),
    )


def bundle(e: RecoveryEvent, *items: EvidenceItem) -> EvidenceBundle:
    return EvidenceBundle(e.recovery_case_id, e.correlation_id, tuple(items))


def ledger(e: RecoveryEvent) -> CommonOutcomeLedger:
    return CommonOutcomeLedger.from_seed(seed=73, case_ids=[e.recovery_case_id])


def test_abstain_path_never_constructs_a_mandateguard_policy_run():
    e = event()
    evidence_bundle = bundle(
        e,
        evidence("E1", EvidenceSource.WEBHOOK, "failed"),
        evidence("E2", EvidenceSource.MANDATE_API, "active"),
    )

    run = RecoveryTruthController().run(event=e, evidence=evidence_bundle, ledger=ledger(e))

    assert run.preflight.decision is Decision.ABSTAIN
    assert run.preflight.recovery_action_allowed is False
    assert run.policy_run is None
    assert run.provider_result is None


def test_already_paid_path_never_constructs_a_mandateguard_policy_run():
    e = event()
    evidence_bundle = bundle(
        e,
        evidence("E1", EvidenceSource.WEBHOOK, "failed"),
        evidence("E2", EvidenceSource.PAYMENT_API, "captured"),
        evidence("E3", EvidenceSource.MANDATE_API, "active"),
    )

    run = RecoveryTruthController().run(event=e, evidence=evidence_bundle, ledger=ledger(e))

    assert run.preflight.decision is Decision.STOP
    assert run.policy_run is None
    assert run.provider_result is None


def test_resolved_recoverable_case_is_handed_to_existing_b2_kernel():
    e = event()
    evidence_bundle = bundle(
        e,
        evidence("E1", EvidenceSource.PAYMENT_API, "failed"),
        evidence("E2", EvidenceSource.MANDATE_API, "active"),
    )

    run = RecoveryTruthController(resolver=DeterministicStateResolver()).run(
        event=e,
        evidence=evidence_bundle,
        ledger=ledger(e),
    )

    assert run.preflight.decision is Decision.ALLOW
    assert run.preflight.recovery_action_allowed is True
    assert run.policy_run is not None
    assert run.policy_run.arm == "B2"
    assert run.policy_run.audit_verified is True
    if run.provider_result is not None:
        assert run.policy_run.decision.decision is Decision.ALLOW


def test_resolver_failure_fails_closed_before_mandateguard():
    e = event()
    evidence_bundle = bundle(
        e,
        evidence("E1", EvidenceSource.PAYMENT_API, "failed"),
        evidence("E2", EvidenceSource.MANDATE_API, "active"),
    )

    class BrokenResolver:
        def __call__(self, _bundle):
            raise RuntimeError("model unavailable")

    run = RecoveryTruthController(resolver=BrokenResolver()).run(
        event=e,
        evidence=evidence_bundle,
        ledger=ledger(e),
    )

    assert run.resolver_failed is True
    assert run.preflight.decision is Decision.ABSTAIN
    assert run.policy_run is None
    assert run.provider_result is None
    assert any(value.startswith("resolver_error:") for value in run.hypothesis.unknowns)
