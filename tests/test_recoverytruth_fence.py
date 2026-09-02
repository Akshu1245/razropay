"""Write-fence and provider-read attacks that used to live only in scripts/.

These are pytest so a green test.sh cannot skip them. Logical exactly-once in
RecoveryTruth is a single-process stub contract, not a distributed guarantee.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from bailiff.recovery_runtime import ExecutionState, RecoveryTruthRuntime

ROOT = Path(__file__).resolve().parents[1]


def _load_rt():
    spec = importlib.util.spec_from_file_location(
        "recoverytruth_check_for_pytest",
        ROOT / "scripts" / "recoverytruth_check.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def rt():
    return _load_rt()


def test_provider_read_failure_on_first_evidence_makes_zero_writes(rt):
    provider = rt.FakeProvider()
    provider.fail_read_at = 1
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert attempt.execution_state == ExecutionState.NOT_EXECUTED
    assert attempt.reason_code == "SAFE_BLOCK_PROVIDER_READ_ERROR"
    assert provider.write_attempts == 0


def test_provider_read_failure_at_prewrite_fence_makes_zero_writes(rt):
    provider = rt.FakeProvider()
    provider.fail_read_at = 2
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert attempt.execution_state == ExecutionState.NOT_EXECUTED
    assert attempt.reason_code == "SAFE_BLOCK_PREWRITE_PROVIDER_READ_ERROR"
    assert provider.write_attempts == 0


def test_write_time_toctou_captured_between_reads_makes_zero_writes(rt):
    provider = rt.FakeProvider()
    original = provider.order_evidence
    calls = {"n": 0}

    def changing_to_paid(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            provider.phase = 2
        return original(**kwargs)

    provider.order_evidence = changing_to_paid  # type: ignore[method-assign]
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert not attempt.executed
    assert attempt.reason_code == "SAFE_BLOCK_ALREADY_PAID"
    assert provider.write_attempts == 0


def test_write_time_toctou_in_flight_between_reads_makes_zero_writes(rt):
    provider = rt.FakeProvider()
    original = provider.order_evidence
    calls = {"n": 0}

    def changing_to_inflight(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            provider.phase = 3
        return original(**kwargs)

    provider.order_evidence = changing_to_inflight  # type: ignore[method-assign]
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert not attempt.executed
    assert attempt.reason_code == "SAFE_BLOCK_IN_FLIGHT"
    assert provider.write_attempts == 0


def test_ambiguous_write_is_unknown_and_leaves_no_receipt(rt):
    """A write timeout after send is UNKNOWN. Blind retry is the adapter test below."""
    provider = rt.FakeProvider()
    provider.ambiguous_write = True
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert attempt.execution_state == ExecutionState.WRITE_OUTCOME_UNKNOWN
    assert attempt.write_outcome_unknown
    assert attempt.reason_code == "PROVIDER_WRITE_OUTCOME_UNKNOWN"
    assert attempt.receipt is None
    assert provider.write_attempts == 1


def test_malformed_write_response_is_unknown_with_no_receipt(rt):
    provider = rt.FakeProvider()
    provider.malformed_write_response = True
    attempt = RecoveryTruthRuntime(provider).execute_customer_fallback(rt.request())
    assert attempt.execution_state == ExecutionState.WRITE_OUTCOME_UNKNOWN
    assert attempt.reason_code == "PROVIDER_WRITE_OUTCOME_UNKNOWN"
    assert attempt.receipt is None
    assert provider.write_attempts == 1


def test_payment_bound_to_another_order_is_refused(rt):
    mismatched = rt.StubRazorpayClient()
    mismatched.wrong_order_payment = True
    with pytest.raises(ValueError, match="another order"):
        mismatched.order_evidence(
            order_id="order_1",
            expected_amount_minor=1000,
            expected_currency="INR",
        )


def test_timeout_after_create_does_not_issue_a_second_post(rt):
    client = rt.StubRazorpayClient(post_mode="timeout_after_create")
    try:
        client.create_payment_link_once(
            amount_minor=1000,
            currency="INR",
            reference_id=rt.recovery_reference("case_1"),
            description="fallback",
        )
    except Exception:
        pass
    reconciled = client.create_payment_link_once(
        amount_minor=1000,
        currency="INR",
        reference_id=rt.recovery_reference("case_1"),
        description="fallback",
    )
    assert reconciled["id"] == "plink_contract_1"
    assert client.post_writes == 1
