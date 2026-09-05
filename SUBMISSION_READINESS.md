# Submission readiness

Status for the judge-experience revision on 5 September 2026.

## Implemented in this revision

- Rebuilt the primary `public/` experience around one **Run recovery demonstration** action instead of four competing top-level screens.
- Put the three decisive cases directly in the judge path: eligible recovery, revoked mandate with zero provider calls, and provider timeout with unknown outcome routed to human review.
- Added a readable five-step case timeline: failure → diagnosis → control checks → action → outcome.
- Put simulated revenue recovered, payments recovered, stopped cases, human review and recoverable value forgone in one batch summary.
- Kept technical receipts, browser audit verification, exports and tamper detection available on demand.
- Moved opt-out, missing notice, ambiguous interpretation and forged webhook into a secondary boundary panel.
- Moved all nine canonical policy arms and the complete price sweep into an expandable advanced evaluation section without removing any evidence.
- Kept the Razorpay Test Mode proof visibly separate from the synthetic batch.
- Aligned the submission copy, judge runbook and canonical five-minute video script with the final product story.

## Engineering boundary unchanged

This revision does not change the recovery engine, canonical policy arms, frozen benchmark protocol, guardrails, provider simulator, RecoveryTruth execution logic, or financial metric definitions. The judge-facing web application continues to call the shared `bailiff/showcase.py` engine endpoints when Python is connected and truthfully labels static hosting as recorded evidence replay.

The required claim remains:

> AI interprets unclear failure information; deterministic controls decide whether an action is allowed.

The bounded interpreter still has no provider tools and cannot authorize money movement.

## Verification and follow-up status

The merged judge-experience revision `28bc8e35606057a9ea47efaf5010c1f689c763f3` passed [clean-checkout CI](https://github.com/Akshu1245/razropay/actions/runs/33944266970): 308 tests and all 14 mutation checks. The [browser verification run](https://github.com/Akshu1245/razropay/actions/runs/33943893074) passed required test, demo and evaluation scripts, desktop/mobile flows, downloads and receipt tamper checks; its tested source tree was identical to that merge.

The follow-up adds the missing awaiting-outcome count, an explicit B2/B3 offline-interpreter comparison, an accurate interpretation-score label, and a fix for changing the selected boundary case while an earlier response is pending. The extended browser acceptance script verifies that delayed responses cannot overwrite another case. See the latest CI run for verification of this follow-up; earlier results are not a substitute.

## Publication and owner actions

Code is in the Akshu1245/razropay repository. At the latest check on 5 September 2026 it remained private, and GitHub Pages was not enabled. Public access and deployment are deferred at the owner's request. Local verification does not establish a public demo.

The owner still needs to record and upload the five-minute video, confirm judge access to the repository/demo, and submit the application. Repository visibility must not be changed without owner approval.

## Production limits remain

Batch recovery is synthetic. The saved provider proof is Razorpay Test Mode, not a production AutoPay batch. Production merchant traffic would still require durable state and scheduling, merchant authentication and tenant isolation, secret management, approved provider capabilities, cross-process reconciliation, evidence retention controls, and validation on permissioned real failures. See `MARKET_READY_ARCHITECTURE.md`.

No guarantee of selection, production readiness, regulatory certification, production AI accuracy, or superiority over untested systems is supported.
