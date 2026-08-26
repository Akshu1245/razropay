from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .evidence import EvidenceItem
from .razorpay_client import RazorpayReadClient, RazorpayReadError


class PostconditionKind(str, Enum):
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"
    PROVIDER_PENDING = "provider_pending"
    ENTITLEMENT_NOT_CONVERGED = "entitlement_not_converged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PostconditionVerdict:
    kind: PostconditionKind
    payment_id: str
    subscription_id: str | None
    retry_allowed: bool
    money_moved: bool
    reason_codes: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        if self.money_moved and self.retry_allowed:
            raise ValueError("money-moved postconditions can never permit another recovery attempt")
        if self.kind is PostconditionKind.UNKNOWN and self.retry_allowed:
            raise ValueError("unknown postconditions must fail closed")


class PostconditionVerifier:
    """Re-read provider truth after a permitted action.

    An HTTP 2xx response from an action endpoint proves only that the request
    was accepted. RecoveryTruth does not treat it as proof that money moved or
    failed. This verifier performs a new current-state read and returns a
    fail-closed verdict that a subsequent attempt can consume.
    """

    _CONFIRMED_MONEY = frozenset({"captured", "paid", "succeeded", "success"})
    _FAILED = frozenset({"failed", "failure"})
    _PENDING = frozenset({"created", "authorized", "pending", "processing"})
    _SUBSCRIPTION_NOT_CONVERGED = frozenset(
        {"pending", "awaiting_authorization", "halted", "created"}
    )

    def __init__(self, *, razorpay: RazorpayReadClient) -> None:
        self.razorpay = razorpay

    def verify(
        self,
        *,
        payment_id: str,
        subscription_id: str | None = None,
        fetched_at: datetime | None = None,
    ) -> PostconditionVerdict:
        evidence: list[EvidenceItem] = []
        try:
            payment = self.razorpay.fetch_payment(payment_id, fetched_at=fetched_at)
        except (RazorpayReadError, ValueError):
            return PostconditionVerdict(
                kind=PostconditionKind.UNKNOWN,
                payment_id=payment_id,
                subscription_id=subscription_id,
                retry_allowed=False,
                money_moved=False,
                reason_codes=("POSTCONDITION_PAYMENT_FETCH_UNRESOLVED",),
                evidence=(),
            )

        evidence.append(payment.evidence)
        payment_state = payment.evidence.normalized_state

        if payment_state in self._CONFIRMED_MONEY:
            if subscription_id:
                try:
                    subscription = self.razorpay.fetch_subscription(
                        subscription_id,
                        fetched_at=fetched_at,
                    )
                except (RazorpayReadError, ValueError):
                    return PostconditionVerdict(
                        kind=PostconditionKind.UNKNOWN,
                        payment_id=payment_id,
                        subscription_id=subscription_id,
                        retry_allowed=False,
                        money_moved=True,
                        reason_codes=(
                            "PAYMENT_CONFIRMED",
                            "POSTCONDITION_SUBSCRIPTION_FETCH_UNRESOLVED",
                        ),
                        evidence=tuple(evidence),
                    )
                evidence.append(subscription.evidence)
                if subscription.evidence.normalized_state in self._SUBSCRIPTION_NOT_CONVERGED:
                    return PostconditionVerdict(
                        kind=PostconditionKind.ENTITLEMENT_NOT_CONVERGED,
                        payment_id=payment_id,
                        subscription_id=subscription_id,
                        retry_allowed=False,
                        money_moved=True,
                        reason_codes=("PAYMENT_CONFIRMED", "SUBSCRIPTION_NOT_CONVERGED"),
                        evidence=tuple(evidence),
                    )
            return PostconditionVerdict(
                kind=PostconditionKind.PAYMENT_CONFIRMED,
                payment_id=payment_id,
                subscription_id=subscription_id,
                retry_allowed=False,
                money_moved=True,
                reason_codes=("PAYMENT_CONFIRMED",),
                evidence=tuple(evidence),
            )

        if payment_state in self._FAILED:
            return PostconditionVerdict(
                kind=PostconditionKind.PAYMENT_FAILED,
                payment_id=payment_id,
                subscription_id=subscription_id,
                retry_allowed=True,
                money_moved=False,
                reason_codes=("PAYMENT_CONFIRMED_FAILED",),
                evidence=tuple(evidence),
            )

        if payment_state in self._PENDING:
            return PostconditionVerdict(
                kind=PostconditionKind.PROVIDER_PENDING,
                payment_id=payment_id,
                subscription_id=subscription_id,
                retry_allowed=False,
                money_moved=payment_state == "authorized",
                reason_codes=("POSTCONDITION_NOT_FINAL",),
                evidence=tuple(evidence),
            )

        return PostconditionVerdict(
            kind=PostconditionKind.UNKNOWN,
            payment_id=payment_id,
            subscription_id=subscription_id,
            retry_allowed=False,
            money_moved=False,
            reason_codes=("POSTCONDITION_STATE_UNKNOWN",),
            evidence=tuple(evidence),
        )
