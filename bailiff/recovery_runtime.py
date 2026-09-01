from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from .recovery_truth import RecoveryProof, TruthResolution, TruthState, WriteFence, resolve_financial_truth


class RecoveryProvider(Protocol):
    def order_evidence(self, *, order_id: str, mandate_id: str | None = None, mandate_status: str | None = None): ...

    def create_payment_link_once(
        self, *, amount_minor: int, currency: str, reference_id: str, description: str
    ): ...

    def verify_payment_link_capture(
        self, *, payment_link_id: str, expected_amount_minor: int, expected_currency: str, expected_reference_id: str
    ): ...


@dataclass(frozen=True)
class RecoveryRequest:
    case_id: str
    decision_id: str
    policy_version: str
    order_id: str
    mandate_id: str
    mandate_status: str
    amount_minor: int
    currency: str = "INR"
    description: str = "RecoveryTruth customer-initiated fallback"

    def __post_init__(self) -> None:
        if not self.case_id or not self.decision_id or not self.policy_version:
            raise ValueError("case_id, decision_id and policy_version are required")
        if not self.order_id.startswith("order_"):
            raise ValueError("RecoveryTruth requires a Razorpay order id")
        if not self.mandate_id:
            raise ValueError("mandate_id is required")
        if self.amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        if self.currency != "INR":
            raise ValueError("RecoveryTruth fallback currently supports INR only")


@dataclass(frozen=True)
class RecoveryActionReceipt:
    case_id: str
    decision_id: str
    policy_version: str
    action_type: str
    reference_id: str
    payment_link_id: str
    short_url: str
    amount_minor: int
    currency: str
    prewrite_resolution: str
    prewrite_evidence_hash: str


@dataclass(frozen=True)
class RecoveryAttempt:
    executed: bool
    reason_code: str
    truth: TruthResolution
    receipt: RecoveryActionReceipt | None = None


def recovery_reference(case_id: str) -> str:
    """Stable <=40-char provider idempotency/reconciliation reference."""
    return "rt_" + sha256(case_id.encode()).hexdigest()[:32]


def _resolution_hash(resolution: TruthResolution) -> str:
    return sha256("|".join(sorted(resolution.evidence_fingerprints)).encode()).hexdigest()


class RecoveryTruthRuntime:
    """Financial-truth enforcement boundary for the provider-backed demo.

    The runtime deliberately does not replace MandateGuard's policy engine.
    It runs after a deterministic decision has authorised a fallback action.
    Before the provider write it resolves current financial truth twice: once
    to arm the fence and again immediately at the write boundary. A state
    change, captured payment, terminal mandate, unknown state or conflict is a
    zero-write SAFE_BLOCK.
    """

    def __init__(self, provider: RecoveryProvider) -> None:
        self.provider = provider

    def execute_customer_fallback(self, request: RecoveryRequest) -> RecoveryAttempt:
        initial_evidence = tuple(
            self.provider.order_evidence(
                order_id=request.order_id,
                mandate_id=request.mandate_id,
                mandate_status=request.mandate_status,
            )
        )
        initial_truth = resolve_financial_truth(initial_evidence)
        if initial_truth.state == TruthState.PAID:
            return RecoveryAttempt(False, "SAFE_BLOCK_ALREADY_PAID", initial_truth)
        if not initial_truth.executable:
            return RecoveryAttempt(False, f"SAFE_BLOCK_{initial_truth.state.value}", initial_truth)

        fence = WriteFence.from_evidence(initial_evidence)

        # This second provider read is intentionally adjacent to the financial
        # write. It closes the time-of-check/time-of-use gap between diagnosis
        # and execution.
        fresh_evidence = tuple(
            self.provider.order_evidence(
                order_id=request.order_id,
                mandate_id=request.mandate_id,
                mandate_status=request.mandate_status,
            )
        )
        allowed, reason = fence.check(fresh_evidence)
        fresh_truth = resolve_financial_truth(fresh_evidence)
        if not allowed:
            return RecoveryAttempt(False, reason, fresh_truth)

        reference_id = recovery_reference(request.case_id)
        link = self.provider.create_payment_link_once(
            amount_minor=request.amount_minor,
            currency=request.currency,
            reference_id=reference_id,
            description=request.description,
        )
        link_id = str(link.get("id") or "")
        short_url = str(link.get("short_url") or "")
        if not link_id.startswith("plink_"):
            raise RuntimeError("provider returned an invalid payment link id")
        if str(link.get("reference_id") or "") != reference_id:
            raise RuntimeError("provider returned a payment link with the wrong recovery reference")
        if int(link.get("amount") or 0) != request.amount_minor:
            raise RuntimeError("provider returned a payment link with the wrong amount")
        if str(link.get("currency") or "") != request.currency:
            raise RuntimeError("provider returned a payment link with the wrong currency")

        receipt = RecoveryActionReceipt(
            case_id=request.case_id,
            decision_id=request.decision_id,
            policy_version=request.policy_version,
            action_type="CREATE_PAYMENT_LINK_FALLBACK",
            reference_id=reference_id,
            payment_link_id=link_id,
            short_url=short_url,
            amount_minor=request.amount_minor,
            currency=request.currency,
            prewrite_resolution=fresh_truth.state.value,
            prewrite_evidence_hash=_resolution_hash(fresh_truth),
        )
        return RecoveryAttempt(True, "FALLBACK_PAYMENT_LINK_CREATED", fresh_truth, receipt)

    def verify_recovery(self, receipt: RecoveryActionReceipt) -> RecoveryProof:
        captured, postcondition_hash = self.provider.verify_payment_link_capture(
            payment_link_id=receipt.payment_link_id,
            expected_amount_minor=receipt.amount_minor,
            expected_currency=receipt.currency,
            expected_reference_id=receipt.reference_id,
        )
        return RecoveryProof(
            case_id=receipt.case_id,
            decision_id=receipt.decision_id,
            policy_version=receipt.policy_version,
            prewrite_resolution=receipt.prewrite_resolution,
            prewrite_evidence_hash=receipt.prewrite_evidence_hash,
            provider_action_type=receipt.action_type,
            provider_action_id=receipt.payment_link_id,
            postcondition_evidence_hash=postcondition_hash,
            payment_id=captured.payment_id,
            amount_minor=captured.amount_minor,
            currency=captured.currency,
            reference_id=captured.reference_id,
        )
