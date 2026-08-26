#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import sys

import httpx

from bailiff.domain import ConsentState, RecoveryEvent
from bailiff.evidence import EvidenceSource
from bailiff.evidence_assembler import EvidenceAssembler
from bailiff.razorpay_client import RazorpayReadClient
from bailiff.recoverytruth import RecoveryTruthController
from bailiff.replay import CommonOutcomeLedger
from bailiff.state_resolution import CanonicalFinancialState, StateHypothesis


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
NOW = datetime(2026, 8, 26, 3, 0, tzinfo=timezone.utc)


def heading(text: str) -> None:
    print(f"\n{CYAN}{text}{RESET}")


def line(label: str, value: str, colour: str = "") -> None:
    print(f"  {label:<28} {colour}{value}{RESET if colour else ''}")


def make_event(case: str, *, payment_id: str, subscription_id: str, normalized_reason: str) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=f"evt_{case}",
        merchant_id="merchant_demo",
        customer_id=f"customer_{case}",
        mandate_id=f"mandate_{case}",
        scheduled_execution_id=f"scheduled_{case}",
        recovery_case_id=f"case_{case}",
        correlation_id=f"corr_{case}",
        amount_minor=249900,
        currency="INR",
        failure_code="PROVIDER_FAILURE",
        mandate_state="active",
        attempt_count=1,
        pre_debit_state="valid",
        event_time=NOW,
        failure_payload={
            "provider": "razorpay",
            "provider_event": "payment.failed",
            "payment_id": payment_id,
            "subscription_id": subscription_id,
            "error_code": "PROVIDER_FAILURE",
            "error_reason": "unknown",
            "error_description": "failure event received",
            "normalized_reason": normalized_reason,
        },
        mcc="5817",
        consent=ConsentState(email=True),
        source="razorpay_test_payload",
        payload_hash=f"sha256:webhook:{case}",
        normalized_failure_reason=normalized_reason,
        proposed_execution_at=datetime(2026, 8, 27, 3, 0, tzinfo=timezone.utc),
        last_attempt_at=datetime(2026, 8, 25, 2, 0, tzinfo=timezone.utc),
        pre_debit_sent_at=datetime(2026, 8, 25, 1, 0, tzinfo=timezone.utc),
    )


def mock_reader(responses: dict[str, dict[str, object]]) -> RazorpayReadClient:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = responses.get(request.url.path)
        if payload is None:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json=payload)

    client = httpx.Client(base_url="https://api.razorpay.com", transport=httpx.MockTransport(handler))
    return RazorpayReadClient(client=client)


def hypothesis_resolver(state: CanonicalFinancialState, confidence: float):
    def resolve(bundle):
        payment = bundle.current(EvidenceSource.PAYMENT_API)
        support = (payment.evidence_id,) if payment is not None else ()
        return StateHypothesis(state=state, confidence=confidence, supporting_evidence=support)

    return resolve


def provider_calls(run) -> int:
    if run.policy_run is None:
        return 0
    return 1 if run.policy_run.provider_result is not None else 0


def main() -> int:
    print(f"{CYAN}RecoveryTruth · Track 03 recovery preflight proof{RESET}")
    print("Synthetic/demo evidence only. Razorpay reads below are deterministic HTTP mocks of the documented GET shapes.")

    # ------------------------------------------------------------------ A
    heading("CASE A · failed webhook, but current payment is already captured")
    event_a = make_event(
        "already_paid",
        payment_id="pay_alreadypaid",
        subscription_id="sub_alreadypaid",
        normalized_reason="INSUFFICIENT_FUNDS",
    )
    assembler_a = EvidenceAssembler(
        razorpay=mock_reader(
            {
                "/v1/payments/pay_alreadypaid": {
                    "id": "pay_alreadypaid",
                    "status": "captured",
                    "amount": 249900,
                    "currency": "INR",
                },
                "/v1/subscriptions/sub_alreadypaid": {
                    "id": "sub_alreadypaid",
                    "status": "awaiting_authorization",
                },
            }
        )
    )
    evidence_a = assembler_a.assemble(
        event=event_a,
        current_mandate_state="active",
        merchant_entitlement_state="not_activated",
        fetched_at=NOW,
    )
    run_a = RecoveryTruthController(
        resolver=hypothesis_resolver(CanonicalFinancialState.RECOVERABLE_FAILURE, 1.0)
    ).run(
        event=event_a,
        evidence=evidence_a,
        ledger=CommonOutcomeLedger.from_seed(seed=11, case_ids=[event_a.recovery_case_id]),
    )
    line("old webhook", "FAILED")
    line("current Payment API", evidence_a.current(EvidenceSource.PAYMENT_API).observed_state.upper(), GREEN)
    line("current Subscription API", evidence_a.current(EvidenceSource.SUBSCRIPTION_API).observed_state.upper())
    line("merchant entitlement", evidence_a.current(EvidenceSource.MERCHANT_ENTITLEMENT).observed_state.upper())
    line("hostile model proposal", "RECOVERABLE · confidence 1.00", RED)
    line("RecoveryTruth", f"{run_a.preflight.state.value} → {run_a.preflight.resolution_action.value}", GREEN)
    line("recovery provider calls", str(provider_calls(run_a)), GREEN if provider_calls(run_a) == 0 else RED)

    # ------------------------------------------------------------------ B
    heading("CASE B · current payment failed, unseen semantics indicate terminal risk")
    event_b = make_event(
        "terminal_risk",
        payment_id="pay_terminalrisk",
        subscription_id="sub_terminalrisk",
        normalized_reason="UNKNOWN_OR_CONFLICTING",
    )
    assembler_b = EvidenceAssembler(
        razorpay=mock_reader(
            {
                "/v1/payments/pay_terminalrisk": {
                    "id": "pay_terminalrisk",
                    "status": "failed",
                    "error_code": "RISK_77",
                    "error_reason": "issuer_security_decline",
                    "error_description": "issuer blocked transaction after suspected fraud screening",
                },
                "/v1/subscriptions/sub_terminalrisk": {"id": "sub_terminalrisk", "status": "pending"},
            }
        )
    )
    evidence_b = assembler_b.assemble(event=event_b, current_mandate_state="active", fetched_at=NOW)
    run_b = RecoveryTruthController(
        resolver=hypothesis_resolver(CanonicalFinancialState.TERMINAL_FAILURE, 0.94)
    ).run(
        event=event_b,
        evidence=evidence_b,
        ledger=CommonOutcomeLedger.from_seed(seed=12, case_ids=[event_b.recovery_case_id]),
    )
    payment_b = evidence_b.current(EvidenceSource.PAYMENT_API)
    line("current payment", payment_b.observed_state.upper())
    line("unseen provider text", str(payment_b.attributes.get("error_description")))
    line("bounded resolver", "TERMINAL_FAILURE · confidence 0.94", YELLOW)
    line("RecoveryTruth", f"{run_b.preflight.decision.value} → {run_b.preflight.resolution_action.value}", GREEN)
    line("recovery provider calls", str(provider_calls(run_b)), GREEN if provider_calls(run_b) == 0 else RED)

    # ------------------------------------------------------------------ C
    heading("CASE C · current failure is recoverable, then MandateGuard owns the money boundary")
    event_c = make_event(
        "recoverable",
        payment_id="pay_recoverable",
        subscription_id="sub_recoverable",
        normalized_reason="BANK_TIMEOUT_OR_TEMPORARY_FAILURE",
    )
    assembler_c = EvidenceAssembler(
        razorpay=mock_reader(
            {
                "/v1/payments/pay_recoverable": {
                    "id": "pay_recoverable",
                    "status": "failed",
                    "error_code": "HNA",
                    "error_reason": "host_not_available",
                    "error_description": "upstream bank host did not respond before timeout",
                },
                "/v1/subscriptions/sub_recoverable": {"id": "sub_recoverable", "status": "pending"},
            }
        )
    )
    evidence_c = assembler_c.assemble(event=event_c, current_mandate_state="active", fetched_at=NOW)
    run_c = RecoveryTruthController(
        resolver=hypothesis_resolver(CanonicalFinancialState.RECOVERABLE_FAILURE, 0.91)
    ).run(
        event=event_c,
        evidence=evidence_c,
        ledger=CommonOutcomeLedger.from_seed(seed=13, case_ids=[event_c.recovery_case_id]),
    )
    line("bounded resolver", "RECOVERABLE_FAILURE · confidence 0.91", YELLOW)
    line("preflight", run_c.preflight.decision.value, GREEN)
    line("MandateGuard handoff", run_c.policy_run.arm if run_c.policy_run else "NONE")
    line("MandateGuard audit", "VERIFIED" if run_c.policy_run and run_c.policy_run.audit_verified else "FAILED")
    line("provider calls", str(provider_calls(run_c)), GREEN if provider_calls(run_c) == 1 else RED)
    if run_c.provider_result is not None:
        line("postcondition", run_c.provider_result.postcondition_state)

    ok = (
        provider_calls(run_a) == 0
        and run_a.preflight.state is CanonicalFinancialState.ENTITLEMENT_MISMATCH
        and provider_calls(run_b) == 0
        and run_b.preflight.state is CanonicalFinancialState.TERMINAL_FAILURE
        and run_c.policy_run is not None
        and run_c.policy_run.audit_verified
        and provider_calls(run_c) == 1
    )
    print()
    if ok:
        print(f"{GREEN}PASS · Evidence establishes state. AI resolves uncertainty. MandateGuard controls the money.{RESET}")
        return 0
    print(f"{RED}FAIL · one or more recovery-boundary invariants did not hold{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
