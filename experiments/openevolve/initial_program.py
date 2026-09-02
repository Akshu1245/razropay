"""OpenEvolve candidate surface for MandateGuard.

Only the block between EVOLVE markers may be mutated. The canonical submission
policy, guardrails, webhook verifier, RecoveryTruth and provider adapters are not
imported here and must remain frozen.
"""

RETRY = "SCHEDULE_RETRY"
STOP = "STOP_RECOVERY"
REVIEW = "ESCALATE_TO_HUMAN"

# EVOLVE-BLOCK-START
def choose_action(reason: str, attempt_count: int) -> str:
    """Return only a proposed policy action; guardrails still authorize it later."""
    retryable = {
        "INSUFFICIENT_FUNDS",
        "BANK_TIMEOUT_OR_TEMPORARY_FAILURE",
    }
    review = {
        "RISK_OR_FRAUD_REJECTED",
        "UNKNOWN_OR_CONFLICTING",
    }
    if reason in retryable:
        return RETRY
    if reason in review:
        return REVIEW
    return STOP
# EVOLVE-BLOCK-END
