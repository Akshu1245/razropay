# MandateGuard — panel answers to memorize

Keep every answer short, concede the limitation first, then point to the checkable proof.

## “Where is the agent?”

> Razorpay already has recovery agents. MandateGuard is the harness in front of a recovery policy: it authenticates the event, evaluates a candidate policy on a frozen ledger, enforces deterministic authority at runtime, and proves both execution and refusal at the provider boundary. In the benchmark, permitted retries really call the local provider simulator; denied and abstained cases must record zero provider calls. RecoveryTruth adds a separate Razorpay Test Mode execution path for one bounded customer-initiated fallback.

Do not say MandateGuard replaces Intelligent Retry or Agent Studio.

## “Where is the AI?”

> The non-B3 policy arms are deterministic on purpose because consent, mandate state, timing and retry-budget checks should not depend on a model. B3 uses a bounded real-model interpreter only for ambiguous failure meaning. The model has no payment authority. If confidence is low, B3 abstains to human review with zero provider calls; even a hostile interpreter cannot turn a revoked mandate into an allowed action.

The design choice is **where not to use AI**.

## “Isn’t `RZP` a strawman?”

> `RZP` is explicitly a fixed temporal reference derived from Razorpay's published **card** retry schedule. It is not Razorpay's current Intelligent UPI Retry Engine and MandateGuard has not been evaluated against Razorpay production decision logic. The narrow finding is that, on this frozen synthetic scheduled-AutoPay ledger, the tested reason-aware arms outperform that fixed temporal reference on the stated metrics.

If asked what would change your mind:

> Another reproducible policy run on the same frozen ledger and metrics that matches or beats the reason-aware arms. The harness should be willing to prove me wrong.

## “Is this real?”

> The benchmark rupees are synthetic counterfactuals and the default provider is a local simulator. I say that before showing any result. What is real is the code path and its invariants: Razorpay-style webhook HMAC verification, attacked 39 ways in tests; deterministic guardrails; zero-provider-call refusal checks; 283 passing tests; 14/14 deliberately reintroduced defects caught; RecoveryTruth's state resolver and write fence; and the Test Mode-only Razorpay adapter. A standard Payment Link fallback is not an AutoPay retry. A credentialed Test Mode receipt, safe block and RecoveryProof should only be claimed after those artifacts actually exist.

## “Why should Razorpay care if it already recovers?”

> Because a configurable recovery engine still needs a pre-deployment answer to: what will this configuration recover, what legitimate recovery will it refuse, what prohibited value can it expose, and can every refusal be proven to have stopped before the provider boundary? MandateGuard is that evaluation and refusal-proof harness.

## “Why lead with refusals instead of recovered money?”

> Because the ungated policies can recover more. Hiding that would make the benchmark useless. MandateGuard reports recovery, legitimate recovery forgone, prohibited value, violations and provider calls together. The product is the instrument that exposes the trade-off, not a claim that the strictest policy always wins.

## “Is the hash chain tamper-proof?”

> No. It is tamper-evident evidence: modifying historical evidence causes verification to fail. I do not claim it prevents someone with write access from changing bytes; I claim the change is detectable under the verification model.

## “What is the Test Mode action?”

> A standard customer-initiated Razorpay Payment Link fallback in Test Mode. It is not an AutoPay debit retry. Before the write, RecoveryTruth re-reads the current Order and Payments. If the case is already paid, in-flight, conflicting, unknown or terminal, it blocks instead of creating a second recovery action.

## “What would you do in week one if you joined?”

> I would plug this harness in front of Intelligent Retry templates so a merchant can see recovered versus refused before enabling a configuration. A failed-payment diagnostic explains why a debit failed; MandateGuard proves when the compliant action is **not** to debit again.
