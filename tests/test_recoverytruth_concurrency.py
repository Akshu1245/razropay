from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import time

from bailiff.razorpay_testmode import RazorpayTestModeClient


class ConcurrentStubClient(RazorpayTestModeClient):
    """Provider stub with a shared reference store and a deliberately slow POST."""

    def __init__(self) -> None:
        super().__init__(key_id="rzp_test_concurrency", key_secret="not-a-real-secret")
        self.link: dict[str, object] | None = None
        self.post_attempts = 0
        self._state_lock = Lock()

    def _request(self, method: str, path: str, **kwargs: object):
        if method == "GET" and path == "/payment_links/":
            params = kwargs.get("params")
            reference = params.get("reference_id") if isinstance(params, dict) else None
            with self._state_lock:
                matches = []
                if self.link is not None and self.link.get("reference_id") == reference:
                    matches = [dict(self.link)]
            return {"payment_links": matches}

        if method == "POST" and path == "/payment_links":
            payload = kwargs.get("json")
            assert isinstance(payload, dict)
            # Widen the race window. Without the process-local reference lock,
            # two barrier-released callers can both observe "not found" and
            # arrive here before either has published the provider object.
            time.sleep(0.05)
            with self._state_lock:
                self.post_attempts += 1
                assert self.link is None, "a second provider mutation reached the stub"
                self.link = {
                    "id": "plink_concurrent_1",
                    "short_url": "https://rzp.io/i/concurrent",
                    "amount": payload["amount"],
                    "currency": payload["currency"],
                    "reference_id": payload["reference_id"],
                    "accept_partial": False,
                }
                return dict(self.link)

        raise AssertionError(f"unexpected request {method} {path}")


def test_two_simultaneous_fallback_requests_share_one_provider_action() -> None:
    client = ConcurrentStubClient()
    start = Barrier(2)
    reference = "rt_concurrency_proof_0000000000000001"

    def create() -> dict[str, object]:
        start.wait(timeout=2)
        return dict(
            client.create_payment_link_once(
                amount_minor=1000,
                currency="INR",
                reference_id=reference,
                description="concurrency proof",
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        left_future = pool.submit(create)
        right_future = pool.submit(create)
        left = left_future.result(timeout=5)
        right = right_future.result(timeout=5)

    assert left["id"] == right["id"] == "plink_concurrent_1"
    assert left["reference_id"] == right["reference_id"] == reference
    assert client.post_attempts == 1
