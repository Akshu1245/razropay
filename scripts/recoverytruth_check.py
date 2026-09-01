from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os

from bailiff.recovery_runtime import RecoveryRequest, RecoveryTruthRuntime, recovery_reference
from bailiff.recovery_truth import ProviderEvidence, TruthState, WriteFence, resolve_financial_truth
from bailiff.razorpay_testmode import RazorpayConfigurationError, RazorpayTestModeClient


def evidence(
    status: str,
    entity_id: str = "pay_1",
    *,
    entity_type: str = "payment",
    authoritative: bool = True,
    observed_at: datetime | None = None,
) -> ProviderEvidence:
    return ProviderEvidence(
        source="razorpay_test_mode" if entity_type == "payment" else "merchant_current_state",
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        amount_minor=1000 if entity_type == "payment" else None,
        currency="INR" if entity_type == "payment" else None,
        reference_id="order_1",
        observed_at=observed_at or datetime.now(timezone.utc),
        authoritative=authoritative,
    )


@contextmanager
def env(**values: str):
    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class FakeProvider:
    def __init__(self) -> None:
        self.phase = 0
        self.create_calls = 0
        self.link = None

    def order_evidence(self, *, order_id: str, mandate_id: str | None = None, mandate_status: str | None = None):
        mandate = evidence(mandate_status or "active", mandate_id or "mandate_1", entity_type="mandate")
        if self.phase == 2:
            return (evidence("captured", "pay_late"), mandate)
        if self.phase == 3:
            return (evidence("authorized", "pay_inflight"), mandate)
        return (evidence("failed"), mandate)

    def create_payment_link_once(self, *, amount_minor: int, currency: str, reference_id: str, description: str):
        if self.link is None:
            self.create_calls += 1
            self.link = {
                "id": "plink_test_1",
                "short_url": "https://rzp.io/i/test",
                "amount": amount_minor,
                "currency": currency,
                "reference_id": reference_id,
                "accept_partial": False,
            }
        return self.link

    def verify_payment_link_capture(self, *, payment_link_id: str, expected_amount_minor: int, expected_currency: str, expected_reference_id: str):
        from bailiff.recovery_truth import verify_captured_payment

        payment = {
            "id": "pay_captured_1",
            "status": "captured",
            "amount": expected_amount_minor,
            "currency": expected_currency,
            "reference_id": expected_reference_id,
        }
        proof = verify_captured_payment(
            payment,
            expected_amount_minor=expected_amount_minor,
            expected_currency=expected_currency,
            expected_reference_id=expected_reference_id,
        )
        return proof, "postcondition_hash_1"


def main() -> int:
    now = datetime.now(timezone.utc)

    # Historical failure loses to fresh current financial truth.
    stale = evidence("failed", authoritative=False, observed_at=now - timedelta(minutes=5))
    captured = evidence("captured", "pay_2", observed_at=now)
    result = resolve_financial_truth([stale, captured])
    assert result.state == TruthState.PAID and not result.executable

    # A completed failed attempt may be considered for recovery, while a
    # payment still created/authorized/pending must block parallel collection.
    failed = evidence("failed")
    active = evidence("active", "mandate_1", entity_type="mandate")
    result = resolve_financial_truth([failed, active])
    assert result.state == TruthState.RECOVERABLE and result.executable
    assert resolve_financial_truth([evidence("authorized", "pay_3"), active]).state == TruthState.IN_FLIGHT
    assert resolve_financial_truth([evidence("pending", "pay_4"), active]).state == TruthState.IN_FLIGHT

    # Unknown and terminal states always abstain.
    assert resolve_financial_truth([evidence("mystery")]).state == TruthState.UNKNOWN
    assert resolve_financial_truth([failed, evidence("revoked", "mandate_1", entity_type="mandate")]).state == TruthState.TERMINAL

    fence = WriteFence.from_evidence([failed, active])
    allowed, reason = fence.check([captured, active])
    assert not allowed and reason == "SAFE_BLOCK_ALREADY_PAID"
    allowed, reason = fence.check([evidence("authorized", "pay_inflight"), active])
    assert not allowed and reason == "SAFE_BLOCK_IN_FLIGHT"

    # Full runtime path: resolve -> immediate re-read -> fence -> exactly-one
    # provider write -> independent captured-payment verification -> proof.
    provider = FakeProvider()
    runtime = RecoveryTruthRuntime(provider)
    request = RecoveryRequest(
        case_id="case_1",
        decision_id="dec_1",
        policy_version="mandateguard_policy_0.2",
        order_id="order_1",
        mandate_id="mandate_1",
        mandate_status="active",
        amount_minor=1000,
    )
    attempt = runtime.execute_customer_fallback(request)
    assert attempt.executed and attempt.receipt is not None
    assert provider.create_calls == 1
    assert len(attempt.receipt.reference_id) <= 40
    assert attempt.receipt.reference_id == recovery_reference("case_1")

    # Repeating the logical action must reuse the same provider reference.
    second = runtime.execute_customer_fallback(request)
    assert second.executed and second.receipt is not None
    assert second.receipt.payment_link_id == attempt.receipt.payment_link_id
    assert provider.create_calls == 1

    proof = runtime.verify_recovery(attempt.receipt)
    assert proof.payment_id == "pay_captured_1"
    assert proof.provider_action_id == "plink_test_1"
    assert proof.provider_action_type == "CREATE_PAYMENT_LINK_FALLBACK"
    assert proof.postcondition_evidence_hash == "postcondition_hash_1"
    assert proof.hash() == proof.hash()

    # TOCTOU: payment captures between diagnosis and write. Zero provider writes.
    provider = FakeProvider()
    original = provider.order_evidence
    calls = {"n": 0}

    def changing_to_paid(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            provider.phase = 2
        return original(**kwargs)

    provider.order_evidence = changing_to_paid  # type: ignore[method-assign]
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(request)
    assert not attempt.executed and attempt.reason_code == "SAFE_BLOCK_ALREADY_PAID"
    assert provider.create_calls == 0

    # TOCTOU: another payment becomes authorized between diagnosis and write.
    provider = FakeProvider()
    original = provider.order_evidence
    calls = {"n": 0}

    def changing_to_inflight(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            provider.phase = 3
        return original(**kwargs)

    provider.order_evidence = changing_to_inflight  # type: ignore[method-assign]
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(request)
    assert not attempt.executed and attempt.reason_code == "SAFE_BLOCK_IN_FLIGHT"
    assert provider.create_calls == 0

    # Live credentials are a hard failure. Test Mode only.
    with env(RAZORPAY_TEST_KEY_ID="rzp_live_forbidden", RAZORPAY_TEST_KEY_SECRET="secret"):
        try:
            RazorpayTestModeClient.from_env()
        except RazorpayConfigurationError:
            pass
        else:
            raise AssertionError("live Razorpay key was not refused")

    print("RecoveryTruth acceptance checks passed: freshness, in-flight block, fence, exactly-once action, proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
