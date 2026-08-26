from __future__ import annotations

import json
import os
from typing import Any, Protocol

from .evidence import EvidenceBundle, EvidenceSource
from .state_resolution import CanonicalFinancialState, StateHypothesis


class StateResolver(Protocol):
    def __call__(self, bundle: EvidenceBundle) -> StateHypothesis:
        ...


class DeterministicStateResolver:
    """Offline resolver used for judge reproducibility and baseline comparison.

    This intentionally does very little. It proves the orchestration path and
    gives the AI resolver a fair deterministic baseline; it is not allowed to
    quietly absorb fuzzy language understanding into more handwritten rules.
    """

    def __call__(self, bundle: EvidenceBundle) -> StateHypothesis:
        payment = bundle.current(EvidenceSource.PAYMENT_API)
        mandate = bundle.current(EvidenceSource.MANDATE_API)
        support: list[str] = []
        unknowns: list[str] = []

        if payment is None:
            unknowns.append("current_payment_state")
            return StateHypothesis(
                state=CanonicalFinancialState.UNKNOWN_CONFLICT,
                confidence=0.0,
                supporting_evidence=(),
                unknowns=tuple(unknowns),
            )
        support.append(payment.evidence_id)

        if mandate is None:
            unknowns.append("current_mandate_state")
        else:
            support.append(mandate.evidence_id)

        state = payment.normalized_state
        if state in {"captured", "paid", "succeeded", "success", "authorized"}:
            return StateHypothesis(
                state=CanonicalFinancialState.MONEY_ALREADY_MOVED,
                confidence=1.0,
                supporting_evidence=tuple(support),
                unknowns=tuple(unknowns),
            )
        if state in {"failed", "failure"} and mandate is not None and mandate.normalized_state in {
            "active",
            "enabled",
            "confirmed",
            "authenticated",
        }:
            return StateHypothesis(
                state=CanonicalFinancialState.RECOVERABLE_FAILURE,
                confidence=0.80,
                supporting_evidence=tuple(support),
                unknowns=tuple(unknowns),
            )
        return StateHypothesis(
            state=CanonicalFinancialState.UNKNOWN_CONFLICT,
            confidence=0.30,
            supporting_evidence=tuple(support),
            unknowns=tuple(unknowns),
        )


class RealEvidenceStateResolver:
    """Bounded OpenAI-compatible resolver over typed evidence.

    It has no provider tools and no authority. It returns a hypothesis only;
    ``evaluate_recovery_preflight`` decides whether any recovery action may be
    handed to MandateGuard.
    """

    _REASONING_FAMILY_PREFIXES = ("gpt-5", "o1", "o3", "o4")

    def __init__(
        self,
        *,
        model: str | None = None,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or os.getenv("RECOVERYTRUTH_RESOLVER_MODEL", "gpt-5-mini")
        self.base_url = base_url or os.getenv("RECOVERYTRUTH_RESOLVER_BASE_URL") or None
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("install the interpreter extra to use the real state resolver") from exc
            self._client = OpenAI(base_url=self.base_url) if self.base_url else OpenAI()
        return self._client

    @property
    def _is_reasoning_family(self) -> bool:
        return self.model.startswith(self._REASONING_FAMILY_PREFIXES)

    def __call__(self, bundle: EvidenceBundle) -> StateHypothesis:
        allowed_states = [state.value for state in CanonicalFinancialState]
        evidence_ids = [item.evidence_id for item in bundle.items]
        schema = {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": allowed_states},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string", "enum": evidence_ids},
                    "uniqueItems": True,
                },
                "contradicting_evidence": {
                    "type": "array",
                    "items": {"type": "string", "enum": evidence_ids},
                    "uniqueItems": True,
                },
                "unknowns": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
            },
            "required": [
                "state",
                "confidence",
                "supporting_evidence",
                "contradicting_evidence",
                "unknowns",
            ],
            "additionalProperties": False,
        }
        system = (
            "You are RecoveryTruth's bounded financial-state resolver. Interpret only the supplied evidence. "
            "Your job is to estimate the current canonical state, not to choose or execute a payment action. "
            "Never invent an evidence ID. Treat newer current-provider observations as stronger evidence of current "
            "provider state than older event-time webhooks, but list genuine contradictions instead of hiding them. "
            "Use UNKNOWN_CONFLICT and lower confidence when the current state cannot be established. "
            "You may not authorize a retry, change consent or mandate state, choose an amount, or call any tool."
        )
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(bundle.model_view(), sort_keys=True)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "recoverytruth_state_hypothesis", "strict": True, "schema": schema},
            },
            "max_completion_tokens": 350,
        }
        if self._is_reasoning_family:
            request["extra_body"] = {"reasoning": {"effort": "minimal"}}

        response = self.client.chat.completions.create(**request)
        content = response.choices[0].message.content
        if not content:
            raise ValueError("state resolver returned empty content")
        parsed = json.loads(content)
        hypothesis = StateHypothesis(
            state=CanonicalFinancialState(parsed["state"]),
            confidence=float(parsed["confidence"]),
            supporting_evidence=tuple(parsed["supporting_evidence"]),
            contradicting_evidence=tuple(parsed["contradicting_evidence"]),
            unknowns=tuple(parsed["unknowns"]),
        )
        bundle.require_ids(hypothesis.supporting_evidence + hypothesis.contradicting_evidence)
        return hypothesis
