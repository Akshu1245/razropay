from __future__ import annotations

from datetime import datetime, timezone

import httpx

from bailiff.domain import ConsentState, RecoveryEvent
from bailiff.evidence import EvidenceSource
from bailiff.evidence_assembler import EvidenceAssembler
from bailiff.razorpay_client import RazorpayReadClient

NOW = datetime(2026, 8, 26, 10, 30, tzinfo=timezone.utc)


def event() -> RecoveryEvent:
    return RecoveryEvent(
        event_id="evt_rt_webhook",
        merchant_id="merchant",
        customer_id="customer",
        mandate_id="mandate_1",
        scheduled_execution_id="sched_1",
        recovery_case_id="case_1",
        correlation_id="corr_1",
        amount_minor=499900,
        currency="INR",
        failure_code="BAD_REQUEST_ERROR",
        mandate_state="active",
        attempt_count=1,
        pre_debit_state="valid",
        event_time=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
        failure_payload={
            "provider": "razorpay",
            "provider_event": "payment.failed",
            "payment_id": "pay_test123",
            "subscription_id": "sub_test123",
            "error_reason": "payment_failed",
            "error_source": "bank",
            "error_step": "payment_authorization",
            "error_description": "Payment failed",
        },
        consent=ConsentState(email=True),
        source="razorpay_test_payload",
        payload_hash="sha256:webhook",
        normalized_failure_reason="UNKNOWN_OR_CONFLICTING",
        proposed_execution_at=NOW,
    )


def test_assembler_preserves_webhook_as_event_time_evidence_and_fetches_current_truth():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/payments/pay_test123":
            return httpx.Response(200, json={"id": "pay_test123", "status": "captured", "amount": 499900})
        if request.url.path == "/v1/subscriptions/sub_test123":
            return httpx.Response(200, json={"id": "sub_test123", "status": "pending", "paid_count": 0})
        raise AssertionError(f"unexpected request {request.url.path}")

    http = httpx.Client(base_url="https://api.razorpay.com", transport=httpx.MockTransport(handler))
    bundle = EvidenceAssembler(razorpay=RazorpayReadClient(client=http)).assemble(
        event=event(),
        current_mandate_state="active",
        merchant_entitlement_state="not_activated",
        fetched_at=NOW,
    )

    webhook = bundle.current(EvidenceSource.WEBHOOK)
    payment = bundle.current(EvidenceSource.PAYMENT_API)
    subscription = bundle.current(EvidenceSource.SUBSCRIPTION_API)
    mandate = bundle.current(EvidenceSource.MANDATE_API)
    entitlement = bundle.current(EvidenceSource.MERCHANT_ENTITLEMENT)

    assert webhook is not None and webhook.observed_at < NOW
    assert webhook.observed_state == "failed"
    assert payment is not None and payment.observed_state == "captured"
    assert subscription is not None and subscription.observed_state == "pending"
    assert mandate is not None and mandate.observed_state == "active"
    assert entitlement is not None and entitlement.observed_state == "not_activated"


def test_provider_fetch_failure_is_recorded_but_not_promoted_to_current_truth():
    http = httpx.Client(
        base_url="https://api.razorpay.com",
        transport=httpx.MockTransport(lambda _request: httpx.Response(503, json={"error": "down"})),
    )
    bundle = EvidenceAssembler(razorpay=RazorpayReadClient(client=http)).assemble(
        event=event(),
        current_mandate_state="active",
        fetched_at=NOW,
    )

    assert bundle.current(EvidenceSource.PAYMENT_API) is None
    assert bundle.current(EvidenceSource.SUBSCRIPTION_API) is None
    history = [item for item in bundle.items if item.source is EvidenceSource.RECOVERY_HISTORY]
    assert len(history) == 2
    assert all(item.observed_state == "provider_fetch_error" for item in history)


def test_without_a_read_client_the_bundle_never_fabricates_current_provider_state():
    bundle = EvidenceAssembler().assemble(
        event=event(),
        current_mandate_state="active",
        fetched_at=NOW,
    )

    assert bundle.current(EvidenceSource.WEBHOOK) is not None
    assert bundle.current(EvidenceSource.PAYMENT_API) is None
    assert bundle.current(EvidenceSource.SUBSCRIPTION_API) is None


def test_current_mandate_state_is_explicit_input_not_copied_from_old_webhook_event():
    stale = event()
    bundle = EvidenceAssembler().assemble(event=stale, fetched_at=NOW)
    assert bundle.current(EvidenceSource.MANDATE_API) is None

    with_current = EvidenceAssembler().assemble(
        event=stale,
        current_mandate_state="revoked",
        fetched_at=NOW,
    )
    mandate = with_current.current(EvidenceSource.MANDATE_API)
    assert mandate is not None
    assert mandate.observed_state == "revoked"
    assert mandate.observed_at == NOW
