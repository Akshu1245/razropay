from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from bailiff.evidence import EvidenceBundle, EvidenceItem, EvidenceSource, TrustTier
from bailiff.resolver import DeterministicStateResolver, RealEvidenceStateResolver
from bailiff.state_resolution import CanonicalFinancialState

NOW = datetime(2026, 8, 26, tzinfo=timezone.utc)


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message


@dataclass
class _Response:
    choices: list[_Choice]


class _Completions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _Response:
        self.calls.append(kwargs)
        return _Response([_Choice(_Message(self.content))])


class _Client:
    def __init__(self, content: str) -> None:
        self.completions = _Completions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def evidence(evidence_id: str, source: EvidenceSource, state: str, **attributes: object) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        entity_id=f"entity:{evidence_id}",
        observed_state=state,
        observed_at=NOW,
        fetched_at=NOW,
        raw_hash=f"sha256:{evidence_id}",
        trust_tier=(
            TrustTier.PROVIDER_CURRENT
            if source in {EvidenceSource.PAYMENT_API, EvidenceSource.MANDATE_API, EvidenceSource.SUBSCRIPTION_API}
            else TrustTier.PROVIDER_EVENT
        ),
        attributes=attributes,
    )


def make_bundle(*items: EvidenceItem) -> EvidenceBundle:
    return EvidenceBundle("case_1", "corr_1", tuple(items))


def test_deterministic_resolver_is_a_small_reproducible_baseline():
    bundle = make_bundle(
        evidence("E1", EvidenceSource.PAYMENT_API, "failed", error_reason="bank_timeout"),
        evidence("E2", EvidenceSource.MANDATE_API, "active"),
    )

    hypothesis = DeterministicStateResolver()(bundle)

    assert hypothesis.state is CanonicalFinancialState.RECOVERABLE_FAILURE
    assert hypothesis.confidence == 0.80
    assert hypothesis.supporting_evidence == ("E1", "E2")


def test_real_resolver_is_schema_bounded_and_has_no_tools():
    bundle = make_bundle(
        evidence("E1", EvidenceSource.WEBHOOK, "failed", error_description="issuer response 91"),
        evidence("E2", EvidenceSource.PAYMENT_API, "failed", error_reason="unknown"),
        evidence("E3", EvidenceSource.MANDATE_API, "active"),
    )
    client = _Client(
        '{"state":"recoverable_failure","confidence":0.86,'
        '"supporting_evidence":["E1","E2","E3"],'
        '"contradicting_evidence":[],"unknowns":[]}'
    )

    hypothesis = RealEvidenceStateResolver(client=client, model="test-model")(bundle)

    assert hypothesis.state is CanonicalFinancialState.RECOVERABLE_FAILURE
    assert hypothesis.confidence == 0.86
    request = client.completions.calls[0]
    assert "tools" not in request
    assert request["response_format"]["type"] == "json_schema"
    assert "authorize a retry" in request["messages"][0]["content"]


def test_real_resolver_cannot_return_an_evidence_reference_that_does_not_exist():
    bundle = make_bundle(
        evidence("E1", EvidenceSource.PAYMENT_API, "failed"),
        evidence("E2", EvidenceSource.MANDATE_API, "active"),
    )
    client = _Client(
        '{"state":"recoverable_failure","confidence":0.99,'
        '"supporting_evidence":["E404"],'
        '"contradicting_evidence":[],"unknowns":[]}'
    )

    with pytest.raises(ValueError, match="unknown evidence IDs"):
        RealEvidenceStateResolver(client=client, model="test-model")(bundle)


def test_model_view_contains_selected_semantics_but_not_raw_payload_body():
    bundle = make_bundle(
        evidence(
            "E1",
            EvidenceSource.WEBHOOK,
            "failed",
            error_code="91",
            error_description="unable to process",
        )
    )

    view = bundle.model_view()

    assert view["evidence"][0]["attributes"]["error_code"] == "91"
    assert view["evidence"][0]["raw_hash"] if "raw_hash" in view["evidence"][0] else True
    assert "raw_payload" not in view["evidence"][0]
