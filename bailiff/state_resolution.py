from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import Decision
from .evidence import EvidenceBundle, EvidenceSource


class CanonicalFinancialState(str, Enum):
    RECOVERABLE_FAILURE = "recoverable_failure"
    TERMINAL_FAILURE = "terminal_failure"
    MONEY_ALREADY_MOVED = "money_already_moved"
    ENTITLEMENT_MISMATCH = "entitlement_mismatch"
    MANDATE_NOT_ACTIONABLE = "mandate_not_actionable"
    UNKNOWN_CONFLICT = "unknown_conflict"


class ResolutionAction(str, Enum):
    PROCEED_TO_RECOVERY = "proceed_to_recovery"
    STOP_RECOVERY = "stop_recovery"
    RECONCILE_ENTITLEMENT = "reconcile_entitlement"
    POLL_PROVIDER = "poll_provider"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True, slots=True)
class StateHypothesis:
    """Typed output expected from the bounded AI state resolver.

    The model may propose what the evidence means. It cannot make the recovery
    action executable; that remains the deterministic preflight gate's job.
    """

    state: CanonicalFinancialState
    confidence: float
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True, slots=True)
class PreflightVerdict:
    decision: Decision
    state: CanonicalFinancialState
    resolution_action: ResolutionAction
    recovery_action_allowed: bool
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: float
    contradictions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.recovery_action_allowed and self.decision is not Decision.ALLOW:
            raise ValueError("only ALLOW may hand off a recovery action")
        if self.decision is Decision.ALLOW and not self.recovery_action_allowed:
            raise ValueError("ALLOW must hand off a recovery action")


_MONEY_MOVED = frozenset({"captured", "paid", "succeeded", "success", "authorized"})
_PAYMENT_FAILED = frozenset({"failed", "failure"})
_MANDATE_ACTIVE = frozenset({"active", "enabled", "confirmed", "authenticated"})
_MANDATE_DEAD = frozenset({"revoked", "cancelled", "canceled", "paused", "expired", "halted"})
_ENTITLEMENT_NOT_ACTIVE = frozenset(
    {"inactive", "not_active", "not_activated", "pending", "awaiting_authorization", "unfulfilled"}
)


def _all_ids(bundle: EvidenceBundle) -> tuple[str, ...]:
    return tuple(item.evidence_id for item in bundle.items)


def _abstain(
    bundle: EvidenceBundle,
    *,
    reason: str,
    action: ResolutionAction = ResolutionAction.POLL_PROVIDER,
    hypothesis: StateHypothesis | None = None,
) -> PreflightVerdict:
    return PreflightVerdict(
        decision=Decision.ABSTAIN,
        state=CanonicalFinancialState.UNKNOWN_CONFLICT,
        resolution_action=action,
        recovery_action_allowed=False,
        reason_codes=(reason,),
        evidence_ids=_all_ids(bundle),
        confidence=0.0 if hypothesis is None else hypothesis.confidence,
        contradictions=() if hypothesis is None else hypothesis.contradicting_evidence,
        unknowns=() if hypothesis is None else hypothesis.unknowns,
    )


def evaluate_recovery_preflight(
    bundle: EvidenceBundle,
    hypothesis: StateHypothesis | None,
    *,
    minimum_confidence: float = 0.75,
) -> PreflightVerdict:
    """Turn multi-source evidence into a fail-closed recovery handoff.

    Precedence is intentional:
    1. Current provider evidence that money already moved blocks another money
       action regardless of what the model says.
    2. A non-actionable mandate blocks recovery regardless of model confidence.
    3. Missing current provider truth is an abstention, not permission to trust
       an older failure webhook.
    4. A high-confidence terminal interpretation may stop recovery but never
       create a provider action.
    5. Only a current failed payment + actionable mandate + sufficiently
       confident recoverable hypothesis may reach MandateGuard.
    """

    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum_confidence must be between zero and one")

    if hypothesis is not None:
        bundle.require_ids(hypothesis.supporting_evidence + hypothesis.contradicting_evidence)

    payment = bundle.current(EvidenceSource.PAYMENT_API)
    mandate = bundle.current(EvidenceSource.MANDATE_API)
    subscription = bundle.current(EvidenceSource.SUBSCRIPTION_API)
    entitlement = bundle.current(EvidenceSource.MERCHANT_ENTITLEMENT)

    # Provider truth that money moved is authoritative for the money boundary.
    # A stale failed webhook cannot reopen recovery after this point.
    if payment is not None and payment.normalized_state in _MONEY_MOVED:
        mismatch = (
            (subscription is not None and subscription.normalized_state in _ENTITLEMENT_NOT_ACTIVE)
            or (entitlement is not None and entitlement.normalized_state in _ENTITLEMENT_NOT_ACTIVE)
        )
        if mismatch:
            return PreflightVerdict(
                decision=Decision.DENY,
                state=CanonicalFinancialState.ENTITLEMENT_MISMATCH,
                resolution_action=ResolutionAction.RECONCILE_ENTITLEMENT,
                recovery_action_allowed=False,
                reason_codes=("MONEY_ALREADY_MOVED", "ENTITLEMENT_NOT_CONVERGED"),
                evidence_ids=_all_ids(bundle),
                confidence=1.0,
                contradictions=() if hypothesis is None else hypothesis.contradicting_evidence,
                unknowns=() if hypothesis is None else hypothesis.unknowns,
            )
        return PreflightVerdict(
            decision=Decision.STOP,
            state=CanonicalFinancialState.MONEY_ALREADY_MOVED,
            resolution_action=ResolutionAction.STOP_RECOVERY,
            recovery_action_allowed=False,
            reason_codes=("MONEY_ALREADY_MOVED",),
            evidence_ids=_all_ids(bundle),
            confidence=1.0,
        )

    if mandate is not None and mandate.normalized_state in _MANDATE_DEAD:
        return PreflightVerdict(
            decision=Decision.DENY,
            state=CanonicalFinancialState.MANDATE_NOT_ACTIONABLE,
            resolution_action=ResolutionAction.STOP_RECOVERY,
            recovery_action_allowed=False,
            reason_codes=("MANDATE_NOT_ACTIONABLE",),
            evidence_ids=_all_ids(bundle),
            confidence=1.0,
        )

    # A failed webhook is not enough. RecoveryTruth is specifically the
    # read-before-act layer, so current payment truth must be present.
    if payment is None:
        return _abstain(bundle, reason="CURRENT_PAYMENT_STATE_MISSING")

    if payment.normalized_state not in _PAYMENT_FAILED:
        return _abstain(bundle, reason="CURRENT_PAYMENT_STATE_UNRESOLVED")

    if mandate is None:
        return _abstain(bundle, reason="CURRENT_MANDATE_STATE_MISSING")

    if mandate.normalized_state not in _MANDATE_ACTIVE:
        return _abstain(bundle, reason="CURRENT_MANDATE_STATE_UNRESOLVED")

    if hypothesis is None:
        return _abstain(bundle, reason="AI_HYPOTHESIS_MISSING", action=ResolutionAction.HUMAN_REVIEW)

    if hypothesis.confidence < minimum_confidence:
        return _abstain(
            bundle,
            reason="AI_CONFIDENCE_BELOW_THRESHOLD",
            action=ResolutionAction.HUMAN_REVIEW,
            hypothesis=hypothesis,
        )

    if hypothesis.state is CanonicalFinancialState.TERMINAL_FAILURE:
        return PreflightVerdict(
            decision=Decision.STOP,
            state=CanonicalFinancialState.TERMINAL_FAILURE,
            resolution_action=ResolutionAction.STOP_RECOVERY,
            recovery_action_allowed=False,
            reason_codes=("AI_TERMINAL_FAILURE",),
            evidence_ids=_all_ids(bundle),
            confidence=hypothesis.confidence,
            contradictions=hypothesis.contradicting_evidence,
            unknowns=hypothesis.unknowns,
        )

    if hypothesis.state is not CanonicalFinancialState.RECOVERABLE_FAILURE:
        return _abstain(
            bundle,
            reason="AI_STATE_NOT_RECOVERABLE",
            action=ResolutionAction.HUMAN_REVIEW,
            hypothesis=hypothesis,
        )

    return PreflightVerdict(
        decision=Decision.ALLOW,
        state=CanonicalFinancialState.RECOVERABLE_FAILURE,
        resolution_action=ResolutionAction.PROCEED_TO_RECOVERY,
        recovery_action_allowed=True,
        reason_codes=("CURRENT_PAYMENT_FAILED", "MANDATE_ACTIONABLE", "AI_RECOVERABLE"),
        evidence_ids=_all_ids(bundle),
        confidence=hypothesis.confidence,
        contradictions=hypothesis.contradicting_evidence,
        unknowns=hypothesis.unknowns,
    )
