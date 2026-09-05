# Judge Runbook

## Fast path — understand MandateGuard in under three minutes

Python 3.11+:

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. The header should say **Python engine connected**.

1. Click **Run recovery demonstration**.
2. Read the three case cards:
   - **Retry is permitted** — eligible failure, one bounded provider action.
   - **Stop before the provider** — revoked mandate, zero provider calls.
   - **Ask a human before another action** — attempted call, unknown postcondition, no blind repeat.
3. Open the eligible receipt and click **Verify audit chain + tamper check**.
4. Read the batch summary, especially recovery **and recoverable value forgone**.
5. Read the AI boundary.
6. Inspect the separate Razorpay Test Mode evidence.
7. Expand **Advanced policy evaluation** only if you want all nine arms and the complete price sweep.

The batch INR is synthetic. The Razorpay proof is saved Test Mode evidence. A Standard Payment Link fallback is not an AutoPay retry, and creating a link is not proof of captured payment.

## What the primary action executes

`public/` is the canonical product. `api/index.py` serves it and exposes bounded demo endpoints that call `bailiff/showcase.py`.

The primary demonstration executes:

- a fixed 100-case synthetic batch;
- the eligible recoverable scenario;
- the revoked-mandate scenario;
- the unknown-timeout scenario.

The API does not load provider credentials or call a real payment provider. Static hosting cannot execute Python; in static mode the header says **Recorded engine evidence** and the action replays `public/evidence.json`.

## Four proofs worth opening

### 1. Zero-call denial

Open the revoked-mandate case. A safe denial requires `provider_calls = 0`.

### 2. Unknown write outcome

Open the timeout case. One action was attempted, but the postcondition is unknown. The case is held for human review before another automated action.

### 3. Receipt tamper check

Open the eligible receipt and run browser verification. The shipped chain verifies; editing an earlier decision breaks verification. The chain is tamper-evident, not immutable.

### 4. Razorpay Test Mode capture

The provider section is saved read-only evidence separate from the synthetic batch. It contains a Test Mode Standard Payment Link fallback, independent captured-payment verification, and an already-paid zero-write case.

## AI explanation

Use this exact sentence:

> **AI interprets unclear failure information; deterministic controls decide whether an action is allowed.**

B3 has no provider tools. The interpreter can normalize ambiguous failure information and confidence; it cannot authorize payment action, widen authority, restore a mandate or bypass deterministic controls. Low-confidence output abstains before the provider.

The repeatable benchmark uses an offline deterministic interpreter. Optional saved real-model evidence proves integration, not production accuracy or measured uplift.

## Reproduce

Required:

```bash
./scripts/test.sh
./scripts/demo.sh
./scripts/evaluate.sh
```

Full evidence verification:

```bash
./scripts/verify_all.sh
python scripts/recoverytruth_check.py
python scripts/security_regression_check.py
python scripts/hardening_check.py
python scripts/interpreter_ablation.py
python scripts/refusal_regret.py
```

Container smoke path:

```bash
docker build -t mandateguard .
docker run --rm -p 8765:8765 mandateguard
```

## Evidence map

- `SUBMISSION_READINESS.md` — canonical final submission report and verification matrix.
- `ARCHITECTURE.md` — authority, execution, evaluation and production boundaries.
- `outputs/report.md` — generated benchmark appendix.
- `outputs/sensitivity.json` — complete price sweep.
- `ROBUSTNESS.md` — fixture-assumption sensitivity.
- `RECOVERYTRUTH.md` — Razorpay Test Mode provider-proof boundary.
- `docs/competitive_position.md` — public competitive research and caveats.
- `docs/problem_evidence.md` — problem-evidence sampling and limitations.
- `docs/panel_qa.md` — short technical answers.
- `VIDEO_SCRIPT.md` — canonical five-minute pitch.

## Do not claim

Do not claim production revenue, production readiness, regulatory certification, a production AutoPay retry integration, a universal winning policy, equivalence to Razorpay's production retry engine, immutable evidence, or measured AI uplift that the artifacts do not support.
