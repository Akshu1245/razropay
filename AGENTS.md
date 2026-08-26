# MandateGuard project rules

MandateGuard evaluates scheduled UPI AutoPay debit failures only. Do not add one off UPI, cards, refunds, write offs, settlement reconciliation, or unrestricted customer messaging without an explicit scope decision.

The canonical policy arm order is B0, B1, B1.5, RZP, B2.25, B2.5, B2.75, B2, B3 (see `bailiff.policies.CANONICAL_ARM_ORDER`, the single source of truth). B1.5 is deterministic retry only. RZP implements Razorpay's own published card retry schedule, reason blind by design, as a benchmark arm rather than a project policy. B2.25/B2.5/B2.75 are diagnostic frontier arms that expose where individual controls trade recovery against violations; never call them safe production defaults. B3 is a bounded interpreter. It may interpret payloads and propose a bounded action, but it has no provider tools and cannot authorize money movement.

All policy arms consume the same frozen common outcome ledger. Never regenerate outcomes separately for an arm. Every final benchmark must record the ledger hash, rules hash, policy version, seed list, and output hash.

All denial paths must prove zero provider calls. All provider actions must have an idempotency key, provider call ID, postcondition, and audit receipt. Timeout with unknown postcondition must route to human review before another action.

Use `legitimate_recovery_forgone_inr` to report recoverable value blocked by controls, `protected_value_by_denial_inr` to report value associated with prohibited actions that were not sent, and `realized_harm_inr` to report prohibited value that actually reached the provider. Never present simulator figures as production revenue.

Every financial metric must be defined by whether a provider call happened, never by the symbolic name of the final action. The baseline path and the guardrail path spell a stop differently, so any metric that branches on that spelling is not comparable across arms. This was a real defect: it once made B1.5 report more than double the legitimate recovery forgone of B2 while also recovering more.

Latent harm in the fixture must never be a pure function of the normalized failure reason. If it is, reason gating alone captures all harm avoidance by construction and no guardrail above B1.5 can ever be shown to be worth its cost. Compliance exposure is drawn independently and the release gate enforces it.

Never report a single recommended arm without the swept price curve beside it. A recommendation computed at one configured cost is an anecdote about that cost.

Every external rule must carry provenance. If a primary source is not pinned and hashed, describe the rule as reported or project policy, not as an official regulation.

Before submitting, run `scripts/test.sh`, `scripts/demo.sh`, and `scripts/evaluate.sh` from a clean checkout. README numbers must be generated from `outputs/`, not typed manually.

## RecoveryTruth v2 rules

`main` is the frozen MandateGuard baseline. RecoveryTruth work belongs on the `recoverytruth-v2` branch until its kill gates pass. Do not weaken an existing MandateGuard invariant to make RecoveryTruth easier to implement.

RecoveryTruth is a **Track 03 recovery preflight**, not a general reconciliation or finance-controller product. It may reconcile only the minimum payment/subscription/mandate/merchant evidence necessary to decide whether an at-risk payment may safely enter recovery.

Never trust an older webhook over newer current provider evidence without recording the reason. A webhook event is evidence about an event-time state; it is not automatically current truth at action time.

An AI hypothesis cannot change, omit, or fabricate an observed source fact. Every AI-supported conclusion must cite evidence IDs that exist in the current immutable `EvidenceBundle`; unknown references are an error.

`UNKNOWN_CONFLICT` is a valid and expected output. Conflicting or missing current provider evidence cannot directly authorize money movement. The correct action is `POLL_PROVIDER`, `HUMAN_REVIEW`, or another non-money resolution step.

Current provider evidence that money already moved has precedence over a model's recoverable hypothesis. A max-confidence model must still be unable to reopen recovery after `captured`, `paid`, `succeeded`, or another configured money-moved state.

Provider timeout means `UNKNOWN` until independently resolved. Never infer failure from timeout and immediately retry.

No numeric recovery probability, expected lift, or rupee value may come directly from an LLM. Quantitative action value must come from a separately evaluated statistical/ML model or controlled experimental estimate.

Held-out state families used for the `Unseen State Challenge` must remain inaccessible during prompt/model tuning. Do not move hard evaluation cases into training/reference data after seeing the result.

Every live or test-mode provider observation stored as evidence must include source/entity ID, observed time, fetched time, raw hash, and trust tier. Secrets and full credentials never enter the evidence artifact.

The judge path must always retain an offline deterministic fallback. Live/test-mode integration is additional evidence, not a prerequisite that can make a clean judge checkout fail.
