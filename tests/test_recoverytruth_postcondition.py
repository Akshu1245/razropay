from __future__ import annotations

from datetime import datetime, timezone

import httpx

from bailiff.postcondition import PostconditionKind, PostconditionVerifier
from bailiff.razorpay_client import RazorpayReadClient

NOW = datetime(2026, 8, 26, 11, 0, tzinfo=timezone.utc)


def reader(responses: dict[str, tuple[int, dict[str, object]]]) -> RazorpayReadClient:
    def handler(request: httpx.Request) -> httpx.Response:
        status, payload = responses.get(request.url.path, (404, {"error": "not found"}))
        return httpx.Response(status, json=payload)

    return RazorpayReadClient(
        client=httpx.Client(
            base_url="https://api.razorpay.com",
            transport=httpx.MockTransport(handler),
        )
    )


def test_captured_payment_is_confirmed_and_never_retryable():
    verifier = PostconditionVerifier(
        razorpay=reader({"/v1/payments/pay_done": (200, {"id": "pay_done", "status": "captured"})})
    )

    verdict = verifier.verify(payment_id="pay_done", fetched_at=NOW)

    assert verdict.kind is PostconditionKind.PAYMENT_CONFIRMED
    assert verdict.money_moved is True
    assert verdict.retry_allowed is False
    assert len(verdict.evidence) == 1


def test_failed_payment_can_be_considered_for_a_new_attempt_but_only_after_fresh_policy_evaluation():
    verifier = PostconditionVerifier(
        razorpay=reader({"/v1/payments/pay_failed": (200, {"id": "pay_failed", "status": "failed"})})
    )

    verdict = verifier.verify(payment_id="pay_failed", fetched_at=NOW)

    assert verdict.kind is PostconditionKind.PAYMENT_FAILED
    assert verdict.money_moved is False
    assert verdict.retry_allowed is True
    assert verdict.reason_codes == ("PAYMENT_CONFIRMED_FAILED",)


def test_authorized_payment_is_not_called_success_but_still_blocks_second_money_action():
    verifier = PostconditionVerifier(
        razorpay=reader({"/v1/payments/pay_auth": (200, {"id": "pay_auth", "status": "authorized"})})
    )

    verdict = verifier.verify(payment_id="pay_auth", fetched_at=NOW)

    assert verdict.kind is PostconditionKind.PROVIDER_PENDING
    assert verdict.money_moved is True
    assert verdict.retry_allowed is False


def test_provider_fetch_failure_stays_unknown_and_fails_closed():
    verifier = PostconditionVerifier(
        razorpay=reader({"/v1/payments/pay_unknown": (503, {"error": "temporarily unavailable"})})
    )

    verdict = verifier.verify(payment_id="pay_unknown", fetched_at=NOW)

    assert verdict.kind is PostconditionKind.UNKNOWN
    assert verdict.money_moved is False
    assert verdict.retry_allowed is False
    assert verdict.evidence == ()


def test_captured_payment_with_pending_subscription_routes_entitlement_resolution_not_retry():
    verifier = PostconditionVerifier(
        razorpay=reader(
            {
                "/v1/payments/pay_done": (200, {"id": "pay_done", "status": "captured"}),
                "/v1/subscriptions/sub_pending": (
                    200,
                    {"id": "sub_pending", "status": "awaiting_authorization"},
                ),
            }
        )
    )

    verdict = verifier.verify(
        payment_id="pay_done",
        subscription_id="sub_pending",
        fetched_at=NOW,
    )

    assert verdict.kind is PostconditionKind.ENTITLEMENT_NOT_CONVERGED
    assert verdict.money_moved is True
    assert verdict.retry_allowed is False
    assert len(verdict.evidence) == 2


def test_captured_payment_with_subscription_fetch_failure_stays_unknown_but_remembers_money_moved():
    verifier = PostconditionVerifier(
        razorpay=reader(
            {
                "/v1/payments/pay_done": (200, {"id": "pay_done", "status": "captured"}),
                "/v1/subscriptions/sub_missing": (503, {"error": "down"}),
            }
        )
    )

    verdict = verifier.verify(
        payment_id="pay_done",
        subscription_id="sub_missing",
        fetched_at=NOW,
    )

    assert verdict.kind is PostconditionKind.UNKNOWN
    assert verdict.money_moved is True
    assert verdict.retry_allowed is False
    assert verdict.reason_codes == (
        "PAYMENT_CONFIRMED",
        "POSTCONDITION_SUBSCRIPTION_FETCH_UNRESOLVED",
    )
