# MandateGuard — submission pack

**Official track: 03 — AI Revenue Recovery**

## Project name and one-line pitch

**MandateGuard: recover failed subscriptions, prove every action.**

A bounded UPI AutoPay recovery workflow that diagnoses failures, executes permitted recovery, escalates uncertainty, and gives every action or refusal a verifiable receipt.

## Submission description

Failed subscription payments need different next steps. A temporary failure may be recoverable; a cancelled mandate must stop; an uncertain bank response needs review.

MandateGuard processes a batch of scheduled UPI AutoPay failures through diagnosis, deterministic authorization, a local provider simulator and postcondition verification. The dashboard shows recovered value, stopped cases, human review and the actual provider calls. Every case has downloadable evidence, and the browser can verify its audit chain and demonstrate tamper detection.

AI is used only for ambiguous failure interpretation. It can return a label and confidence but cannot authorize a debit or call the provider. The repeatable default uses a deterministic interpreter; a captured optional real-model run is included.

Nine executable policies consume the same frozen outcomes. The evaluation reports both simulated recovery and the costs of excessive intervention or excessive refusal. A price sweep exposes when the preferred policy changes.

Separately, RecoveryTruth demonstrates a captured Razorpay Test Mode Standard Payment Link fallback, an independently verified captured payment, and an already-paid refusal with zero new fallback writes. A Payment Link is not an AutoPay retry. No production recovery or regulatory approval is claimed.

Razorpay already offers Intelligent Revenue-Protect and Subscription Recovery. The proposed contribution is a narrow, auditable recovery workflow and a policy evaluation surface that could support recovery configuration.

## Deliverables

| Item | Artifact |
|---|---|
| Working product | `python -m uvicorn api.index:app --port 8765` |
| Public static evidence | [Pages](https://akshu1245.github.io/razropay/) — must be updated with this revision |
| Source repository | [GitHub](https://github.com/Akshu1245/razropay) — must contain this revision |
| Five-minute video | Record using [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md); supply its accessible URL in the form |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Generated results | [README metrics](README.md#measured-recovery), [report](outputs/report.md), [price sweep](outputs/sensitivity.json) |
| Verification | [FINAL_VERIFICATION.md](FINAL_VERIFICATION.md) |

## Track fit

The [official brief](https://razorpay.com/buildathon/) asks for a complete recovery workflow and batch evidence, with escalation, stopping rules and an audit trail.

| Requirement | What to show |
|---|---|
| Detect revenue at risk | Failure batch and case amounts |
| Diagnose and intervene | Failure lab and case reasons |
| Execute bounded recovery | Run batch; inspect a recovered case and provider postcondition |
| Measure recovery across a batch | Generated dashboard totals; export receipts |
| Handle exceptions | Human-review filter, forged webhook, revoked mandate, timeout |
| Show an audit trail | Receipt verification in the browser |
| Provider integration | Captured Test Mode fallback and capture proof, clearly separated from simulation |

## Panel answers

**Why another recovery agent?** Razorpay already has recovery. This prototype makes a narrow workflow inspectable and tests candidate policies before rollout. It does not claim an absent capability in Razorpay's internal systems.

**Where is the AI?** Ambiguous diagnosis only. Deterministic rules retain execution authority. The UI labels offline interpretation honestly.

**Did you recover real money?** The batch amounts are simulated. The separate saved Test Mode example verifies a captured payment; Test Mode is not merchant revenue.

**Why does the guarded arm recover less?** Controls block some latent recoverable cases. The forgone-recovery metric and price sweep expose this cost rather than hiding it.

**Is RZP a competitor benchmark?** It is a fixed card-schedule reference applied under a stated assumption, not Razorpay's UPI engine.

**What is missing for production?** Durable state, merchant authentication, provider-side atomicity or reconciliation guarantees, an approved AutoPay execution integration, and validation on permissioned merchant data.

## Final owner actions

Publish this revision, check the public links in a signed-out browser, record and upload the five-minute video, and submit the form. An unrecorded script is not a submitted video. Do not mark these complete until performed.
