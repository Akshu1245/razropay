from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Mapping


class TruthState(str, Enum):
    PAID = "PAID"
    FAILED = "FAILED"
    RECOVERABLE = "RECOVERABLE"
    TERMINAL = "TERMINAL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class ProviderEvidence:
    source: str
    entity_type: str
    entity_id: str
    status: str | None
    amount_minor: int | None = None
    currency: str | None = None
    reference_id: str | None = None
    observed_at: datetime = datetime.min.replace(tzinfo=timezone.utc)
    raw_hash: str = ""

    def fingerprint(self) -> str:
        body = {
            "source": self.source,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "status": self.status,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "reference_id": self.reference_id,
            "raw_hash": self.raw_hash,
        }
        return sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class TruthResolution:
    state: TruthState
    reason_codes: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]
    resolved_at: datetime

    @property
    def executable(self) -> bool:
        return self.state == TruthState.RECOVERABLE


_CAPTURED = {"captured", "paid"}
_FAILED = {"failed"}
_TERMINAL = {"refunded", "cancelled", "expired"}
_RECOVERABLE = {"created", "authorized", "pending"}


def resolve_financial_truth(evidence: Iterable[ProviderEvidence]) -> TruthResolution:
    rows = tuple(evidence)
    now = datetime.now(timezone.utc)
    if not rows:
        return TruthResolution(TruthState.UNKNOWN, ("NO_PROVIDER_EVIDENCE",), (), now)

    statuses = {str(row.status).lower() for row in rows if row.status is not None}
    fingerprints = tuple(row.fingerprint() for row in rows)

    if statuses & _CAPTURED and (statuses & (_FAILED | _RECOVERABLE | _TERMINAL)):
        return TruthResolution(TruthState.CONFLICT, ("CAPTURED_CONFLICTS_WITH_OTHER_STATE",), fingerprints, now)
    if statuses & _CAPTURED:
        return TruthResolution(TruthState.PAID, ("CAPTURED_PAYMENT_OBSERVED",), fingerprints, now)
    if statuses & _TERMINAL:
        return TruthResolution(TruthState.TERMINAL, ("TERMINAL_PROVIDER_STATE",), fingerprints, now)
    if statuses and statuses.issubset(_FAILED):
        return TruthResolution(TruthState.FAILED, ("FAILED_PROVIDER_STATE",), fingerprints, now)
    if statuses and statuses.issubset(_FAILED | _RECOVERABLE) and statuses & _RECOVERABLE:
        return TruthResolution(TruthState.RECOVERABLE, ("NO_CAPTURED_PAYMENT_AND_RECOVERABLE_STATE",), fingerprints, now)
    return TruthResolution(TruthState.UNKNOWN, ("UNRECOGNIZED_OR_INCOMPLETE_PROVIDER_STATE",), fingerprints, now)


@dataclass(frozen=True)
class WriteFence:
    diagnosis_fingerprint: str

    @classmethod
    def from_evidence(cls, evidence: Iterable[ProviderEvidence]) -> "WriteFence":
        return cls(_set_fingerprint(evidence))

    def check(self, fresh_evidence: Iterable[ProviderEvidence]) -> tuple[bool, str]:
        fresh = tuple(fresh_evidence)
        resolution = resolve_financial_truth(fresh)
        if resolution.state == TruthState.PAID:
            return False, "SAFE_BLOCK_ALREADY_PAID"
        if resolution.state != TruthState.RECOVERABLE:
            return False, f"SAFE_BLOCK_{resolution.state.value}"
        if _set_fingerprint(fresh) != self.diagnosis_fingerprint:
            return False, "SAFE_BLOCK_STATE_CHANGED_BEFORE_WRITE"
        return True, "WRITE_FENCE_PASSED"


def _set_fingerprint(evidence: Iterable[ProviderEvidence]) -> str:
    values = sorted(row.fingerprint() for row in evidence)
    return sha256("|".join(values).encode()).hexdigest()


@dataclass(frozen=True)
class CapturedPaymentProof:
    payment_id: str
    amount_minor: int
    currency: str
    reference_id: str
    captured: bool


def verify_captured_payment(
    payment: Mapping[str, object], *, expected_amount_minor: int, expected_currency: str, expected_reference_id: str
) -> CapturedPaymentProof:
    payment_id = str(payment.get("id") or "")
    status = str(payment.get("status") or "").lower()
    amount = int(payment.get("amount") or 0)
    currency = str(payment.get("currency") or "")
    notes = payment.get("notes")
    note_reference = notes.get("recovery_reference", "") if isinstance(notes, Mapping) else ""
    reference = str(payment.get("reference_id") or note_reference)
    if not payment_id:
        raise ValueError("payment id missing")
    if status != "captured":
        raise ValueError("payment is not captured")
    if amount != expected_amount_minor:
        raise ValueError("captured payment amount mismatch")
    if currency != expected_currency:
        raise ValueError("captured payment currency mismatch")
    if reference != expected_reference_id:
        raise ValueError("captured payment reference mismatch")
    return CapturedPaymentProof(payment_id, amount, currency, reference, True)


@dataclass(frozen=True)
class RecoveryProof:
    case_id: str
    decision_id: str
    policy_version: str
    prewrite_resolution: str
    prewrite_evidence_hash: str
    provider_action_id: str
    payment_id: str
    amount_minor: int
    currency: str
    reference_id: str
    previous_proof_hash: str = "GENESIS"

    def hash(self) -> str:
        body = asdict(self)
        return sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
