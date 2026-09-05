# MandateGuard — canonical five-minute submission video

Use the Python-backed workspace at `http://127.0.0.1:8765`. The header must say **Python engine connected** before calling the demonstration live. If it says **Recorded engine evidence**, say exactly that; do not imply fresh Python execution.

The batch figures are synthetic. Razorpay Test Mode evidence is separate. A Standard Payment Link fallback is not an AutoPay retry, and a created link is not proof of captured payment.

**Do not open with a recovery number.**

## 0:00–0:35 — The decision problem

**Screen:** top of the MandateGuard workspace.

“A scheduled UPI AutoPay payment fails. The next step is not always retry. A temporary failure may be recoverable, a revoked mandate must stop, and an unknown provider result must be reviewed before another automated action.”

“MandateGuard helps merchants recover failed scheduled UPI AutoPay payments, with explicit controls for when to retry, when to stop, and when to ask a human—with evidence for every decision.”

Point to the five-question decision contract.

## 0:35–1:15 — Run the batch

**Action:** click **Run recovery demonstration**.

“This runs a fixed 100-case synthetic batch and the three decisive examples through the shared Python engine. No customer is contacted and no real AutoPay debit is executed.”

Point to the summary.

“Recovered INR is counted from successful simulated provider postconditions, not from a prediction. I also show payments recovered, stopped cases, human review, unknown outcomes and legitimate recovery forgone. Controls have a cost, so I show it.”

## 1:15–2:25 — Three decisions

### Eligible failure

Point to **Retry is permitted**.

“The failure is recoverable and authority checks permit one bounded action.”

Open the receipt.

“The receipt carries the call identifier, idempotency evidence, postcondition and audit chain.”

Run **Verify audit chain + tamper check**.

“The shipped chain verifies. Editing an earlier decision breaks verification. This is tamper-evident, not immutable.”

### Revoked mandate

Point to **Stop before the provider**.

“This can look retryable from the failure reason alone, but the mandate is revoked. Authority ends here, and the actual result is zero provider calls.”

### Unknown timeout

Point to **Ask a human before another action**.

“One provider call was attempted, but the postcondition is unknown. MandateGuard does not call that a normal failure and retry blindly. It holds the case for review first.”

## 2:25–3:05 — AI boundary

**Screen:** AI boundary.

“AI interprets unclear failure information; deterministic controls decide whether an action is allowed.”

“The interpreter can normalize an ambiguous reason and confidence. It has no payment tools and cannot restore a mandate, raise an amount limit, refill retry attempts or bypass consent. Low confidence abstains before the provider.”

Expand the interpreter comparison briefly.

“The repeatable benchmark uses the offline interpreter. The saved real-model artifact proves integration, not production accuracy or measured uplift.”

## 3:05–3:45 — Razorpay Test Mode proof

**Screen:** Razorpay Test Mode evidence.

“This is separate from the synthetic batch. RecoveryTruth captured a Razorpay Test Mode Standard Payment Link fallback and then independently verified the captured payment. Creating the link alone is not counted as recovered money.”

Point to the already-paid proof.

“In the already-paid case, the evidence shows no new fallback write.”

## 3:45–4:25 — Evaluation without hiding trade-offs

Expand **Advanced policy evaluation**.

“All nine policies consume the same frozen outcomes. Recovery and prohibited execution are compared on the same cases.”

Point to the price sweep.

“There is no universal winning policy. The preferred arm changes with the assumed cost of an unsafe action. The relaxed frontier arms are diagnostic, not production defaults.”

“RZP is only a fixed temporal reference derived from a published card schedule. It is not Razorpay's current Intelligent UPI Retry Engine.”

## 4:25–4:45 — What broke

“During development, the first judge UI was too research-heavy, static mode logged a health 404, a provider timeout needed a real unknown state, and the deep verifier was mutating evidence it later checksummed. Those failures became browser, integrity and release gates instead of being hidden.”

## 4:45–5:00 — Close

Return to the closing card.

“The idea is focused: recover when authority is clear, stop when it ends, escalate uncertainty, and leave evidence.”

“MandateGuard: recover deliberately. Stop when authority ends. Escalate uncertainty. Leave evidence.”

## Recording checklist

- Browser at 100% zoom; use the verified Python-backed workspace.
- Rehearse once and stay under five minutes.
- Do not read policy codes aloud.
- Never call synthetic INR merchant revenue.
- Never call the Payment Link fallback an AutoPay retry.
- Never count link creation as captured payment.
- Never call the audit chain tamper-proof or immutable.
- Never claim production AI uplift or accuracy that has not been measured.
- Verify repository, demo and video URLs in a signed-out browser before submission.
