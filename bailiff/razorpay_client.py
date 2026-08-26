from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any, Mapping

import httpx

from .evidence import EvidenceItem, EvidenceSource, TrustTier


_ID = re.compile(r"^[A-Za-z0-9_]+$")


class RazorpayReadError(RuntimeError):
    """Raised when current provider truth cannot be fetched safely."""


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    evidence: EvidenceItem
    payload: Mapping[str, Any]


class RazorpayReadClient:
    """Read-only Razorpay client used by RecoveryTruth's preflight.

    Only current-state GETs belong here. Recovery execution remains behind the
    existing MandateGuard provider boundary so a state resolver never acquires
    payment tools merely because it can read evidence.
    """

    def __init__(
        self,
        *,
        key_id: str | None = None,
        key_secret: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 8.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("RAZORPAY_API_BASE_URL") or "https://api.razorpay.com").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self._key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            if not self._key_id or not self._key_secret:
                raise RazorpayReadError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required for live/test-mode reads")
            self._client = httpx.Client(
                base_url=self.base_url,
                auth=(self._key_id, self._key_secret),
                timeout=self.timeout_seconds,
                headers={"Accept": "application/json", "User-Agent": "RecoveryTruth/0.1"},
            )
        return self._client

    @staticmethod
    def _validate_id(value: str, prefix: str) -> str:
        if not value or not value.startswith(prefix) or not _ID.fullmatch(value):
            raise ValueError(f"invalid Razorpay {prefix.rstrip('_')} identifier")
        return value

    @staticmethod
    def _hash_payload(payload: Mapping[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def _get(self, path: str) -> dict[str, Any]:
        try:
            response = self.client.get(path)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RazorpayReadError(f"Razorpay state fetch failed for {path}: {type(exc).__name__}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise RazorpayReadError(f"Razorpay returned non-JSON state for {path}") from exc
        if not isinstance(payload, dict):
            raise RazorpayReadError(f"Razorpay returned a non-object state for {path}")
        return payload

    def fetch_payment(self, payment_id: str, *, fetched_at: datetime | None = None) -> ProviderSnapshot:
        payment_id = self._validate_id(payment_id, "pay_")
        payload = self._get(f"/v1/payments/{payment_id}")
        fetched = fetched_at or datetime.now(timezone.utc)
        status = str(payload.get("status") or "unknown")
        attributes = {
            key: payload.get(key)
            for key in (
                "amount",
                "currency",
                "method",
                "order_id",
                "invoice_id",
                "error_code",
                "error_description",
                "error_source",
                "error_step",
                "error_reason",
            )
            if key in payload
        }
        evidence = EvidenceItem(
            evidence_id=f"payment_api:{payment_id}:{int(fetched.timestamp())}",
            source=EvidenceSource.PAYMENT_API,
            entity_id=payment_id,
            observed_state=status,
            observed_at=fetched,
            fetched_at=fetched,
            raw_hash=self._hash_payload(payload),
            trust_tier=TrustTier.PROVIDER_CURRENT,
            attributes=attributes,
        )
        return ProviderSnapshot(evidence=evidence, payload=payload)

    def fetch_subscription(self, subscription_id: str, *, fetched_at: datetime | None = None) -> ProviderSnapshot:
        subscription_id = self._validate_id(subscription_id, "sub_")
        payload = self._get(f"/v1/subscriptions/{subscription_id}")
        fetched = fetched_at or datetime.now(timezone.utc)
        status = str(payload.get("status") or "unknown")
        attributes = {
            key: payload.get(key)
            for key in (
                "plan_id",
                "customer_id",
                "payment_method",
                "paid_count",
                "remaining_count",
                "current_start",
                "current_end",
                "charge_at",
                "source",
            )
            if key in payload
        }
        evidence = EvidenceItem(
            evidence_id=f"subscription_api:{subscription_id}:{int(fetched.timestamp())}",
            source=EvidenceSource.SUBSCRIPTION_API,
            entity_id=subscription_id,
            observed_state=status,
            observed_at=fetched,
            fetched_at=fetched,
            raw_hash=self._hash_payload(payload),
            trust_tier=TrustTier.PROVIDER_CURRENT,
            attributes=attributes,
        )
        return ProviderSnapshot(evidence=evidence, payload=payload)
