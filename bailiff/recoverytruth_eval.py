from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping

from .domain import Decision
from .evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from .resolver import DeterministicStateResolver, StateResolver
from .state_resolution import CanonicalFinancialState, StateHypothesis, evaluate_recovery_preflight


DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "recoverytruth_unseen_v1.json"
BASE_TIME = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ChallengeCase:
    case_id: str
    family: str
    gold_state: CanonicalFinancialState
    evidence: EvidenceBundle


@dataclass(frozen=True, slots=True)
class EvalRow:
    case_id: str
    family: str
    gold_state: str
    hypothesis_state: str
    hypothesis_confidence: float
    verdict_state: str
    decision: str
    recovery_action_allowed: bool
    correct: bool


@dataclass(frozen=True, slots=True)
class EvalSummary:
    resolver: str
    n: int
    state_accuracy: float
    selective_accuracy: float
    automation_coverage: float
    unsafe_recovery_rate: float
    dangerous_second_action_rate: float
    terminal_wrong_allow_rate: float
    unknown_wrong_allow_rate: float
    missed_recovery_rate: float
    rows: tuple[EvalRow, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "resolver": self.resolver,
            "n": self.n,
            "state_accuracy": self.state_accuracy,
            "selective_accuracy": self.selective_accuracy,
            "automation_coverage": self.automation_coverage,
            "unsafe_recovery_rate": self.unsafe_recovery_rate,
            "dangerous_second_action_rate": self.dangerous_second_action_rate,
            "terminal_wrong_allow_rate": self.terminal_wrong_allow_rate,
            "unknown_wrong_allow_rate": self.unknown_wrong_allow_rate,
            "missed_recovery_rate": self.missed_recovery_rate,
            "rows": [
                {
                    "case_id": row.case_id,
                    "family": row.family,
                    "gold_state": row.gold_state,
                    "hypothesis_state": row.hypothesis_state,
                    "hypothesis_confidence": row.hypothesis_confidence,
                    "verdict_state": row.verdict_state,
                    "decision": row.decision,
                    "recovery_action_allowed": row.recovery_action_allowed,
                    "correct": row.correct,
                }
                for row in self.rows
            ],
        }


class ExactLookupResolver:
    """Small exact-string baseline; intentionally no fuzzy semantics."""

    _RECOVERABLE = frozenset({"insufficient_funds", "bank_technical_error", "payment_timed_out"})
    _TERMINAL = frozenset({"account_closed", "payment_risk_check_failed", "mandate_revoked", "mandate_cancelled"})

    def __call__(self, bundle: EvidenceBundle) -> StateHypothesis:
        payment = bundle.current(EvidenceSource.PAYMENT_API)
        if payment is None:
            return StateHypothesis(CanonicalFinancialState.UNKNOWN_CONFLICT, 0.0, (), unknowns=("current_payment_state",))
        reason = str(payment.attributes.get("error_reason") or "").strip().lower()
        if reason in self._RECOVERABLE:
            return StateHypothesis(CanonicalFinancialState.RECOVERABLE_FAILURE, 0.95, (payment.evidence_id,))
        if reason in self._TERMINAL:
            return StateHypothesis(CanonicalFinancialState.TERMINAL_FAILURE, 0.95, (payment.evidence_id,))
        return StateHypothesis(
            CanonicalFinancialState.UNKNOWN_CONFLICT,
            0.20,
            (payment.evidence_id,),
            unknowns=("exact_reason_not_mapped",),
        )


class KeywordTaxonomyResolver:
    """Stronger deterministic lexical baseline frozen before model evaluation."""

    _RECOVERABLE = (
        "insufficient",
        "balance below",
        "available balance",
        "timeout",
        "timed out",
        "temporary",
        "maintenance",
        "technical",
        "host not available",
        "host did not respond",
        "unavailable",
    )
    _TERMINAL = (
        "account is closed",
        "account closed",
        "suspected fraud",
        "fraud screening",
        "risk check",
        "risk service",
        "mandate revoked",
        "mandate cancelled",
        "mandate canceled",
    )

    def __call__(self, bundle: EvidenceBundle) -> StateHypothesis:
        payment = bundle.current(EvidenceSource.PAYMENT_API)
        if payment is None:
            return StateHypothesis(CanonicalFinancialState.UNKNOWN_CONFLICT, 0.0, (), unknowns=("current_payment_state",))

        semantic_items = [payment]
        webhook = bundle.current(EvidenceSource.WEBHOOK)
        if webhook is not None:
            semantic_items.append(webhook)
        text = " ".join(
            " ".join(str(value).lower() for value in item.attributes.values())
            for item in semantic_items
        )
        recoverable = any(token in text for token in self._RECOVERABLE)
        terminal = any(token in text for token in self._TERMINAL)
        support = tuple(item.evidence_id for item in semantic_items)
        if recoverable and terminal:
            return StateHypothesis(
                CanonicalFinancialState.UNKNOWN_CONFLICT,
                0.45,
                support,
                unknowns=("conflicting_failure_semantics",),
            )
        if terminal:
            return StateHypothesis(CanonicalFinancialState.TERMINAL_FAILURE, 0.88, support)
        if recoverable:
            return StateHypothesis(CanonicalFinancialState.RECOVERABLE_FAILURE, 0.88, support)
        return StateHypothesis(
            CanonicalFinancialState.UNKNOWN_CONFLICT,
            0.35,
            support,
            unknowns=("unmapped_failure_semantics",),
        )


def _item(
    case_id: str,
    suffix: str,
    source: EvidenceSource,
    state: str,
    observed_at: datetime,
    *,
    attributes: Mapping[str, object] | None = None,
    trust: TrustTier = TrustTier.PROVIDER_CURRENT,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"{case_id}:{suffix}",
        source=source,
        entity_id=f"{source.value}:{case_id}",
        observed_state=state,
        observed_at=observed_at,
        fetched_at=observed_at + timedelta(seconds=1),
        raw_hash=f"sha256:{hashlib.sha256(f'{case_id}:{suffix}:{state}'.encode()).hexdigest()}",
        trust_tier=trust,
        attributes=attributes or {},
    )


def load_challenge(path: Path = DATASET_PATH) -> tuple[str, tuple[ChallengeCase, ...]]:
    raw_bytes = path.read_bytes()
    payload = json.loads(raw_bytes)
    cases: list[ChallengeCase] = []
    for index, row in enumerate(payload["cases"]):
        case_id = str(row["id"])
        event_time = BASE_TIME + timedelta(minutes=index * 10)
        now = event_time + timedelta(minutes=4)
        semantic = {
            "error_code": row.get("error_code"),
            "error_reason": row.get("error_reason"),
            "error_description": row.get("error_description"),
        }
        items: list[EvidenceItem] = []
        webhook_state = row.get("webhook_state")
        if webhook_state is not None:
            items.append(
                _item(
                    case_id,
                    "webhook",
                    EvidenceSource.WEBHOOK,
                    str(webhook_state),
                    event_time,
                    attributes=semantic,
                    trust=TrustTier.PROVIDER_EVENT,
                )
            )
        elif row.get("payment_state") is not None:
            # A failed-event observation is included for all payment-failure
            # cases so the evaluator mirrors the recovery-trigger context.
            items.append(
                _item(
                    case_id,
                    "webhook",
                    EvidenceSource.WEBHOOK,
                    "failed",
                    event_time,
                    attributes=semantic,
                    trust=TrustTier.PROVIDER_EVENT,
                )
            )

        payment_state = row.get("payment_state")
        if payment_state is not None:
            payment_attrs = semantic if str(payment_state).lower() in {"failed", "failure"} else {}
            items.append(
                _item(
                    case_id,
                    "payment",
                    EvidenceSource.PAYMENT_API,
                    str(payment_state),
                    now,
                    attributes=payment_attrs,
                )
            )

        mandate_state = row.get("mandate_state")
        if mandate_state is not None:
            items.append(_item(case_id, "mandate", EvidenceSource.MANDATE_API, str(mandate_state), now))

        subscription_state = row.get("subscription_state")
        if subscription_state is not None:
            items.append(_item(case_id, "subscription", EvidenceSource.SUBSCRIPTION_API, str(subscription_state), now))

        entitlement_state = row.get("merchant_entitlement_state")
        if entitlement_state is not None:
            items.append(
                _item(
                    case_id,
                    "entitlement",
                    EvidenceSource.MERCHANT_ENTITLEMENT,
                    str(entitlement_state),
                    now,
                    trust=TrustTier.MERCHANT_STATE,
                )
            )

        cases.append(
            ChallengeCase(
                case_id=case_id,
                family=str(row["family"]),
                gold_state=CanonicalFinancialState(str(row["gold_state"])),
                evidence=EvidenceBundle(case_id, f"corr:{case_id}", tuple(items)),
            )
        )
    dataset_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    return dataset_hash, tuple(cases)


def evaluate_resolver(
    name: str,
    resolver: StateResolver,
    cases: Iterable[ChallengeCase],
    *,
    minimum_confidence: float = 0.75,
) -> EvalSummary:
    rows: list[EvalRow] = []
    for case in cases:
        try:
            hypothesis = resolver(case.evidence)
        except Exception as exc:
            hypothesis = StateHypothesis(
                CanonicalFinancialState.UNKNOWN_CONFLICT,
                0.0,
                (),
                unknowns=(f"resolver_error:{type(exc).__name__}",),
            )
        verdict = evaluate_recovery_preflight(
            case.evidence,
            hypothesis,
            minimum_confidence=minimum_confidence,
        )
        correct = verdict.state is case.gold_state
        rows.append(
            EvalRow(
                case_id=case.case_id,
                family=case.family,
                gold_state=case.gold_state.value,
                hypothesis_state=hypothesis.state.value,
                hypothesis_confidence=hypothesis.confidence,
                verdict_state=verdict.state.value,
                decision=verdict.decision.value,
                recovery_action_allowed=verdict.recovery_action_allowed,
                correct=correct,
            )
        )

    total = len(rows)
    automated = [row for row in rows if row.decision != Decision.ABSTAIN.value]
    nonrecoverable = [row for row in rows if row.gold_state != CanonicalFinancialState.RECOVERABLE_FAILURE.value]
    money_moved = [
        row
        for row in rows
        if row.gold_state
        in {
            CanonicalFinancialState.MONEY_ALREADY_MOVED.value,
            CanonicalFinancialState.ENTITLEMENT_MISMATCH.value,
        }
    ]
    terminal = [row for row in rows if row.gold_state == CanonicalFinancialState.TERMINAL_FAILURE.value]
    unknown = [row for row in rows if row.gold_state == CanonicalFinancialState.UNKNOWN_CONFLICT.value]
    recoverable = [row for row in rows if row.gold_state == CanonicalFinancialState.RECOVERABLE_FAILURE.value]

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    return EvalSummary(
        resolver=name,
        n=total,
        state_accuracy=rate(sum(row.correct for row in rows), total),
        selective_accuracy=rate(sum(row.correct for row in automated), len(automated)),
        automation_coverage=rate(len(automated), total),
        unsafe_recovery_rate=rate(sum(row.recovery_action_allowed for row in nonrecoverable), len(nonrecoverable)),
        dangerous_second_action_rate=rate(sum(row.recovery_action_allowed for row in money_moved), len(money_moved)),
        terminal_wrong_allow_rate=rate(sum(row.recovery_action_allowed for row in terminal), len(terminal)),
        unknown_wrong_allow_rate=rate(sum(row.recovery_action_allowed for row in unknown), len(unknown)),
        missed_recovery_rate=rate(sum(not row.recovery_action_allowed for row in recoverable), len(recoverable)),
        rows=tuple(rows),
    )


def run_baselines() -> tuple[str, tuple[EvalSummary, ...]]:
    dataset_hash, cases = load_challenge()
    summaries = (
        evaluate_resolver("exact_lookup", ExactLookupResolver(), cases),
        evaluate_resolver("status_only", DeterministicStateResolver(), cases),
        evaluate_resolver("keyword_taxonomy", KeywordTaxonomyResolver(), cases),
    )
    return dataset_hash, summaries
