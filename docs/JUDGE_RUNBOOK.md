# Judge runbook

## Fast path: understand MandateGuard in under three minutes

Python 3.11 or newer:

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. The header should say **Python engine connected**.

1. Click **Run recovery demonstration**.
2. Read the three decision cards:
   - **Retry is permitted** — eligible recoverable failure, one permitted provider action and a receipt.
   - **Stop before the provider** — revoked mandate, zero provider calls.
   - **Ask a human before another action** — provider timeout, one attempted call with unknown outcome, then human review.
3. Open the eligible case receipt and click **Verify audit chain + tamper check**.
4. Read the batch summary. It includes simulated revenue recovered, payments recovered, stopped cases, human review and **recoverable value forgone**.
5. Read the **AI boundary** and the separate **Razorpay Test Mode evidence**.
6. Expand **Advanced policy evaluation** only if you want the nine-arm benchmark and complete swept price curve.

The batch INR is synthetic. The Razorpay proof is saved Test Mode evidence. A Standard Payment Link fallback is not an AutoPay retry, and creating a link is not proof of captured payment.

## What the primary action executes

`public/` is the judge-facing product. `api/index.py` serves it and exposes bounded demo endpoints. Those endpoints call `bailiff/showcase.py`, which uses the shared engine rather than a presentation-only mock.

The main demonstration executes:

- the fixed 100-case batch across all nine canonical arms on one frozen outcome ledger;
- the eligible recoverable scenario;
- the revoked-mandate scenario; and
- the unknown-timeout scenario.

Static hosting cannot execute Python. In that mode the header says **Recorded engine evidence**, and the primary action replays `public/evidence.json` rather than pretending to run live code.

## Evidence checks

### Decision receipt

A permitted provider action includes idempotency data, a provider-call identifier, postcondition and audit events. Denied or abstained paths show zero provider calls. The browser verification recomputes the shipped hash chain and confirms that an edited decision fails verification.

### Unknown timeout

The timeout case is intentionally different from a denial. One provider action was attempted; the postcondition is unknown. The case is held in human review and cannot be followed by another automated action until resolved.

### AI boundary

Use this exact explanation:

> AI interprets unclear failure information; deterministic controls decide whether an action is allowed.

B3 has no provider tools and cannot authorize money movement. The deterministic guardrails remain the execution authority. The repeatable default interpreter is offline and deterministic. Optional saved real-model evidence does not establish production accuracy or uplift.

### Razorpay Test Mode proof

The provider section is read-only saved evidence, separate from the synthetic batch. It contains:

- a Test Mode Standard Payment Link fallback;
- independently verified captured-payment evidence bound to that recovery case; and
- an already-paid zero-write case.

## Advanced reproducibility

Required submission commands from a clean checkout:

```bash
./scripts/test.sh
./scripts/demo.sh
./scripts/evaluate.sh
```

Deeper evidence checks:

```bash
./scripts/verify_all.sh
python scripts/recoverytruth_check.py
python scripts/security_regression_check.py
python scripts/interpreter_ablation.py
python scripts/refusal_regret.py
```

Important artifacts:

- `FINAL_VERIFICATION.md` — observed verification record.
- `outputs/report.md` — generated benchmark report.
- `outputs/sensitivity.json` — complete price sweep.
- `ROBUSTNESS.md` — fixture-assumption sensitivity.
- `ARCHITECTURE.md` — authority and evidence boundaries.
- `MARKET_READY_ARCHITECTURE.md` — explicit production gaps.
- `VIDEO_SCRIPT.md` — canonical five-minute narration.

## What not to claim

Do not claim production revenue, production readiness, regulatory certification, a production AutoPay retry integration, a universal winning policy, Razorpay production-engine equivalence, tamper-proof storage, or measured AI uplift that is not supported by the artifacts.
