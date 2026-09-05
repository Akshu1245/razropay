"""Actual engine results shared by the web demo, Streamlit and static export.

Every action uses the local simulator. Static hosting replays exported results;
a Python host executes these same functions on demand.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from .demo import make_event, make_ambiguous_event, _ledger, execute
from .fixtures import generate_fixture
from .guardrails import AuditChain
from .metrics import annotate_runs, summarize_runs
from .policies import CANONICAL_ARM_ORDER, PolicyRun, run_policy_case
from .razorpay_adapter import normalize_razorpay_autopay_payload, to_razorpay_test_payload
from .rules import RuleCatalog
from .runner import _event_row
from .webhook import WebhookGate, build_signed_delivery, SIGNATURE_HEADER

SCENARIOS = {
    "recover": ("Recover a failed debit", "A temporary balance failure with valid permission."),
    "revoked": ("Customer cancelled", "The bank error looks retryable. The mandate is revoked."),
    "optout": ("Customer opted out", "Recovery stops when the customer withdraws permission."),
    "notice": ("Notice missing", "A retry must satisfy the configured pre-debit notice rule."),
    "ambiguous": ("AI is uncertain", "Conflicting signals go to a human, with no provider call."),
    "forged": ("Forged webhook", "An invalid signature stops the payload before diagnosis."),
    "timeout": ("Provider timed out", "An unknown outcome requires review before another action."),
}


def receipt_row(run):
    row = _event_row(run, run.ledger_sha256)
    row.update({
        "amount_inr": run.event.amount_minor / 100,
        "recovered_inr": run.event.amount_minor / 100 if run.provider_result and run.provider_result.recovered else 0,
        "mandate_state": run.event.mandate_state,
        "attempt_count": run.event.attempt_count,
        "opted_out": run.event.consent.opted_out,
        "pre_debit_state": run.event.pre_debit_state,
        "provider_call_count": int(run.provider_result is not None),
        "idempotency_key": run.provider_result.idempotency_key if run.provider_result else None,
        "audit_events": list(run.audit_events),
        "model_calls": run.decision.model_calls,
        "interpreter_consulted": run.decision.model_used,
    })
    return row


def run_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise ValueError("unknown demo scenario")
    now = datetime.now(timezone.utc)
    event = make_ambiguous_event("demo_ambiguous") if name == "ambiguous" else make_event("demo_" + name)
    # Keep the long-running server's demo valid across midnight.
    event = replace(event, event_time=now, valid_until=now + timedelta(days=2),
                    proposed_execution_at=(now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0),
                    pre_debit_sent_at=now - timedelta(hours=48), last_attempt_at=now - timedelta(hours=48))
    if name == "revoked":
        event = replace(event, mandate_state="revoked")
    elif name == "optout":
        event = replace(event, consent=replace(event.consent, opted_out=True))
    elif name == "notice":
        event = replace(event, pre_debit_state="missing")
    payload = to_razorpay_test_payload(event)
    payload["created_at"] = int(now.timestamp())
    secret = "mandateguard-public-demo-secret"
    raw, headers = build_signed_delivery(payload, secret=secret, event_id=event.event_id)
    if name == "forged":
        headers[SIGNATURE_HEADER] = "0" * 64
    gate = WebhookGate(secrets=(secret,))
    verdict = gate.verify(raw_body=raw, headers=headers, received_at=now)
    result = {"scenario": name, "title": SCENARIOS[name][0], "description": SCENARIOS[name][1],
              "mode": "local_simulator", "interpreter_mode": "deterministic_offline",
              "ingress": asdict(verdict), "provider_call_count": 0, "receipt": None}
    if not verdict.should_process:
        result.update({"status": "Rejected at ingress", "rejection_evidence": list(gate.rejections)})
        return result
    event = normalize_razorpay_autopay_payload(json.loads(raw))
    ledger = _ledger(event, recoverable=name not in {"revoked", "optout"})
    if name == "timeout":
        decision, provider_result, provider, audit, engine = execute(event, timeout=True)
        run = PolicyRun("B2", event, decision, provider_result, audit_events=tuple(audit.events),
                        audit_verified=audit.verify(), ledger_sha256=ledger.sha256())
        result["case_state"] = engine.cases.get(event.recovery_case_id).state.value
        result["provider_call_count"] = provider.call_count
    else:
        run = run_policy_case(arm="B3", event=event, ledger=ledger)
        result["provider_call_count"] = int(run.provider_result is not None)
    run = annotate_runs([run], ledger)[0]
    result["receipt"] = receipt_row(run)
    result["status"] = ("Human review" if name == "timeout" or run.decision.decision.value in {"abstain", "escalate"}
                        else "Recovered" if run.provider_result and run.provider_result.recovered else "Stopped")
    tampered = AuditChain()
    tampered.events = deepcopy(list(run.audit_events))
    tampered.events[0]["decision"] = "tampered"
    result["tamper_detected"] = not tampered.verify()
    return result


def run_batch() -> dict:
    """Execute all arms against ONE frozen 100-case outcome ledger."""
    events, ledger = generate_fixture("R1_TRANSIENT", 1701, 100)
    events = [normalize_razorpay_autopay_payload(to_razorpay_test_payload(event)) for event in events]
    catalog = RuleCatalog.load()
    summaries, receipts = [], []
    for arm in CANONICAL_ARM_ORDER:
        runs = annotate_runs([run_policy_case(arm=arm, event=event, ledger=ledger) for event in events], ledger)
        summaries.append(summarize_runs(runs, ledger,
            human_review_cost_inr=float(catalog.value("human_review_cost_inr")),
            violation_cost_inr=float(catalog.value("violation_cost_inr"))))
        if arm == "B3":
            receipts = [receipt_row(run) for run in runs]
    result = {"mode": "local_simulator", "interpreter_mode": "deterministic_offline",
              "regime": "R1_TRANSIENT", "seed": 1701, "n": len(events), "arms": list(CANONICAL_ARM_ORDER),
              "ledger_sha256": ledger.sha256(), "rules_sha256": catalog.sha256(),
              "policy_version": catalog.version, "summaries": summaries, "receipts": receipts}
    result["output_sha256"] = sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result
