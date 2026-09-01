# Submission Readiness — evidence, not optimism

This file is the current submission-status source of truth. **VERIFIED** means the repository has an executable check or recorded CI evidence for the claim. **IMPLEMENTED / TEST MODE RUN REQUIRED** means the path exists but the credentialed Razorpay Test Mode proof has not yet been captured. Anything else is **NOT CLAIMED**.

## Current status

**Offline submission path: VERIFIED AND GREEN.**

The frozen RecoveryTruth hardening head completed the full clean GitHub Actions path successfully: install, checksum candidate, 283-test suite, RecoveryTruth acceptance, offline demo, deep non-mutating verification, README/report integrity and evidence upload. The original offline verification record still describes the synthetic benchmark baseline, while the final post-Test-Mode verification record will supersede it for the complete submission.

**Credentialed provider path: IMPLEMENTED / TEST MODE RUN REQUIRED.**

The code is ready for Razorpay Test Mode only. The remaining external-account evidence is one successful fallback receipt, one real `SAFE_BLOCK_ALREADY_PAID` or `SAFE_BLOCK_IN_FLIGHT`, and one captured-payment `RecoveryProof`.

## RecoveryTruth implementation matrix

| Capability | Status | Evidence / boundary |
|---|---|---|
| Fresh current financial truth states | VERIFIED OFFLINE | `bailiff/recovery_truth.py`, `scripts/recoverytruth_check.py` |
| Stale event loses to fresh captured state | VERIFIED OFFLINE | historical evidence is non-authoritative; current captured state resolves `PAID` |
| In-flight payment blocks parallel collection | VERIFIED OFFLINE | `created`, `authorized`, `pending` => `IN_FLIGHT` |
| Exact Razorpay Order binding | IMPLEMENTED / TEST MODE RUN REQUIRED | exact Order id, amount and currency validation |
| Exact Order-payment identity binding | IMPLEMENTED / TEST MODE RUN REQUIRED | every payment must bind to exact order id, amount and currency |
| Razorpay Order `paid` as independent stop signal | IMPLEMENTED / TEST MODE RUN REQUIRED | current Order state participates in truth resolution |
| Immediate pre-write provider reread | VERIFIED OFFLINE | two evidence reads before one write |
| State-change SAFE_BLOCK | VERIFIED OFFLINE | captured/in-flight TOCTOU attacks make zero writes |
| Expiring decision authority | VERIFIED OFFLINE | decision hash/action/amount/expiry bound and rechecked at write |
| Live credentials refused | VERIFIED OFFLINE | any non-`rzp_test_` key raises |
| Standard Payment Link fallback | IMPLEMENTED / TEST MODE RUN REQUIRED | `scripts/razorpay_testmode_demo.py execute` |
| Ambiguous write reconciliation | VERIFIED OFFLINE CONTRACT / TEST MODE EVIDENCE REQUIRED | timeout/network ambiguity reconciles by deterministic reference |
| Duplicate-reference reconciliation | VERIFIED OFFLINE CONTRACT / TEST MODE EVIDENCE REQUIRED | duplicate provider reference is looked up/reused |
| Captured-payment postcondition | IMPLEMENTED / TEST MODE RUN REQUIRED | Payment Link + independent Payment fetch; exact captured/amount/currency/reference |
| RecoveryProof | VERIFIED OFFLINE CONTRACT / REAL EVIDENCE REQUIRED | binds decision, original order, mandate, authority, provider action and exact captured payment |
| Production AutoPay debit retry | NOT CLAIMED | fallback is a customer-initiated Standard Payment Link, not mandate debit execution |
| Production/live money execution | NOT CLAIMED | live keys are intentionally refused |

## Remaining submission blockers

Only credential-bound/final-evidence work remains:

1. Run one Razorpay **Test Mode** recoverable case and preserve the fallback receipt.
2. Complete the hosted Test Mode payment and generate the independent `RecoveryProof`.
3. Capture one real Test Mode already-paid or in-flight `SAFE_BLOCK` with zero fallback write.
4. Redact and preserve those Test Mode artifacts without secrets or customer PII.
5. Regenerate `SHA256SUMS.txt` after those final artifacts and the final verification record exist.
6. Replace/supersede the old `FINAL_VERIFICATION.md` with the final record separating offline synthetic evidence from real Test Mode evidence.

## Frozen safety boundary

Do not change the canonical policy arms, `guardrails.py`, webhook HMAC boundary, RecoveryTruth state resolver/write fence, or the frozen benchmark merely to improve a score. Any required safety-code change invalidates the freeze and requires a new full verification run.

OpenEvolve experimentation is isolated from the submission safety boundary and must not modify guardrails, webhook authentication, RecoveryTruth fences or provider execution.

## Judge-facing wording

Use this meaning until the credentialed provider evidence exists:

> **Razorpay already recovers. MandateGuard is the harness in front of that engine: before a retry configuration goes live, prove what it recovers, what it refuses, and that every refusal made zero provider calls.**

Keep these limits explicit: benchmark rupees are synthetic counterfactuals; the Test Mode Standard Payment Link is not an AutoPay retry; `RZP` is not Intelligent Retry; the hash chain is tamper-evident evidence, not tamper-proof storage.

## Current submission status

- Offline proof: **GREEN / FROZEN**
- RecoveryTruth offline acceptance: **GREEN**
- Checksum manifest before Test Mode artifacts: **MAINTAINED**
- Test Mode fallback receipt: **PENDING USER TEST KEYS**
- Test Mode SAFE_BLOCK: **PENDING USER TEST KEYS**
- Real RecoveryProof: **PENDING USER TEST KEYS + HOSTED TEST PAYMENT**
- Final post-Test-Mode checksum freeze: **PENDING FINAL ARTIFACTS**
- Final `FINAL_VERIFICATION.md`: **PENDING FINAL ARTIFACTS**

**Everything that can be completed without Razorpay Test Mode credentials is ready; the repository must not yet claim the credentialed provider proof as completed.**
