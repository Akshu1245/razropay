from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bailiff.recovery_truth import (
    ProviderEvidence,
    RecoveryProof,
    TruthState,
    WriteFence,
    resolve_financial_truth,
    verify_captured_payment,
)
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


def test_captured_state_has_authority_over_failed_event():
    result = resolve_financial_truth([evidence("failed"), evidence("captured", "pay_2")])
    assert result.state == TruthState.CONFLICT
    assert not result.executable


def test_recoverable_state_requires_no_captured_payment():
    result = resolve_financial_truth([evidence("failed"), evidence("authorized", "pay_2")])
    assert result.state == TruthState.RECOVERABLE
    assert result.executable


def test_unknown_provider_state_abstains():
    result = resolve_financial_truth([evidence("mystery")])
    assert result.state == TruthState.UNKNOWN
    assert not result.executable


def test_write_fence_blocks_when_payment_becomes_captured():
    initial = [evidence("failed")]
    fence = WriteFence.from_evidence(initial)
    allowed, reason = fence.check([evidence("captured")])
    assert not allowed
    assert reason == "SAFE_BLOCK_ALREADY_PAID"


def test_write_fence_blocks_any_state_change_before_write():
    initial = [evidence("failed")]
    fence = WriteFence.from_evidence(initial)
    allowed, reason = fence.check([evidence("authorized")])
    assert not allowed
    assert reason == "SAFE_BLOCK_STATE_CHANGED_BEFORE_WRITE"


def test_captured_payment_proof_binds_amount_currency_and_reference():
    proof = verify_captured_payment(
        {"id": "pay_1", "status": "captured", "amount": 1000, "currency": "INR", "reference_id": "case_1"},
        expected_amount_minor=1000,
        expected_currency="INR",
        expected_reference_id="case_1",
    )
    assert proof.captured
    with pytest.raises(ValueError, match="amount mismatch"):
        verify_captured_payment(
            {"id": "pay_1", "status": "captured", "amount": 999, "currency": "INR", "reference_id": "case_1"},
            expected_amount_minor=1000,
            expected_currency="INR",
            expected_reference_id="case_1",
        )


def test_recovery_proof_is_tamper_evident():
    proof = RecoveryProof("case_1", "dec_1", "v1", "RECOVERABLE", "abc", "plink_1", "pay_1", 1000, "INR", "case_1")
    changed = RecoveryProof("case_1", "dec_1", "v1", "RECOVERABLE", "abc", "plink_1", "pay_1", 1001, "INR", "case_1")
    assert proof.hash() != changed.hash()


def test_live_razorpay_key_is_refused(monkeypatch):
    monkeypatch.setenv("RAZORPAY_TEST_KEY_ID", "rzp_live_forbidden")
    monkeypatch.setenv("RAZORPAY_TEST_KEY_SECRET", "secret")
    with pytest.raises(RazorpayConfigurationError, match="non-test"):
        RazorpayTestModeClient.from_env()
