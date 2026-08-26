from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from bailiff.evidence import EvidenceSource, TrustTier
from bailiff.razorpay_client import RazorpayReadClient, RazorpayReadError

NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def test_fetch_payment_builds_current_provider_evidence_from_documented_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/payments/pay_test123"
        return httpx.Response(
            200,
            json={
                "id": "pay_test123",
                "entity": "payment",
                "status": "captured",
                "amount": 249900,
                "currency": "INR",
                "method": "upi",
                "order_id": "order_test123",
            },
        )

    client = httpx.Client(base_url="https://api.razorpay.com", transport=httpx.MockTransport(handler))
    snapshot = RazorpayReadClient(client=client).fetch_payment("pay_test123", fetched_at=NOW)

    assert snapshot.evidence.source is EvidenceSource.PAYMENT_API
    assert snapshot.evidence.entity_id == "pay_test123"
    assert snapshot.evidence.observed_state == "captured"
    assert snapshot.evidence.trust_tier is TrustTier.PROVIDER_CURRENT
    assert snapshot.evidence.raw_hash.startswith("sha256:")
    assert snapshot.evidence.attributes["amount"] == 249900
    assert snapshot.evidence.attributes["order_id"] == "order_test123"


def test_fetch_subscription_builds_current_provider_evidence_from_documented_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/subscriptions/sub_test123"
        return httpx.Response(
            200,
            json={
                "id": "sub_test123",
                "entity": "subscription",
                "status": "active",
                "plan_id": "plan_test123",
                "paid_count": 2,
                "remaining_count": 10,
                "payment_method": "upi",
            },
        )

    client = httpx.Client(base_url="https://api.razorpay.com", transport=httpx.MockTransport(handler))
    snapshot = RazorpayReadClient(client=client).fetch_subscription("sub_test123", fetched_at=NOW)

    assert snapshot.evidence.source is EvidenceSource.SUBSCRIPTION_API
    assert snapshot.evidence.observed_state == "active"
    assert snapshot.evidence.attributes["plan_id"] == "plan_test123"
    assert snapshot.evidence.attributes["paid_count"] == 2


def test_provider_error_fails_as_missing_truth_instead_of_fabricating_a_state():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"description": "temporarily unavailable"}})

    client = httpx.Client(base_url="https://api.razorpay.com", transport=httpx.MockTransport(handler))

    with pytest.raises(RazorpayReadError, match="state fetch failed"):
        RazorpayReadClient(client=client).fetch_payment("pay_test123", fetched_at=NOW)


def test_identifiers_are_validated_before_they_can_enter_a_request_path():
    client = httpx.Client(
        base_url="https://api.razorpay.com",
        transport=httpx.MockTransport(lambda _request: pytest.fail("request should never be sent")),
    )
    reader = RazorpayReadClient(client=client)

    with pytest.raises(ValueError, match="invalid Razorpay pay identifier"):
        reader.fetch_payment("../../secrets", fetched_at=NOW)
    with pytest.raises(ValueError, match="invalid Razorpay sub identifier"):
        reader.fetch_subscription("pay_wrongprefix", fetched_at=NOW)


def test_live_client_requires_credentials_but_test_injected_client_does_not(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    with pytest.raises(RazorpayReadError, match="RAZORPAY_KEY_ID"):
        _ = RazorpayReadClient().client

    injected = httpx.Client(
        base_url="https://api.razorpay.com",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={})),
    )
    assert RazorpayReadClient(client=injected).client is injected
