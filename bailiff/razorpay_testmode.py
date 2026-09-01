from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from typing import Mapping

import httpx

from .recovery_truth import ProviderEvidence, verify_captured_payment


class RazorpayConfigurationError(RuntimeError):
    pass


@dataclass
class RazorpayTestModeClient:
    key_id: str
    key_secret: str
    base_url: str = "https://api.razorpay.com/v1"
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "RazorpayTestModeClient":
        key_id = os.getenv("RAZORPAY_TEST_KEY_ID", "")
        key_secret = os.getenv("RAZORPAY_TEST_KEY_SECRET", "")
        if not key_id or not key_secret:
            raise RazorpayConfigurationError("RAZORPAY_TEST_KEY_ID and RAZORPAY_TEST_KEY_SECRET are required")
        if not key_id.startswith("rzp_test_"):
            raise RazorpayConfigurationError("RecoveryTruth refuses non-test Razorpay credentials")
        return cls(key_id=key_id, key_secret=key_secret)

    def _request(self, method: str, path: str, **kwargs: object) -> Mapping[str, object]:
        with httpx.Client(auth=(self.key_id, self.key_secret), timeout=self.timeout_seconds) as client:
            response = client.request(method, f"{self.base_url}{path}", **kwargs)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, Mapping):
            raise ValueError("Razorpay response must be an object")
        return data

    def fetch_payment(self, payment_id: str) -> Mapping[str, object]:
        return self._request("GET", f"/payments/{payment_id}")

    def fetch_order_payments(self, order_id: str) -> tuple[Mapping[str, object], ...]:
        data = self._request("GET", f"/orders/{order_id}/payments")
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Razorpay order payments response has invalid items")
        return tuple(item for item in items if isinstance(item, Mapping))

    def fetch_payment_link(self, payment_link_id: str) -> Mapping[str, object]:
        return self._request("GET", f"/payment_links/{payment_link_id}")

    def find_payment_link_by_reference(self, reference_id: str) -> Mapping[str, object] | None:
        data = self._request("GET", "/payment_links/", params={"reference_id": reference_id})
        links = data.get("payment_links", [])
        if not isinstance(links, list):
            return None
        matches = [link for link in links if isinstance(link, Mapping) and link.get("reference_id") == reference_id]
        if len(matches) > 1:
            raise RuntimeError("multiple payment links found for unique recovery reference")
        return matches[0] if matches else None

    def create_payment_link_once(self, *, amount_minor: int, currency: str, reference_id: str, description: str) -> Mapping[str, object]:
        existing = self.find_payment_link_by_reference(reference_id)
        if existing is not None:
            return existing
        payload = {
            "amount": amount_minor,
            "currency": currency,
            "reference_id": reference_id,
            "description": description,
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {"recovery_reference": reference_id, "system": "RecoveryTruth"},
        }
        try:
            return self._request("POST", "/payment_links", json=payload)
        except httpx.TimeoutException:
            reconciled = self.find_payment_link_by_reference(reference_id)
            if reconciled is not None:
                return reconciled
            raise

    @staticmethod
    def payment_evidence(payment: Mapping[str, object]) -> ProviderEvidence:
        raw = json.dumps(dict(payment), sort_keys=True, default=str, separators=(",", ":")).encode()
        return ProviderEvidence(
            source="razorpay_test_mode",
            entity_type="payment",
            entity_id=str(payment.get("id") or ""),
            status=str(payment.get("status") or ""),
            amount_minor=int(payment.get("amount") or 0),
            currency=str(payment.get("currency") or ""),
            reference_id=str(payment.get("order_id") or ""),
            raw_hash=sha256(raw).hexdigest(),
        )

    def verify_payment_link_capture(self, *, payment_link_id: str, expected_amount_minor: int, expected_currency: str, expected_reference_id: str):
        link = self.fetch_payment_link(payment_link_id)
        if str(link.get("reference_id") or "") != expected_reference_id:
            raise ValueError("payment link reference mismatch")
        if int(link.get("amount") or 0) != expected_amount_minor:
            raise ValueError("payment link amount mismatch")
        if str(link.get("currency") or "") != expected_currency:
            raise ValueError("payment link currency mismatch")
        payments = link.get("payments")
        if not isinstance(payments, list) or not payments:
            raise ValueError("no captured payment attached to payment link")
        if len(payments) != 1:
            raise ValueError("expected exactly one captured payment for non-partial recovery link")
        payment = dict(payments[0])
        payment.setdefault("status", "captured")
        payment.setdefault("currency", expected_currency)
        payment.setdefault("reference_id", expected_reference_id)
        return verify_captured_payment(
            payment,
            expected_amount_minor=expected_amount_minor,
            expected_currency=expected_currency,
            expected_reference_id=expected_reference_id,
        )
