from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EvidenceSource(str, Enum):
    """Sources RecoveryTruth may use to establish the current financial state."""

    WEBHOOK = "webhook"
    PAYMENT_API = "payment_api"
    SUBSCRIPTION_API = "subscription_api"
    MANDATE_API = "mandate_api"
    MERCHANT_ENTITLEMENT = "merchant_entitlement"
    RECOVERY_HISTORY = "recovery_history"
    CUSTOMER_REPORT = "customer_report"


class TrustTier(int, Enum):
    """Relative evidence authority; freshness still matters inside a source."""

    CUSTOMER_REPORT = 20
    MERCHANT_STATE = 70
    PROVIDER_EVENT = 80
    PROVIDER_CURRENT = 100


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    source: EvidenceSource
    entity_id: str
    observed_state: str
    observed_at: datetime
    fetched_at: datetime
    raw_hash: str
    trust_tier: TrustTier

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if not self.entity_id:
            raise ValueError("entity_id is required")
        if not self.observed_state:
            raise ValueError("observed_state is required")
        if not self.raw_hash:
            raise ValueError("raw_hash is required")
        if self.observed_at.tzinfo is None or self.fetched_at.tzinfo is None:
            raise ValueError("evidence timestamps must be timezone aware")

    @property
    def normalized_state(self) -> str:
        return self.observed_state.strip().lower().replace(" ", "_")


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    recovery_case_id: str
    correlation_id: str
    items: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        if not self.recovery_case_id or not self.correlation_id:
            raise ValueError("recovery_case_id and correlation_id are required")
        if not self.items:
            raise ValueError("at least one evidence item is required")
        ids = [item.evidence_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence IDs must be unique")

    @property
    def by_id(self) -> dict[str, EvidenceItem]:
        return {item.evidence_id: item for item in self.items}

    def current(self, source: EvidenceSource) -> EvidenceItem | None:
        candidates = [item for item in self.items if item.source is source]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.observed_at, item.fetched_at, item.evidence_id))

    def require_ids(self, evidence_ids: tuple[str, ...]) -> None:
        available = self.by_id
        unknown = sorted(set(evidence_ids) - set(available))
        if unknown:
            raise ValueError(f"hypothesis references unknown evidence IDs: {', '.join(unknown)}")
