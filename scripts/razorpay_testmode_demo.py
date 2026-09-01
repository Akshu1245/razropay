from __future__ import annotations

import argparse
import json

from bailiff.recovery_runtime import RecoveryRequest, RecoveryTruthRuntime, recovery_reference
from bailiff.razorpay_testmode import RazorpayTestModeClient


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Run the provider-backed RecoveryTruth path against Razorpay TEST MODE only. "
            "This creates a customer-initiated Payment Link fallback; it is not an AutoPay debit retry."
        )
    )
    p.add_argument("--order-id", required=True, help="Razorpay Test Mode order id (order_...)")
    p.add_argument("--case-id", required=True, help="Internal recovery case id; hashed into the provider reference")
    p.add_argument("--mandate-id", required=True, help="Mandate/subscription identity used by MandateGuard")
    p.add_argument("--mandate-status", default="active", help="Current merchant-side mandate state")
    p.add_argument("--amount-minor", required=True, type=int, help="Expected INR amount in paise")
    p.add_argument("--decision-id", default="demo_decision")
    p.add_argument("--policy-version", default="mandateguard_policy_0.2")
    p.add_argument(
        "--verify-link-id",
        help="Do not create a new fallback; verify this already-paid Test Mode Payment Link and emit RecoveryProof",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    client = RazorpayTestModeClient.from_env()
    runtime = RecoveryTruthRuntime(client)
    request = RecoveryRequest(
        case_id=args.case_id,
        decision_id=args.decision_id,
        policy_version=args.policy_version,
        order_id=args.order_id,
        mandate_id=args.mandate_id,
        mandate_status=args.mandate_status,
        amount_minor=args.amount_minor,
    )

    if args.verify_link_id:
        from bailiff.recovery_runtime import RecoveryActionReceipt

        reference_id = recovery_reference(args.case_id)
        receipt = RecoveryActionReceipt(
            case_id=args.case_id,
            decision_id=args.decision_id,
            policy_version=args.policy_version,
            action_type="CREATE_PAYMENT_LINK_FALLBACK",
            reference_id=reference_id,
            payment_link_id=args.verify_link_id,
            short_url="",
            amount_minor=args.amount_minor,
            currency="INR",
            prewrite_resolution="RECOVERABLE",
            prewrite_evidence_hash="external-demo-prewrite-evidence-recorded-at-create-step",
        )
        proof = runtime.verify_recovery(receipt)
        print(
            json.dumps(
                {
                    "mode": "razorpay_test_mode_verify",
                    "recovery_verified": True,
                    "provider_action_type": proof.provider_action_type,
                    "provider_action_id": proof.provider_action_id,
                    "payment_id": proof.payment_id,
                    "amount_minor": proof.amount_minor,
                    "currency": proof.currency,
                    "reference_id": proof.reference_id,
                    "postcondition_evidence_hash": proof.postcondition_evidence_hash,
                    "recovery_proof_hash": proof.hash(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    attempt = runtime.execute_customer_fallback(request)
    output: dict[str, object] = {
        "mode": "razorpay_test_mode_execute",
        "executed": attempt.executed,
        "reason_code": attempt.reason_code,
        "financial_truth": attempt.truth.state.value,
        "truth_reason_codes": list(attempt.truth.reason_codes),
        "reference_id": recovery_reference(args.case_id),
    }
    if attempt.receipt is not None:
        output.update(
            {
                "provider_action_type": attempt.receipt.action_type,
                "payment_link_id": attempt.receipt.payment_link_id,
                "short_url": attempt.receipt.short_url,
                "amount_minor": attempt.receipt.amount_minor,
                "currency": attempt.receipt.currency,
                "prewrite_evidence_hash": attempt.receipt.prewrite_evidence_hash,
            }
        )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
