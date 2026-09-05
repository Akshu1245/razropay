# MandateGuard — canonical five-minute submission video

Use the local Python-backed workspace at `http://127.0.0.1:8765`. The header must say **Python engine connected** before calling the demonstration live. If it says **Recorded engine evidence**, say exactly that; do not imply fresh Python execution.

The batch figures are synthetic. The separate Razorpay artifact is Test Mode evidence. A Standard Payment Link fallback is not an AutoPay retry, and a created link is not proof of captured payment.

**Do not open with a recovery number.** The story starts with the merchant decision problem, then shows recovery and the cost of restraint together.

## 0:00–0:35 — The merchant decision problem

**Screen:** Top of the MandateGuard workspace.

“A scheduled UPI AutoPay payment fails. The next step is not always retry. A temporary failure may be recoverable, a revoked mandate must stop, and an unknown provider result must be reviewed before another automated action.”

“MandateGuard helps merchants recover failed scheduled UPI AutoPay payments, with explicit controls for when to retry, when to stop, and when to ask a human—with evidence for every decision.”

Point briefly to the five-question decision contract: what failed, what next, why allowed, what happened, and where the evidence is.

## 0:35–1:20 — Run the recovery demonstration

**Action:** Click **Run recovery demonstration**.

“This runs the 100-case batch and the three decisive examples through the shared Python engine. The batch is synthetic and uses a local provider simulator; no customer is contacted and no real AutoPay debit is executed.”

Point to the five batch numbers.

“The recovered INR comes from successful simulated provider postconditions, not a predicted recovery score. I also show payments recovered, cases stopped, cases requiring review, and recoverable value forgone. Controls have a cost, so I do not hide it.”

## 1:20–2:35 — Three decisions judges should remember

### A. Eligible failure

Point to **Retry is permitted**.

“This failure is recoverable and the configured authority checks allow the bounded action. The card shows the full path: failure, diagnosis, controls, provider action and recovered postcondition.”

**Action:** Open its decision receipt.

“The receipt includes the provider-call evidence, idempotency data, postcondition and audit chain.”

**Action:** Click **Verify audit chain + tamper check**.

“The browser recomputes the hashes. The shipped receipt verifies, and changing the first decision breaks the chain. This is tamper-evident evidence, not immutable storage.”

### B. Revoked mandate

Point to **Stop before the provider**.

“The failure itself can look retryable, but the mandate is revoked. Authority ends there. The actual engine result is zero provider calls.”

### C. Unknown provider timeout

Point to **Ask a human before another action**.

“One provider call happened, but the postcondition is unknown. MandateGuard does not call that a failure and retry blindly. The case moves to human review before another automated action.”

## 2:35–3:20 — Explain the AI boundary

**Screen:** AI boundary section.

“AI interprets unclear failure information; deterministic controls decide whether an action is allowed.”

“The bounded interpreter can return a label and confidence. It has no payment tools and cannot restore a revoked mandate, raise an amount limit, or bypass consent and retry controls. Low-confidence interpretation abstains before the provider.”

“If asked about model performance: the repeatable default uses deterministic offline interpretation, and the optional captured real-model artifact proves an integration path only. I do not claim production AI uplift from it.”

## 3:20–4:00 — Separate Razorpay Test Mode proof

**Screen:** Razorpay Test Mode evidence.

“This evidence is separate from the synthetic batch. RecoveryTruth captured a Razorpay Test Mode Standard Payment Link fallback and then independently verified the captured payment. Creating the link alone is not counted as recovered money.”

Point to the already-paid proof.

“In the already-paid case, the saved evidence shows Payment Links stayed zero to zero. No new fallback collection object was created.”

“These are saved Test Mode artifacts shown read-only here, not a fresh provider call from this viewer.”

## 4:00–4:40 — Advanced evaluation without hiding the trade-off

**Action:** Expand **Advanced policy evaluation**.

“All nine canonical policies consume the same frozen outcomes. The comparison shows both simulated recovery and prohibited value executed.”

Point to the complete price sweep.

“There is no universal winning policy. The preferred arm changes with the assumed cost of a prohibited action. The relaxed frontier arms are diagnostic, not safe production defaults.”

“RZP is only a fixed temporal reference derived from a published card schedule. It is not Razorpay's current Intelligent UPI Retry Engine.”

## 4:40–5:00 — Close on the product boundary

Return to the closing card.

“The idea is focused: recover when authority is clear, stop when it ends, escalate uncertainty, and leave evidence.”

“For production, this would still need durable state and scheduling, merchant authentication and tenant isolation, approved provider execution, cross-process reconciliation, and validation on permissioned merchant failures.”

“MandateGuard: recover deliberately. Stop when authority ends. Escalate uncertainty. Leave evidence.”

## Recording checklist

- Keep the browser at 100% zoom and use the local Python-backed workspace.
- Rehearse once so the video ends before five minutes.
- Do not spend time reading policy codes aloud.
- Never call synthetic INR merchant revenue.
- Never call the Payment Link fallback an AutoPay retry.
- Never count link creation as proof of captured payment.
- Never call the audit chain tamper-proof or immutable.
- Never claim AI uplift or production model accuracy that has not been measured.
- Leave the source repository and demo URL visible only after you have verified the exact submitted links in a signed-out browser.
