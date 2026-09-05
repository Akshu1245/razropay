# MandateGuard — submission pack

**Official track:** 03 — AI Revenue Recovery

## Product promise

**MandateGuard helps merchants recover failed scheduled UPI AutoPay payments, with explicit controls for when to retry, when to stop, and when to ask a human—with evidence for every decision.**

## Submission description

A failed scheduled UPI AutoPay payment does not always deserve another retry. A temporary failure may be recoverable, a revoked mandate must stop, and an unknown provider timeout must wait for human review before another automated action.

MandateGuard makes that decision flow visible. The judge-facing workspace opens with one recovery demonstration and three concrete cases: an eligible recoverable failure, a revoked mandate, and a provider timeout with an unknown outcome. Each case shows what failed, the diagnosis, the control checks, the action actually taken, the provider-call count, the postcondition, and an inspectable audit receipt.

The batch demonstration executes 100 synthetic scheduled AutoPay failures against one frozen outcome ledger. It reports simulated INR recovered, payments recovered, cases stopped, cases requiring review, and legitimate recoverable value forgone. Financial metrics depend on actual provider calls and observed simulator postconditions, not a predicted recovery score.

**AI interprets unclear failure information; deterministic controls decide whether an action is allowed.** B3 may return a bounded interpretation and confidence, but it has no provider tools and cannot authorize money movement. Low-confidence interpretation abstains. The default repeatable demo uses the deterministic offline interpreter; captured optional real-model evidence is labeled separately and is not presented as proof of production uplift.

Advanced evaluation remains available without dominating the product story. All nine canonical arms consume the same frozen outcomes, and the complete swept price curve is shown beside any preferred arm. There is no universal winning policy: more recovery can also execute prohibited value, while stronger controls can forgo legitimate recovery.

Separately, RecoveryTruth contains saved Razorpay Test Mode evidence for a Standard Payment Link fallback, independent captured-payment verification, and an already-paid zero-write case. A Payment Link is not an AutoPay retry, and creating a link is not proof of recovered money.

No production merchant recovery, regulatory certification, production model accuracy, or superiority over Razorpay's production recovery systems is claimed.

## What judges should do first

1. Start the local Python-backed workspace and click **Run recovery demonstration**.
2. Read the three decision cards: **Retry is permitted**, **Stop before the provider**, and **Ask a human before another action**.
3. Open a decision receipt and click **Verify audit chain + tamper check**.
4. Inspect the batch summary, including **Recoverable value forgone**.
5. Review the separate **Razorpay Test Mode evidence**.
6. Expand **Advanced policy evaluation** only after the core workflow is clear.

## Deliverables

| Item | Artifact |
|---|---|
| Working product | `python -m uvicorn api.index:app --host 127.0.0.1 --port 8765` |
| Source repository | `https://github.com/Akshu1245/razropay` |
| Static evidence replay | `https://akshu1245.github.io/razropay/` — use only after deployment is confirmed |
| Judge runbook | `docs/JUDGE_RUNBOOK.md` |
| Five-minute video script | `VIDEO_SCRIPT.md` |
| Architecture | `ARCHITECTURE.md` |
| Generated evaluation | `outputs/report.md`, `outputs/sensitivity.json`, `ROBUSTNESS.md` |
| Verification record | `FINAL_VERIFICATION.md` |

## Track fit

| Track need | MandateGuard evidence |
|---|---|
| Detect revenue at risk | 100-case scheduled UPI AutoPay failure batch |
| Diagnose the failure | Normalized reason plus bounded interpretation for ambiguity |
| Decide the next step | Deterministic mandate, consent, notice, retry and authority controls |
| Execute bounded recovery | Provider simulator call with idempotency, call identifier and postcondition |
| Handle exceptions | Revoked mandate, opt-out, missing notice, ambiguity, forged webhook and unknown timeout |
| Measure batch recovery | Provider-call-defined recovery metrics plus forgone recovery |
| Prove decisions | Per-case audit receipts, browser hash verification and tamper detection |
| Show provider integration | Separate captured Razorpay Test Mode fallback and capture proof |

## Panel answers

**Where is the AI?** It interprets ambiguous failure information only. Deterministic controls retain execution authority.

**Did the batch recover real merchant money?** No. Batch INR is synthetic. The provider proof is a separate Razorpay Test Mode example.

**Why show recoverable value forgone?** Because controls can prevent legitimate recovery as well as prevent prohibited actions. Hiding that cost would make the comparison misleading.

**Why does the timeout go to a human after one provider call?** The call happened but the outcome is unknown. Another automated action could duplicate payment, so the state is held for review.

**Is the RZP arm Razorpay's UPI engine?** No. It is a fixed temporal reference derived from a published card schedule and is explicitly labeled as an assumption.

**What is still required for production?** Durable state and scheduling, merchant authentication and tenant isolation, approved provider execution, secret management, cross-process reconciliation, evidence retention controls, and validation on permissioned merchant failures.

## Owner actions still required

- Decide when the reviewed branch should become the submission branch.
- Confirm repository visibility required by the submission form; do not change it accidentally.
- Confirm the hosted demo actually deploys and opens in a signed-out browser before putting that URL in the form.
- Record and upload the five-minute video using `VIDEO_SCRIPT.md`.
- Submit the application form.
