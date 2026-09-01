# Submission Readiness — evidence, not optimism

This file is the current submission-status source of truth. A capability is marked **VERIFIED** only when the repository contains an executable check or previously recorded acceptance evidence that supports it. A capability is **IMPLEMENTED / LIVE RUN REQUIRED** when the code path exists but a real Razorpay Test Mode credentialed run has not yet been captured. Anything else is **NOT CLAIMED**.

## MandateGuard offline benchmark baseline

**Status: VERIFIED BASELINE, PRE-RECOVERYTRUTH BUILD**

The existing `FINAL_VERIFICATION.md` records the acceptance run for the hardened offline MandateGuard package: 283 tests, 14/14 mutation checks, adversarial and webhook-ingress attacks, release gate, clean-package verification and checksum verification.

That record remains evidence for the **offline benchmark baseline it names**. It must not be misread as verification of files added after that acceptance run. The final submission package requires a fresh verification record and a regenerated checksum manifest after RecoveryTruth hardening is frozen.

## RecoveryTruth implementation matrix

| Capability | Status | Evidence / boundary |
|---|---|---|
| Fresh current financial truth states | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | `bailiff/recovery_truth.py`, `scripts/recoverytruth_check.py` |
| Stale event loses to fresh captured state | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | historical evidence is non-authoritative; current captured state resolves `PAID` |
| In-flight payment blocks parallel collection | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | `created`, `authorized`, `pending` => `IN_FLIGHT` |
| Exact Razorpay Order binding | IMPLEMENTED / LIVE RUN REQUIRED | Test Mode client fetches exact Order and validates amount/currency |
| Exact Order-payment identity binding | IMPLEMENTED / LIVE RUN REQUIRED | `/orders/:id/payments`; every payment must carry exact order id, amount, currency |
| Razorpay Order `paid` as independent stop signal | IMPLEMENTED / LIVE RUN REQUIRED | current Order state participates in truth resolution |
| Immediate pre-write provider reread | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | two evidence reads are asserted before one provider write |
| State-change SAFE_BLOCK | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | captured/in-flight TOCTOU attacks make zero writes |
| Expiring decision authority | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | decision hash/action/amount/expiry bound and rechecked at write |
| Live credentials refused | IMPLEMENTED + OFFLINE ACCEPTANCE GATED | any non-`rzp_test_` key raises |
| Real Test Mode Payment Link fallback | IMPLEMENTED / LIVE RUN REQUIRED | `scripts/razorpay_testmode_demo.py execute` |
| Ambiguous network-write reconciliation | IMPLEMENTED / LIVE RUN REQUIRED | timeout/network failure => lookup by deterministic reference |
| Concurrent duplicate-reference reconciliation | IMPLEMENTED / LIVE RUN REQUIRED | documented Razorpay duplicate-reference 400/409 => lookup/reuse |
| Captured-payment postcondition | IMPLEMENTED / LIVE RUN REQUIRED | Payment Link + independent Payment fetch; exact captured/amount/currency/reference |
| RecoveryProof | IMPLEMENTED + OFFLINE ACCEPTANCE GATED; REAL EVIDENCE REQUIRED | binds decision, pre-write evidence, provider action and postcondition hashes |
| Full production AutoPay retry through Razorpay | NOT CLAIMED | real provider action is a customer-initiated fallback Payment Link, not a mandate debit retry |
| Statistically calibrated abstention | NOT CLAIMED | B3 is confidence-gated; no ECE/Brier calibration claim |
| Full authenticated human approval console | NOT CLAIMED | review routing/queue exists; approval-to-write workflow is not claimed |
| Production/live money execution | NOT CLAIMED | Test Mode client rejects live credentials |

## Submission release blockers

The project must **not** be labelled 100% submission-verified until all items below are closed.

1. Run the complete repository verification after the RecoveryTruth code is frozen:
   - compileall,
   - legacy full pytest suite,
   - mutation check,
   - `scripts/recoverytruth_check.py`,
   - release gate,
   - fixture sensitivity sweep.
2. Execute at least one credentialed Razorpay **Test Mode** provider path using an exact Test Mode Order with failed payment evidence.
3. Capture one successful fallback receipt, complete it in Test Mode, and run the independent verification step to produce a real `RecoveryProof`.
4. Capture at least one real Test Mode `SAFE_BLOCK` case where the current Order/Payment state prevents a new fallback. Prefer an already-paid or in-flight case.
5. Replace/regenerate the final checksum manifest after all submission files are frozen.
6. Replace or supersede the old `FINAL_VERIFICATION.md` with a fresh final acceptance record that clearly separates:
   - synthetic/offline benchmark evidence,
   - real Razorpay Test Mode evidence.
7. Ensure judge-facing wording never converts:
   - synthetic rupees into production recovery,
   - standard Payment Link fallback into AutoPay retry,
   - confidence threshold into statistical calibration,
   - hash evidence into “tamper-proof”.

## What is already structurally closed

The following architectural loopholes have been deliberately addressed in the hardening path:

- stale webhook/event evidence cannot outrank a fresh captured provider fact;
- a pending/authorized payment cannot be treated as safe for parallel collection;
- a write fence cannot arm from an unknown/non-recoverable state;
- provider state is re-read immediately before the write;
- order id, amount and currency are bound to the decision;
- policy authority cannot widen its amount or action;
- policy authority expires and is checked at the write boundary;
- caller-provided mandate status is not mislabeled as provider truth;
- the customer-initiated fallback is explicitly different from an AutoPay retry;
- a timeout is not permission to blindly create again;
- a duplicate-reference race is reconciled using the same deterministic provider reference;
- “link paid” alone is not treated as proof; the exact Payment is independently fetched and must be captured;
- the postcondition hash is built from raw provider responses before derived local binding fields are added;
- a verify command cannot invent a missing pre-write evidence hash; it requires the exact execution receipt.

## Current honest submission sentence

Until the credentialed provider run and final package verification are captured, the strongest accurate wording is:

> MandateGuard is a verified offline policy-evaluation and bounded-authority runtime. RecoveryTruth adds a release-gated financial-truth and write-fencing protocol plus a Razorpay Test Mode provider adapter for a customer-initiated Payment Link fallback. The Test Mode execution code is implemented; final credentialed provider evidence is still required before claiming the end-to-end provider path as verified.
