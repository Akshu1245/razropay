"""Judge-facing paths must use the actual engine and report actual calls."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api.index import app
from bailiff.demo import make_event, execute
from bailiff.domain import ActionType, Decision
from bailiff.guardrails import EvaluationContext
from bailiff.middleware import MandateGuardMiddleware
from bailiff.provider_proof import load_provider_proofs, ProviderProofBundle
from bailiff.razorpay_adapter import to_razorpay_test_payload
from bailiff.showcase import SCENARIOS, run_scenario, run_batch
from bailiff.webhook import build_signed_delivery


def test_scenarios_report_actual_calls_and_timeout_uncertainty():
    for name in SCENARIOS:
        result = run_scenario(name)
        assert result["provider_call_count"] == int(name in {"recover", "timeout"})
        if result["receipt"]:
            assert result["receipt"]["provider_call_count"] == result["provider_call_count"]
            assert result["receipt"]["audit_verified"]
            assert result["tamper_detected"]
    assert run_scenario("recover")["status"] == "Recovered"
    assert run_scenario("ambiguous")["status"] == "Human review"
    assert run_scenario("forged")["receipt"] is None
    timeout = run_scenario("timeout")
    assert timeout["case_state"] == "HUMAN_REVIEW"
    assert timeout["receipt"]["recovered_inr"] == 0


def test_batch_conserves_recovered_money_and_uses_one_ledger():
    batch = run_batch()
    assert len(batch["receipts"]) == batch["n"] == 100
    assert len(batch["summaries"]) == 9
    summary = next(row for row in batch["summaries"] if row["arm"] == "B3")
    assert sum(row["recovered_inr"] for row in batch["receipts"]) == summary["recovered_inr"]
    assert sum(row["provider_call_count"] for row in batch["receipts"]) == summary["provider_calls"]
    assert {row["ledger_sha256"] for row in batch["receipts"]} == {batch["ledger_sha256"]}
    assert all(row["idempotency_key"] for row in batch["receipts"] if row["provider_call_made"])
    assert batch["output_sha256"] == run_batch()["output_sha256"]


def test_serverless_entrypoint_and_bounded_input_contract():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["mode"] == "local_simulator"
    assert client.post("/api/demo/scenario", json={"scenario": "recover"}).json()["provider_call_count"] == 1
    assert client.post("/api/demo/scenario", json={"scenario": "revoked"}).json()["provider_call_count"] == 0
    assert client.post("/api/demo/scenario", json={"scenario": "unknown"}).status_code == 422
    assert client.post("/api/demo/scenario", json={"scenario": "recover", "amount": -1}).status_code == 422


def test_middleware_stops_forgery_denial_ambiguity_and_duplicates():
    host = FastAPI()
    host.add_middleware(MandateGuardMiddleware, webhook_secret="test-secret")
    calls = []

    @host.post("/webhook/razorpay")
    async def endpoint(request: Request):
        calls.append(True)
        # The original body remains available after middleware authentication.
        assert await request.body()
        return request.state.mandateguard

    client = TestClient(host)
    assert client.post("/webhook/razorpay", content=b"{}").status_code == 401
    for name in ("recover", "revoked", "ambiguous"):
        event = replace(make_event(name), event_time=datetime.now(timezone.utc))
        if name == "revoked":
            event = replace(event, mandate_state="revoked")
        if name == "ambiguous":
            event = replace(event, failure_code="UNKNOWN", normalized_failure_reason="UNKNOWN_OR_CONFLICTING",
                            failure_payload={"description": "unmapped signal"})
        payload = to_razorpay_test_payload(event)
        payload["event"] = "payment.failed"
        body, headers = build_signed_delivery(payload, secret="test-secret", event_id=name)
        response = client.post("/webhook/razorpay", content=body, headers=headers)
        assert response.status_code == 200
        assert response.json()["provider_calls"] == 0
        duplicate = client.post("/webhook/razorpay", content=body, headers=headers)
        assert duplicate.json()["status"] == "IGNORED_NON_ACTIONABLE"
    assert len(calls) == 1


def test_unknown_timeout_cannot_be_followed_by_another_automated_action():
    event = make_event("timeout_followup")
    _, _, provider, _, engine = execute(event, timeout=True)
    from bailiff.policies import default_policy, _authority
    policy = default_policy("B2")
    context = EvaluationContext(event=event, policy=policy, proposed_action=ActionType.SEND_EMAIL,
                                authority=_authority(event, policy))
    decision = engine.evaluate(context)
    assert decision.decision == Decision.ESCALATE
    assert engine.execute(context=context, decision=decision) is None
    assert provider.call_count == 1


def test_saved_provider_proof_checks_hash_and_cross_artifact_binding():
    bundle = load_provider_proofs(Path(__file__).resolve().parents[1])
    assert bundle.recovery_verified
    artifacts = deepcopy(dict(bundle.artifacts))
    artifacts["recovery_proof"]["proof"]["amount_minor"] += 1
    assert not ProviderProofBundle(bundle.evidence_dir, artifacts).recovery_verified
    artifacts = deepcopy(dict(bundle.artifacts))
    artifacts["success"]["receipt"]["payment_link_id"] = "plink_unrelated"
    assert not ProviderProofBundle(bundle.evidence_dir, artifacts).recovery_verified


def test_api_default_arms_and_distinct_seed_validation():
    from bailiff.api import app as experiment_app
    client = TestClient(experiment_app)
    result = client.post("/experiments", json={"n": 2})
    assert result.status_code == 200
    identifier = result.json()["experiment_id"]
    assert "pid_rzp" in result.json()["policy_ids"]
    assert client.post(f"/experiments/{identifier}/run", json={"seeds": [1701]*5, "n_per_seed": 2}).status_code == 400


def test_adapter_rejects_other_payment_rails_and_missing_permission():
    import pytest
    from bailiff.razorpay_adapter import normalize_razorpay_autopay_payload, RazorpayPayloadError
    source = to_razorpay_test_payload(make_event("scope"))
    for amount in (True, 10.5, float("inf"), float("nan")):
        payload = deepcopy(source)
        payload["payload"]["payment"]["entity"]["amount"] = amount
        with pytest.raises(RazorpayPayloadError):
            normalize_razorpay_autopay_payload(payload)
    for timestamp in (True, float("inf"), 10**100):
        payload = deepcopy(source)
        payload["created_at"] = timestamp
        with pytest.raises(RazorpayPayloadError):
            normalize_razorpay_autopay_payload(payload)
    payload = deepcopy(source)
    subscription = payload["payload"]["subscription"]["entity"]
    del subscription["status"]
    assert normalize_razorpay_autopay_payload(payload).mandate_state == "unknown"
    del subscription["notes"]["attempt_count"]
    with pytest.raises(RazorpayPayloadError):
        normalize_razorpay_autopay_payload(payload)
    for field, value in (("method", "card"), ("recurring", False)):
        payload = deepcopy(source)
        payload["payload"]["payment"]["entity"][field] = value
        with pytest.raises(RazorpayPayloadError):
            normalize_razorpay_autopay_payload(payload)
    payload = deepcopy(source)
    notes = payload["payload"]["subscription"]["entity"]["notes"]
    del notes["pre_debit_state"]
    del notes["consent_email"]
    event = normalize_razorpay_autopay_payload(payload)
    assert event.pre_debit_state == "missing"
    assert event.consent.email is False
    del notes["is_scheduled_autopay"]
    with pytest.raises(RazorpayPayloadError):
        normalize_razorpay_autopay_payload(payload)


def test_lineage_never_calls_a_decision_id_an_event_or_invents_ai_use():
    from bailiff.lineage import lineage_for, provenance_chain, NOT_PRESENT
    row = {"arm": "B3", "decision_id": "dec_1", "policy_id": "pid_b3", "confidence": 0.94}
    fields = {field.name: field.value for field in lineage_for(row)}
    assert fields["Event ID"] == fields["Policy version"] == NOT_PRESENT
    assert not any(step.title == "B3 interpreter proposal" for step in provenance_chain(row))
