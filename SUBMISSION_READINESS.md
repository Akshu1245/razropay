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

## Verification status

The previously recorded **308-test / 14-mutation** result in `FINAL_VERIFICATION.md` is historical evidence for the handoff revision, not proof that this new UI revision passes.

The judge-experience branch must earn its own clean-checkout verification before submission. Record the exact current results for:

- `scripts/test.sh`
- `scripts/demo.sh`
- `scripts/evaluate.sh`
- browser flow at desktop and 390-pixel mobile width
- the three primary cases
- receipt verification and tamper detection
- export behavior
- JavaScript syntax and browser errors
- manifest/checksum integrity

Do not rewrite the historical verification record as if those checks have already passed.

## Publication status at handoff to this revision

- Repository visibility was still **private** when this work began.
- `main` was still at handoff commit `1f3a1b1175bc633cbf40181e3c5ccca9c8f84a6f` before the judge-experience branch was created.
- The existing GitHub Pages deployment for that handoff commit had failed; local correctness did not establish a public demo.
- Repository visibility must not be changed without owner approval.

## Production limits remain

Batch recovery is synthetic. The saved provider proof is Razorpay Test Mode, not a production AutoPay batch. Production merchant traffic would still require durable state and scheduling, merchant authentication and tenant isolation, secret management, approved provider capabilities, cross-process reconciliation, evidence retention controls, and validation on permissioned real failures. See `MARKET_READY_ARCHITECTURE.md`.

No guarantee of selection, production readiness, regulatory certification, production AI accuracy, or superiority over untested systems is supported.
