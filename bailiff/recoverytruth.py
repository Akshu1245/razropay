from __future__ import annotations

from dataclasses import dataclass

from .domain import RecoveryEvent
from .evidence import EvidenceBundle
from .policies import PolicyRun, run_policy_case
from .replay import CommonOutcomeLedger
from .resolver import DeterministicStateResolver, StateResolver
from .state_resolution import (
    CanonicalFinancialState,
    PreflightVerdict,
    StateHypothesis,
    evaluate_recovery_preflight,
)


@dataclass(frozen=True, slots=True)
class RecoveryTruthRun:
    evidence: EvidenceBundle
    hypothesis: StateHypothesis
    preflight: PreflightVerdict
    policy_run: PolicyRun | None
    resolver_failed: bool = False

    @property
    def provider_result(self):
        if self.policy_run is None:
            return None
        return self.policy_run.provider_result


class RecoveryTruthController:
    """Recovery preflight plus the existing MandateGuard B2 authority kernel."""

    def __init__(
        self,
        *,
        resolver: StateResolver | None = None,
        minimum_confidence: float = 0.75,
    ) -> None:
        self.resolver = resolver or DeterministicStateResolver()
        self.minimum_confidence = minimum_confidence

    def run(
        self,
        *,
        event: RecoveryEvent,
        evidence: EvidenceBundle,
        ledger: CommonOutcomeLedger,
    ) -> RecoveryTruthRun:
        if evidence.recovery_case_id != event.recovery_case_id:
            raise ValueError("evidence bundle belongs to a different recovery case")
        if evidence.correlation_id != event.correlation_id:
            raise ValueError("evidence bundle correlation_id does not match the event")

        resolver_failed = False
        try:
            hypothesis = self.resolver(evidence)
        except Exception as exc:
            resolver_failed = True
            hypothesis = StateHypothesis(
                state=CanonicalFinancialState.UNKNOWN_CONFLICT,
                confidence=0.0,
                supporting_evidence=(),
                unknowns=(f"resolver_error:{type(exc).__name__}",),
            )

        preflight = evaluate_recovery_preflight(
            evidence,
            hypothesis,
            minimum_confidence=self.minimum_confidence,
        )

        # The crucial structural property: no MandateGuard runner, provider,
        # idempotency record, or money-side effect is even constructed until
        # the preflight returns ALLOW.
        if not preflight.recovery_action_allowed:
            return RecoveryTruthRun(
                evidence=evidence,
                hypothesis=hypothesis,
                preflight=preflight,
                policy_run=None,
                resolver_failed=resolver_failed,
            )

        # RecoveryTruth already used AI to resolve state, so hand off to B2,
        # the deterministic full guardrail profile. This avoids giving a model
        # a second interpretation opportunity at the money boundary.
        policy_run = run_policy_case(arm="B2", event=event, ledger=ledger)
        return RecoveryTruthRun(
            evidence=evidence,
            hypothesis=hypothesis,
            preflight=preflight,
            policy_run=policy_run,
            resolver_failed=resolver_failed,
        )
