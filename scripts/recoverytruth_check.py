from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os

from bailiff.recovery_truth import ProviderEvidence, RecoveryProof, TruthState, WriteFence, resolve_financial_truth, verify_captured_payment
from bailiff.razorpay_testmode import RazorpayConfigurationError, RazorpayTestModeClient


def evidence(status: str, entity_id: str = "pay_1") -> ProviderEvidence:
    return ProviderEvidence(
        source="razorpay_test_mode",
        entity_type="payment",
        entity_id=entity_id,
        status=status,
        amount_minor=1000,
        currency="INR",
        reference_id="case_1",
        observed_at=datetime.now(timezone.utc),
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


def main() -> int:
    result = resolve_financial_truth([evidence("failed"), evidence("captured", "pay_2")])
    assert result.state == TruthState.CONFLICT and not result.executable

    result = resolve_financial_truth([evidence("failed"), evidence("authorized", "pay_2")])
    assert result.state == TruthState.RECOVERABLE and result.executable

    result = resolve_financial_truth([evidence("mystery")])
    assert result.state == TruthState.UNKNOWN and not result.executable

    fence = WriteFence.from_evidence([evidence("failed")])
    allowed, reason = fence.check([evidence("captured")])
    assert not allowed and reason == "SAFE_BLOCK_ALREADY_PAID"

    fence = WriteFence.from_evidence([evidence("authorized")])
    allowed, reason = fence.check([evidence("pending")])
    assert not allowed and reason == "SAFE_BLOCK_STATE_CHANGED_BEFORE_WRITE"

    captured = verify_captured_payment(
        {"id": "pay_1", "status": "captured", "amount": 1000, "currency": "INR", "reference_id": "case_1"},
        expected_amount_minor=1000,
        expected_currency="INR",
        expected_reference_id="case_1",
    )
    assert captured.captured

    proof = RecoveryProof("case_1", "dec_1", "v1", "RECOVERABLE", "abc", "plink_1", "pay_1", 1000, "INR", "case_1")
    changed = RecoveryProof("case_1", "dec_1", "v1", "RECOVERABLE", "abc", "plink_1", "pay_1", 1001, "INR", "case_1")
    assert proof.hash() != changed.hash()

    with env(RAZORPAY_TEST_KEY_ID="rzp_live_forbidden", RAZORPAY_TEST_KEY_SECRET="secret"):
        try:
            RazorpayTestModeClient.from_env()
        except RazorpayConfigurationError:
            pass
        else:
            raise AssertionError("live Razorpay key was not refused")

    print("RecoveryTruth acceptance checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
