# OpenEvolve REFUSAL_REPORT

Honest negative / not-run result. No live evolution was performed on this PR. No evolved winner was merged into the Track 1 safety kernel.

## Scope

Isolated **EVOLVE-BLOCK** only: B2 policy selection / retry *reasoning* in `experiments/openevolve/initial_program.py` between `EVOLVE-BLOCK-START` and `EVOLVE-BLOCK-END`.

The candidate may propose `SCHEDULE_RETRY`, `STOP_RECOVERY`, or `ESCALATE_TO_HUMAN`. It does not authorize or execute a payment. `experiments/openevolve/evaluator.py` still runs every B2 proposal through the frozen `GuardrailEngine` on the frozen MandateGuard ledger. Candidates that touch protected surfaces, record a violation, perform prohibited execution, or leave an incomplete audit receive zero fitness.

**Track 1 freeze is untouched.** This branch was created from `main` at `42e844b8dad79cce3087eda23974621635f0e319` (frozen safety kernel). The isolated experiment tree was copied from `openevolve-experiment@ab34e8a0b6f9874463c4f6eb850d1f3ea35a26a0`. That older branch forked from `290dbfeb` *before* Final security hardening + Freeze submission safety; it is not the PR base and was not merged into `main`.

Copied surface (isolated):

- `experiments/openevolve/README.md` (runbook)
- `experiments/openevolve/CLAUDE_INKLING_HELPER.md`
- `experiments/openevolve/config_groq.yaml`
- `experiments/openevolve/config_gemini.yaml`
- `experiments/openevolve/evaluator.py`
- `experiments/openevolve/initial_program.py`

Not copied from the old experiment branch (stale or kernel-adjacent):

- root `README.md` (stale vs frozen main)
- `SHA256SUMS.txt` (stale; the old branch rewrote the whole manifest)
- `FINAL_VERIFICATION.md`, `pyproject.toml`, `requirements.txt`, `app.py`
- anything under `bailiff/` or `outputs/`

`scripts/make_checksum_manifest.py` on main walks the entire tree and regenerates every hash. Mutating `SHA256SUMS.txt` here would rewrite frozen-output hashes as a side effect. **Checksums for the new experiment files are left for A1/A2 to regenerate** rather than rewriting the frozen manifest on this PR.

## Live evolve

**NO.** Environment was checked once. `GROQ_API_KEY`, `GEMINI_API_KEY`, and `GOOGLE_API_KEY` were absent. No Groq/Gemini call was made. No OpenEvolve loop was started. No generations were run. This PR does not invent an AI win, fitness scores, or generation logs.

The old `experiments/openevolve/` tree on `openevolve-experiment@ab34e8a0` contains only the six source/config/runbook files listed above. There is no `output-groq/`, `output-gemini/`, checkpoint, best-program dump, or scored candidate artifact.

## Comparison table

Every rupee below is a **synthetic counterfactual** from the frozen offline ledger. It is not production revenue, merchant collections, or Razorpay performance.

Re-read on `main` `outputs/manifest.json` (SHA `cd0d755b2b2ba4d1ff3c36930f0ab9b4aeebdd0a`):

- dataset hash: `725a38d6ffdcadf0ea33fdb81d94b7fa9e7f11de296b86a42188f6153dbed0f7`
- rules hash: `70e2909d26598695f74ae9e4d5c81dabb4c772d1f6d376d6567923cdc8a52506`

Those hashes still match `FINDINGS.md` on main.

### a) Handwritten baseline (frozen B0..B3)

Canonical arm order from `AGENTS.md`: B0, B1, B1.5, RZP, B2.25, B2.5, B2.75, B2, B3.

| Arm | Role (AGENTS.md / README) | FINDINGS.md / frozen ledger (synthetic INR) |
|---|---|---|
| B0 | No intervention; stops without attempting recovery | Incremental recovery is the zero control. Not a recommended arm. |
| B1 | Ungated retry; no reason gate, no guardrails | Realized harm (synthetic): R1 ₹32,806.05; R2 ₹53,037.05; R3 ₹36,801.25 (`FINDINGS.md`). |
| B1.5 | Deterministic retry on transient reasons only | Recommended arm under **flat** per-breach cost in all three regimes (`FINDINGS.md`). |
| B2 | Full deterministic guardrail profile; B2 proposed-action is the OpenEvolve surface | Incremental recovery (synthetic): R1 ₹6,386.15; R2 ₹2,536.15; R3 ₹3,016.20. Realized harm ₹0.00 in all three regimes. |
| B3 | Bounded interpreter on ambiguous payloads; no provider tools | Harm-priced recommended arm on R1 and R3; B1.5 remains recommended on R2 at 1.50× harm. Abstention: R1 0.0240; R2 0.0250; R3 0.1205. Interpreter influence: R1 9.00; R2 8.90; R3 29.10. Realized harm ₹0.00 (B2/B3 retain the full guardrail profile). |

B2 versus B1 break-even violation cost (synthetic, `FINDINGS.md`): R1 ₹72.81; R2 ₹30.65; R3 ₹29.93.

OpenEvolve is allowed to mutate only B2 `choose_action` reasoning. It must not replace B0..B3, `bailiff/policies.py`, or guardrails.

### b) Best SAFE evolved candidate

**None.** No live run on this PR. The old `experiments/` tree contains **no** logged candidate with scores. There is therefore nothing to cite as a historical safe winner from `openevolve-experiment@ab34e8a0`. The initial EVOLVE-BLOCK program is a handwritten starting policy (retry `INSUFFICIENT_FUNDS` / `BANK_TIMEOUT_OR_TEMPORARY_FAILURE`; escalate `RISK_OR_FRAUD_REJECTED` / `UNKNOWN_OR_CONFLICTING`; otherwise stop). It was **not re-run** and is **not merged** into `bailiff/`.

### c) Best UNSAFE high-recovery mutant

**None generated on this PR.** The old artifacts also include no unsafe high-recovery mutant (no output tree). If a later live run produces a high-recovery candidate that records any violation, prohibited execution, or incomplete audit, the evaluator assigns zero fitness and Track 1 must reject promotion.

## Result

**not-run / no-improvement.** Preserve that. There is no AI win to report. The handwritten frozen B2/B3 policies remain the Track 1 baseline.

## Track 1

The experiment was **not** applied to the safety kernel. Protected files are left exactly as on `main`:

- `bailiff/guardrails.py`, `bailiff/webhook.py`, `bailiff/recovery_truth.py`
- `bailiff/razorpay_testmode.py`, `scripts/razorpay_testmode_demo.py`
- `bailiff/checker.py`, `bailiff/policies.py`, `bailiff/runner.py`, `bailiff/fixtures.py`, `bailiff/rules.json`
- `outputs/**`
- `FINDINGS.md`, `README.md`, `AGENTS.md`, `RECOVERYTRUTH.md`, `app.py`, `FINAL_VERIFICATION.md`, `SUBMISSION_READINESS.md`
- `SHA256SUMS.txt`

Promotion of any evolved winner into `bailiff/` would threaten Track 1 (kernel freeze, frozen ledger, checksum identity). Promotion was dropped. `SUBMISSION_READINESS.md` already requires OpenEvolve to stay isolated from guardrails, webhook authentication, RecoveryTruth fences, and provider execution.

## How to re-run later if keys exist

Follow `experiments/openevolve/README.md`. Cap **~10 generations**. Do not edit frozen files.

```bash
python -m venv .venv-evolve
source .venv-evolve/bin/activate
pip install -e .
pip install openevolve

# Gemini
export GEMINI_API_KEY="..."   # shell only; never commit
python -m openevolve.cli \
  --initial-program experiments/openevolve/initial_program.py \
  --evaluator experiments/openevolve/evaluator.py \
  --config experiments/openevolve/config_gemini.yaml \
  --iterations 10 \
  --output experiments/openevolve/output-gemini

# or Groq
export GROQ_API_KEY="..."
python -m openevolve.cli \
  --initial-program experiments/openevolve/initial_program.py \
  --evaluator experiments/openevolve/evaluator.py \
  --config experiments/openevolve/config_groq.yaml \
  --iterations 10 \
  --output experiments/openevolve/output-groq
```

Write outputs only under `experiments/openevolve/`. If no safe candidate beats handwritten B2 on zero violations, report that negative result. Do not merge a winner into `bailiff/`.

After a real run, A1/A2 should regenerate `SHA256SUMS.txt` so new experiment files are added without silently rewriting frozen output hashes from a different environment.
