# Panel Q&A — short answers that survive follow-up

Use these in your own words. Concede the real limitation first, then point to executable proof.

## “Where is the agent?”

The recovery policy is the agentic loop: ingest failure evidence, diagnose, propose next action, pass deterministic authorization, execute only if allowed, verify the postcondition, then stop or escalate.

The important part is not another detect-and-retry dashboard. Unsafe non-actions are first-class outcomes and carry provider-call evidence.

## “Where is the AI? This looks like rules.”

That is deliberate. Revoked mandate, exhausted attempt budget, missing consent and amount authority are deterministic constraints and should not depend on an LLM.

B3 is the bounded interpreter arm. A model may normalize an ambiguous provider payload and return a reason plus confidence. It cannot authorize payment action, widen authority, change mandate state or bypass the guardrail layer.

> **AI interprets. Policy authorizes. Provider executes. Evidence proves.**

A compromised or overconfident interpreter still cannot move a revoked mandate past deterministic authority.

## “Doesn’t Razorpay already do recovery?”

Yes. **Razorpay already recovers; MandateGuard evaluates whether a recovery policy should be trusted before it goes live.**

The project does not claim Razorpay lacks recovery. The proposal is an evidence-backed recovery-policy trust layer: compare candidate behavior on common outcomes, prove refusals, expose recovery forgone, and preserve case-level receipts.

## “Isn’t RZP a strawman?”

It would be if presented as Razorpay's current UPI retry engine. It is not.

`RZP` is a fixed temporal reference derived from a published **card** schedule. It does not reproduce Intelligent UPI Retry, and MandateGuard has not been evaluated against Razorpay's production decision logic.

## “Is this real or synthetic?”

The batch benchmark is synthetic and offline. Every rupee number in that benchmark is a counterfactual value, not observed merchant revenue.

The executable safety properties are real software behavior: raw-body HMAC validation, replay/order controls, authority attenuation, guardrails, provider-call accounting, abstention, timeout handling, audit verification and the independent checker. The webhook boundary is attacked 42 ways in tests. The final release gate runs 308 tests and a 14/14 mutation check.

Separately, RecoveryTruth contains **Razorpay Test Mode only** evidence. Its write is a Standard Payment Link fallback, not an AutoPay retry. The saved proof independently verifies captured payment and contains an already-paid zero-write case.

## “What does the RecoveryProof prove?”

It binds the recovery case to decision evidence, policy version, authority expiry, original Order, mandate, pre-write financial truth, provider action, postcondition evidence, captured Payment, amount, currency and recovery reference.

The proof is tamper-evident. It does not make the underlying files immutable.

## “Does a decision hash authorize an external caller?”

No. In the Test Mode harness the decision evidence hash binds to MandateGuard decision/audit evidence. It is not a signed external capability token.

The current claim is narrower: deterministic in-process authority decides whether execution is permitted, and the Test Mode harness proves provider-side truth/write/postcondition evidence.

## “Why not maximize recovered money?”

Because an ungated policy can recover more by executing actions that should have been refused.

MandateGuard therefore reports recovery beside protected value by denial, realized harm, prohibited execution rate, violations, legitimate recovery forgone and sensitivity to the assumed harm price. The complete price curve matters more than the biggest rupee number.

## “What would you do inside Razorpay?”

I would not try to replace Intelligent Retry or Agent Studio. I would use this as an evaluation and evidence layer around recovery configurations: replay candidate policies against common outcomes, inspect recovery versus refusal, and require proof of safe stopping before rollout.

## “What broke during development?”

Several failures became permanent verification gates:

- the first judge UX exposed research before the product, so it was rebuilt around one action and three cases;
- static health probing caused a browser 404, so static mode received an explicit health marker;
- an unknown provider timeout could not safely be called “failed,” so it became a distinct human-review state;
- deep verification mutated generated evidence, so it was isolated from the shipped checkout;
- asynchronous boundary-case switching could display a late response for the wrong selection, so request-selection protection and browser coverage were added.

## Four sentences to remember

1. **Razorpay already recovers; MandateGuard evaluates whether a recovery policy should be trusted before it goes live.**
2. **Synthetic rupees stay synthetic; the real Test Mode artifact is separate evidence.**
3. **Payment Link fallback is not an AutoPay retry, and RZP is not Intelligent Retry.**
4. **A refusal is only interesting when provider calls are provably zero.**
