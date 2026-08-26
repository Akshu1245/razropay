# RecoveryTruth v2 — Frozen Build Spec

Status: active build branch (`recoverytruth-v2`)
Baseline: `main` remains the frozen, verified MandateGuard submission until this branch clears its kill gates.

## One-line product

RecoveryTruth is a Track 03 recovery preflight: before a recovery action is allowed to execute, it assembles current payment evidence, resolves whether revenue is actually still at risk, abstains when the state remains contradictory or unknown, and then hands only resolved recoverable cases to MandateGuard for bounded execution.

## Problem boundary

A failed-payment event is evidence about what was true when that event was emitted; it is not sufficient by itself to prove the payment is still failed when recovery executes. RecoveryTruth exists to prevent a recovery agent from acting on stale, incomplete, duplicated, out-of-order, or contradictory state.

This remains a Track 03 project. It is not a general finance reconciliation platform. The only reconciliation-like work permitted in this branch is the minimum preflight required to decide whether an at-risk payment may safely enter a recovery workflow.

## Core invariant

**No second money action may be authorized while current financial state is unresolved or while authoritative current evidence shows money already moved.**

An AI hypothesis can interpret evidence. It cannot rewrite evidence, invent evidence IDs, expand authority, or make a blocked recovery executable.

## Evidence model

Every observation used by RecoveryTruth must be represented as a typed immutable evidence item with:

- evidence ID
- source
- entity ID
- observed state
- observed timestamp
- fetched timestamp
- raw payload hash
- trust tier

Initial sources:

- signed webhook event/history
- current Payment API state
- current Subscription API state
- current mandate/authorization state
- merchant entitlement/order state
- prior recovery history

Customer/support text may be added later as low-trust interpretive evidence but can never independently authorize a money action.

## State resolver contract

The bounded AI resolver must return a typed hypothesis:

- canonical state
- calibrated confidence
- supporting evidence IDs
- contradicting evidence IDs
- unknown fields

The deterministic consistency gate owns the executable verdict.

Initial canonical states:

- `RECOVERABLE_FAILURE`
- `TERMINAL_FAILURE`
- `MONEY_ALREADY_MOVED`
- `ENTITLEMENT_MISMATCH`
- `MANDATE_NOT_ACTIONABLE`
- `UNKNOWN_CONFLICT`

Initial resolution actions:

- `PROCEED_TO_RECOVERY`
- `STOP_RECOVERY`
- `RECONCILE_ENTITLEMENT`
- `POLL_PROVIDER`
- `HUMAN_REVIEW`

## Precedence rules

1. Current provider evidence that money moved blocks another money action regardless of model output.
2. A revoked/cancelled/paused/expired mandate blocks recovery regardless of model confidence.
3. Missing current provider state is an abstention; an older failed webhook is not enough to proceed.
4. A high-confidence terminal interpretation may stop recovery but may never create a provider action.
5. Only a current failed payment + actionable mandate + sufficiently confident recoverable hypothesis may hand off to MandateGuard.
6. Provider timeout or unknown postcondition remains `UNKNOWN` until independently resolved.
7. A hypothesis that references an evidence ID not present in the bundle is invalid.

## Hero cases required before UI work

The vertical slice is not complete until these cases pass from a clean checkout:

1. **Consistent recoverable** — current payment failed, mandate active, high-confidence recoverable hypothesis -> hand off to MandateGuard.
2. **Already paid after failed webhook** — older webhook failed, newer current payment captured -> stop; zero recovery provider calls.
3. **Paid but entitlement not converged** — payment captured while subscription/merchant entitlement is pending/inactive -> deny second money action; route to entitlement resolution.
4. **Unknown/contradictory** — missing current payment truth or low-confidence hypothesis -> abstain/poll/human; zero recovery provider calls.
5. **Compromised model** — max-confidence recoverable output cannot override captured payment or dead mandate evidence.

## Evaluation plan

The headline AI evaluation must use a held-out `Unseen State Challenge`, not a random row split from one easy generator.

Held-out families should include:

- unseen reason codes / issuer strings
- misspelled or truncated descriptions
- duplicated webhook delivery
- out-of-order webhooks
- stale failure webhook + newer captured provider state
- captured payment + pending subscription
- captured payment + inactive merchant entitlement
- provider timeout followed by late success
- mandate revoked after the original failure
- missing provider source
- conflicting source/reason combinations

Systems compared on the same cases:

1. exact lookup baseline
2. deterministic taxonomy baseline
3. LLM-only resolver
4. RecoveryTruth (LLM hypothesis + deterministic evidence verification + abstention + MandateGuard)

## Metrics

- state-resolution accuracy
- selective accuracy
- automation coverage
- unsafe second-action rate
- unknown-postcondition escape rate
- duplicate provider-call rate
- unnecessary customer-contact rate
- incremental recovered INR on the recovery batch
- legitimate recovery forgone
- provider/API calls per resolved case
- violations
- evidence-chain verification

No LLM may generate the reported recovery probability or rupee lift directly. Economic probabilities must come from a separately evaluated statistical/ML or controlled experimental model.

## Razorpay integration target

Keep a deterministic offline judge path. Separately capture Razorpay Test Mode evidence for a read-before-act / verify-after-act flow:

signed test webhook -> fetch current provider state -> resolve/abstain -> MandateGuard -> permitted test-mode recovery action -> re-fetch/confirm postcondition -> audit receipt.

Credentials are environment-only and never committed.

## Non-goals until all P0 kill gates pass

Do not add:

- voice recovery
- generic chatbot
- multi-agent swarm
- blockchain
- Kafka/Kubernetes
- database rewrite
- multiple LLM-provider logos for appearance
- unrestricted customer messaging
- general settlement reconciliation
- dashboard redesign

## P0 kill gates

### Gate A — vertical slice

All five hero cases above pass in CI. Existing MandateGuard tests remain green.

### Gate B — AI earns its place

On held-out ambiguous/unseen cases, the AI-assisted system must show measurable value over deterministic taxonomy through higher selective accuracy, useful additional coverage at a controlled error rate, or materially safer abstention. If it does not, report that result and change the AI role rather than fabricating benefit.

The deterministic comparison is frozen before the real-model run. The real model does not get a lower bar simply because it is an LLM.

### Gate C — provider truth

At least one Razorpay Test Mode read/verification flow is captured with evidence hashes and no secrets.

### Gate D — release

Fresh clone/install/test/demo/evaluation/release checks all pass and every README headline number is artifact-derived.

## Judge story

**Evidence establishes state. AI resolves uncertainty. Recovery intelligence chooses. MandateGuard authorizes. Razorpay executes. Postcondition confirms. Evidence proves.**
