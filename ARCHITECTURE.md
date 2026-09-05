# MandateGuard Architecture

## Purpose

MandateGuard is a bounded recovery decision system for failed scheduled UPI AutoPay payments. It combines a reproducible nine-policy evaluation harness with a deterministic execution authority and case-level evidence.

The judge-facing product is `public/`, served by `api/index.py`. The API invokes `bailiff/showcase.py`, which uses the shared recovery engine. Static hosting may replay `public/evidence.json`, but it is explicitly labelled **Recorded engine evidence**.

> **AI interprets. Policy authorizes. Provider executes. Evidence proves.**

The synthetic benchmark and the saved Razorpay Test Mode proof are separate evidence domains. The Test Mode fallback is a Standard Payment Link example, not a production AutoPay retry.

## Runtime flow

```text
Raw scheduled AutoPay failure
          |
          v
HMAC authentication / replay-order checks
          |
          v
Razorpay-shaped adapter -> canonical RecoveryEvent
          |
          v
deterministic diagnosis ── ambiguous/conflicting ──> bounded interpreter
          |                                      label + confidence only
          +--------------------------+---------------------+
                                     |
                                     v
                         deterministic authority envelope
                                     |
                                     v
                              guardrail engine
                         /                         \
                deny / abstain                   allow
                   |                               |
          zero provider calls                      v
                   |                       idempotency gate
                   |                               |
                   |                               v
                   |                        provider action
                   |                               |
                   +----------------------> postcondition
                                                   |
                                      known success/failure or
                                      UNKNOWN_POSTCONDITION
                                                   |
                                                   v
                                     decision + audit receipt
```

## Canonical policy arms

The evidence contract keeps this order unchanged:

**B0, B1, B1.5, RZP, B2.25, B2.5, B2.75, B2, B3**

| Arm | Purpose |
|---|---|
| `B0` | no-intervention control |
| `B1` | ungated retry baseline |
| `B1.5` | deterministic transient-reason retry |
| `RZP` | fixed temporal reference from a published card schedule |
| `B2.25` | timing frontier diagnostic |
| `B2.5` | timing + attempt frontier diagnostic |
| `B2.75` | timing + attempt + consent frontier diagnostic |
| `B2` | complete deterministic guardrail profile |
| `B3` | B2 guardrails plus bounded interpretation for ambiguity |

The frontier arms are diagnostic counterfactuals, not safe production defaults. `RZP` is not Razorpay's current Intelligent UPI Retry Engine.

## Deterministic authority boundary

Each recovery case carries an authority envelope that binds:

- recovery case identity;
- mandate/scheduled execution identity;
- allowed action classes;
- amount ceiling;
- attempts remaining;
- consent snapshot;
- authority expiry.

Authority can only attenuate. A derived authority cannot add actions, raise the amount, replenish attempts, extend expiry, restore a mandate or change case identity.

Before execution, the guardrail engine checks consent, opt-out state, mandate state, terminal state, retry budget, retry gap, pre-debit notice state, execution window, amount ceiling/review, authority expiry and action class.

### Required decision semantics

| Situation | Required result |
|---|---|
| eligible recoverable failure | one permitted provider action + postcondition |
| revoked/cancelled/paused/expired mandate | deny before provider |
| opted-out contact/action | deny before provider |
| exhausted retry budget | deny before provider |
| invalid timing/pre-debit state | deny before provider |
| ambiguous low-confidence interpretation | abstain before provider |
| exact replay | reuse original result; no second call |
| provider timeout with unknown postcondition | human review before another automated action |
| edited historical receipt | hash-chain verification fails |

## AI boundary

The interpreter exists only to normalize ambiguous or conflicting failure information. It receives no payment/provider tools and cannot authorize execution.

Its output is bounded to a normalized reason/confidence or abstention. The same deterministic authority and guardrail engine still decides whether any action is permitted.

Unavailability, malformed output, conflict or low confidence becomes `ABSTAIN`, which routes to human review with zero provider calls.

The default final evaluation uses a deterministic offline interpreter for reproducibility. Optional real-model evidence demonstrates integration only; it is not a production accuracy or recovery-uplift result.

## Provider and idempotency boundary

Provider execution is downstream of deterministic authorization.

A permitted action records:

- idempotency key;
- provider call identifier;
- request/decision binding;
- provider result;
- postcondition;
- audit receipt.

Financial metrics depend on whether a provider call actually happened.

A timeout after a write is not converted into a convenient “failed” state. `UNKNOWN_POSTCONDITION` blocks another automated action and requires reconciliation/human review.

## Evidence model

Decision receipts form a SHA-256 hash chain. The browser recomputes the chain and intentionally edits an earlier decision to prove verification then fails.

This provides tamper evidence, not immutable storage.

Denied/abstained paths must prove `provider_calls = 0`. A contradictory record is an invariant failure, not a display problem.

Webhook evidence preserves raw provider signal and payload hash. Authentication occurs on raw bytes before normalization. Duplicate, stale, forged and out-of-order deliveries are tested.

## Evaluation contract

Every policy receives the same generated cases and the same common-outcome ledger. Latent recoverable value and prohibited/harmful value are hidden from policy decisions and used only for scoring.

The final protocol uses:

- 20 fixed seeds;
- 3 regimes;
- 100 cases per seed/regime;
- 9 canonical arms;
- 54,000 policy decisions.

The report keeps distinct:

- incremental recovered INR;
- legitimate recovery forgone;
- protected value by denial;
- realized harm;
- prohibited execution rate;
- violations;
- provider calls;
- abstentions/human review;
- net value under multiple harm-price assumptions.

Compliance exposure is generated independently of normalized failure reason so reason gating cannot trivially explain all safety value. `ROBUSTNESS.md` sweeps fixture assumptions, while `outputs/sensitivity.json` sweeps harm/violation prices.

A recommended arm is never presented without its price curve.

## Razorpay Test Mode boundary

RecoveryTruth is separate from the synthetic benchmark.

It records a bounded Razorpay Test Mode Standard Payment Link fallback and independently verifies captured-payment evidence. Link creation alone is not counted as recovery. An already-paid case records a safe block with zero new fallback write.

Saved sanitized artifacts live in `docs/testmode_evidence/`.

## Canonical surfaces

| Surface | Role |
|---|---|
| `public/` + `api/index.py` | primary judge-facing product |
| `SUBMISSION_READINESS.md` | canonical final report |
| `outputs/report.md` | generated benchmark appendix |
| `RECOVERYTRUTH.md` | provider-proof boundary |
| `ROBUSTNESS.md` | assumption sensitivity |
| `docs/JUDGE_RUNBOOK.md` | reviewer fast path |
| `docs/panel_qa.md` | technical follow-up |
| `app.py` / `provider_proof_app.py` | optional secondary Streamlit evidence viewers |

The Streamlit files are secondary inspection tools only. They are not the canonical product entry point.

## Deployment contract

The canonical container runs the same FastAPI + `public/` application used by the judge flow:

```bash
docker build -t mandateguard .
docker run --rm -p 8765:8765 mandateguard
```

Local source run:

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

Serverless routing is described by `vercel.json`. Static replay can be served directly from `public/`, but must remain labelled recorded evidence.

## Production boundary

The submission is not a merchant-production payment service.

Production deployment requires:

- durable event/state/idempotency storage;
- transactional worker claims and crash recovery;
- merchant authentication and tenant isolation;
- managed secrets and approved provider capabilities;
- durable retry scheduling/cancellation;
- cross-process reconciliation for provider races;
- evidence retention, anchoring and access controls;
- production observability/rate limiting;
- permissioned real-failure labels and economic validation;
- model calibration, cost and latency validation if a live interpreter is used.

Fresh provider reads reduce but do not eliminate write/read races. Process-local locks are not distributed exactly-once execution. The project taxonomy and unpinned rules remain project policy unless backed by recorded external provenance.
