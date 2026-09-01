from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from typing import Mapping

import httpx

from .recovery_truth import CapturedPaymentProof, ProviderEvidence, verify_captured_payment


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

    @staticmethod
    def _raw_hash(value: Mapping[str, object]) -> str:
        raw = json.dumps(dict(value), sort_keys=True, default=str, separators=(",", ":")).encode()
        return sha256(raw).hexdigest()

    def fetch_payment(self, payment_id: str) -> Mapping[str, object]:
        if not payment_id.startswith("pay_"):
            raise ValueError("invalid Razorpay payment id")
        return self._request("GET", f"/payments/{payment_id}")

    def fetch_order_payments(self, order_id: str) -> tuple[Mapping[str, object], ...]:
        if not order_id.startswith("order_"):
            raise ValueError("invalid Razorpay order id")
        data = self._request("GET", f"/orders/{order_id}/payments")
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Razorpay order payments response has invalid items")
        return tuple(item for item in items if isinstance(item, Mapping))

    def fetch_payment_link(self, payment_link_id: str) -> Mapping[str, object]:
        if not payment_link_id.startswith("plink_"):
            raise ValueError("invalid Razorpay payment link id")
        return self._request("GET", f"/payment_links/{payment_link_id}")

    def find_payment_link_by_reference(self, reference_id: str) -> Mapping[str, object] | None:
        if not reference_id or len(reference_id) > 40:
            raise ValueError("payment link reference_id must contain 1 to 40 characters")
        data = self._request("GET", "/payment_links/", params={"reference_id": reference_id})
        links = data.get("payment_links", [])
        if not isinstance(links, list):
            raise ValueError("Razorpay payment links response has invalid payment_links")
        matches = [link for link in links if isinstance(link, Mapping) and link.get("reference_id") == reference_id]
        if len(matches) > 1:
            raise RuntimeError("multiple payment links found for unique recovery reference")
        return matches[0] if matches else None

    def create_payment_link_once(
        self, *, amount_minor: int, currency: str, reference_id: str, description: str
    ) -> Mapping[str, object]:
        """Create a customer-initiated fallback collection link exactly once.

        This is intentionally not labelled an AutoPay debit retry. It is a
        separate recovery action. On an ambiguous POST timeout we reconcile by
        unique reference before returning control; callers must never blindly
        POST the same logical recovery again.
        """
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        if currency != "INR":
            raise ValueError("RecoveryTruth Test Mode fallback is INR only")
        existing = self.find_payment_link_by_reference(reference_id)
        if existing is not None:
            return existing
        payload = {
            "amount": amount_minor,
            "currency": currency,
            "reference_id": reference_id,
            "description": description,
            "accept_partial": False,
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {"recovery_reference": reference_id, "system": "RecoveryTruth"},
        }
        try:
            return self._request("POST", "/payment_links", json=payload)
        except (httpx.TimeoutException, httpx.NetworkError):
            reconciled = self.find_payment_link_by_reference(reference_id)
            if reconciled is not None:
                return reconciled
            raise

    @staticmethod
    def payment_evidence(payment: Mapping[str, object], *, authoritative: bool = True) -> ProviderEvidence:
        return ProviderEvidence(
            source="razorpay_test_mode",
            entity_type="payment",
            entity_id=str(payment.get("id") or ""),
            status=str(payment.get("status") or ""),
            amount_minor=int(payment.get("amount") or 0),
            currency=str(payment.get("currency") or ""),
            reference_id=str(payment.get("order_id") or ""),
            observed_at=datetime.now(timezone.utc),
            raw_hash=RazorpayTestModeClient._raw_hash(payment),
            authoritative=authoritative,
        )

    @staticmethod
    def mandate_evidence(*, mandate_id: str, status: str, reference_id: str = "") -> ProviderEvidence:
        return ProviderEvidence(
            source="merchant_current_state",
            entity_type="mandate",
            entity_id=mandate_id,
            status=status,
            reference_id=reference_id,
            observed_at=datetime.now(timezone.utc),
            authoritative=True,
        )

    def order_evidence(
        self, *, order_id: str, mandate_id: str | None = None, mandate_status: str | None = None
    ) -> tuple[ProviderEvidence, ...]:
        rows = [self.payment_evidence(payment) for payment in self.fetch_order_payments(order_id)]
        if mandate_id and mandate_status:
            rows.append(self.mandate_evidence(mandate_id=mandate_id, status=mandate_status, reference_id=order_id))
        return tuple(rows)

    def verify_payment_link_capture(
        self, *, payment_link_id: str, expected_amount_minor: int, expected_currency: str, expected_reference_id: str
    ) -> tuple[CapturedPaymentProof, str]:
        """Bind the Payment Link to the exact captured Razorpay payment.

        Razorpay documents that the Payment Link `payments` array is populated
        only with captured payments. We still fetch the referenced Payment
        object independently and verify its current `captured` status, amount
        and currency instead of trusting the link status alone.
        """
        link = self.fetch_payment_link(payment_link_id)
        link_raw_hash = self._raw_hash(link)
        if str(link.get("reference_id") or "") != expected_reference_id:
            raise ValueError("payment link reference mismatch")
        if int(link.get("amount") or 0) != expected_amount_minor:
            raise ValueError("payment link amount mismatch")
        if str(link.get("currency") or "") != expected_currency:
            raise ValueError("payment link currency mismatch")
        if bool(link.get("accept_partial", False)):
            raise ValueError("partial payment link is outside RecoveryTruth proof contract")

        payments = link.get("payments")
        if not isinstance(payments, list) or not payments:
            raise ValueError("no captured payment attached to payment link")
        if len(payments) != 1:
            raise ValueError("expected exactly one captured payment for non-partial recovery link")

        link_payment = payments[0]
        if not isinstance(link_payment, Mapping):
            raise ValueError("invalid captured payment entry on payment link")
        payment_id = str(link_payment.get("payment_id") or link_payment.get("id") or "")
        if not payment_id:
            raise ValueError("captured payment entry has no payment id")
        linked_plink = str(link_payment.get("payment_link_id") or "")
        if linked_plink and linked_plink != payment_link_id:
            raise ValueError("captured payment is bound to a different payment link")

        provider_payment = dict(self.fetch_payment(payment_id))
        payment_raw_hash = self._raw_hash(provider_payment)

        # The reference belongs to the verified Payment Link, not the Payment
        # entity. Add it only to a derived copy used by the local binding
        # verifier; the evidence hash below remains over raw provider bytes.
        bound_payment = dict(provider_payment)
        bound_payment["reference_id"] = expected_reference_id
        proof = verify_captured_payment(
            bound_payment,
            expected_amount_minor=expected_amount_minor,
            expected_currency=expected_currency,
            expected_reference_id=expected_reference_id,
        )
        binding = f"{link_raw_hash}:{payment_raw_hash}:{payment_link_id}:{payment_id}:{expected_reference_id}"
        postcondition_evidence_hash = sha256(binding.encode()).hexdigest()
        return proof, postcondition_evidence_hash
