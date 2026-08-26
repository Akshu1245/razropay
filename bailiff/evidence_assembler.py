from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .domain import RecoveryEvent
from .evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from .razorpay_client import ProviderSnapshot, RazorpayReadClient, RazorpayReadError


class EvidenceAssembler:
    """Build the immutable RecoveryTruth evidence bundle for one recovery case."""

    def __init__(self, *, razorpay: RazorpayReadClient | None = None) -> None:
        self.razorpay = razorpay

    @staticmethod
    def webhook_item(event: RecoveryEvent) -> EvidenceItem:
        provider_event = str(event.failure_payload.get("provider_event") or "payment.failed")
        observed_state = "failed"
        if provider_event.endswith("charged") or provider_event.endswith("captured"):
            observed_state = "captured"
        elif provider_event.endswith("authenticated") or provider_event.endswith("active"):
            observed_state = "active"
        elif provider_event.endswith("pending"):
            observed_state = "pending"

        return EvidenceItem(
            evidence_id=f"webhook:{event.event_id}",
            source=EvidenceSource.WEBHOOK,
            entity_id=str(event.failure_payload.get("payment_id") or event.scheduled_execution_id),
            observed_state=observed_state,
            observed_at=event.event_time,
            fetched_at=event.event_time,
            raw_hash=event.payload_hash or f"event:{event.event_id}",
            trust_tier=TrustTier.PROVIDER_EVENT,
            attributes={
                key: event.failure_payload.get(key)
                for key in (
                    "provider_event",
                    "payment_id",
                    "subscription_id",
                    "error_code",
                    "error_reason",
                    "error_source",
                    "error_step",
                    "error_description",
                    "method",
                    "normalized_reason",
                )
                if event.failure_payload.get(key) is not None
            },
        )

    @staticmethod
    def current_mandate_item(
        event: RecoveryEvent,
        state: str,
        *,
        observed_at: datetime,
        source_label: str = "merchant_mandate_store",
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=f"mandate_state:{event.mandate_id}:{int(observed_at.timestamp())}",
            source=EvidenceSource.MANDATE_API,
            entity_id=event.mandate_id,
            observed_state=state,
            observed_at=observed_at,
            fetched_at=observed_at,
            raw_hash=f"project-state:{event.mandate_id}:{state}:{int(observed_at.timestamp())}",
            trust_tier=TrustTier.MERCHANT_STATE,
            attributes={"source_label": source_label},
        )

    @staticmethod
    def merchant_entitlement_item(
        event: RecoveryEvent,
        state: str,
        *,
        observed_at: datetime,
        entitlement_id: str | None = None,
    ) -> EvidenceItem:
        entity_id = entitlement_id or event.customer_id
        return EvidenceItem(
            evidence_id=f"merchant_entitlement:{entity_id}:{int(observed_at.timestamp())}",
            source=EvidenceSource.MERCHANT_ENTITLEMENT,
            entity_id=entity_id,
            observed_state=state,
            observed_at=observed_at,
            fetched_at=observed_at,
            raw_hash=f"project-state:{entity_id}:{state}:{int(observed_at.timestamp())}",
            trust_tier=TrustTier.MERCHANT_STATE,
        )

    @staticmethod
    def _fetch_error_item(event: RecoveryEvent, source: str, error: Exception, at: datetime) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=f"recovery_history:{source}:{int(at.timestamp())}",
            source=EvidenceSource.RECOVERY_HISTORY,
            entity_id=event.recovery_case_id,
            observed_state="provider_fetch_error",
            observed_at=at,
            fetched_at=at,
            raw_hash=f"local-error:{source}:{type(error).__name__}",
            trust_tier=TrustTier.MERCHANT_STATE,
            attributes={"failed_source": source, "error_type": type(error).__name__},
        )

    def assemble(
        self,
        *,
        event: RecoveryEvent,
        current_mandate_state: str | None = None,
        merchant_entitlement_state: str | None = None,
        entitlement_id: str | None = None,
        fetched_at: datetime | None = None,
        extra_items: Iterable[EvidenceItem] = (),
    ) -> EvidenceBundle:
        now = fetched_at or datetime.now(timezone.utc)
        items: list[EvidenceItem] = [self.webhook_item(event)]

        payment_id = str(event.failure_payload.get("payment_id") or "")
        subscription_id = str(event.failure_payload.get("subscription_id") or "")

        if self.razorpay is not None and payment_id.startswith("pay_"):
            try:
                payment: ProviderSnapshot = self.razorpay.fetch_payment(payment_id, fetched_at=now)
                items.append(payment.evidence)
            except (RazorpayReadError, ValueError) as exc:
                items.append(self._fetch_error_item(event, "payment_api", exc, now))

        if self.razorpay is not None and subscription_id.startswith("sub_"):
            try:
                subscription: ProviderSnapshot = self.razorpay.fetch_subscription(subscription_id, fetched_at=now)
                items.append(subscription.evidence)
            except (RazorpayReadError, ValueError) as exc:
                items.append(self._fetch_error_item(event, "subscription_api", exc, now))

        if current_mandate_state is not None:
            items.append(self.current_mandate_item(event, current_mandate_state, observed_at=now))

        if merchant_entitlement_state is not None:
            items.append(
                self.merchant_entitlement_item(
                    event,
                    merchant_entitlement_state,
                    observed_at=now,
                    entitlement_id=entitlement_id,
                )
            )

        items.extend(extra_items)
        return EvidenceBundle(
            recovery_case_id=event.recovery_case_id,
            correlation_id=event.correlation_id,
            items=tuple(items),
        )
