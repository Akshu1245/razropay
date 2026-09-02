# MandateGuard OpenEvolve experiment

This directory is an **extra experiment**, not part of the frozen submission proof.
The submission branch remains separate and frozen; this branch is for policy-evolution experimentation only.

## Safety boundary

OpenEvolve may mutate only the block in `initial_program.py` between:

- `EVOLVE-BLOCK-START`
- `EVOLVE-BLOCK-END`

The evaluator rejects candidates that reference protected surfaces such as guardrails,
webhook verification, RecoveryTruth, Razorpay adapters, networking or subprocesses.
The canonical `GuardrailEngine` still evaluates every B2 proposal on the same frozen
MandateGuard benchmark. Any candidate with a violation, prohibited execution, or
incomplete audit receives zero fitness.

The frozen benchmark contract is read from `outputs/manifest.json`: 20 fixed seeds,
3 regimes, 100 cases per seed/regime, 60 datasets total. The experiment never edits
that manifest or the frozen evidence.

## Install

Use a separate environment from the submission proof:

```bash
python -m venv .venv-evolve
source .venv-evolve/bin/activate  # Windows: .venv-evolve\\Scripts\\activate
pip install -e .
pip install openevolve
```

## Run with Gemini

Keep the key only in your shell. Do not commit it.

```bash
export GEMINI_API_KEY="..."
python -m openevolve.cli \
  --initial-program experiments/openevolve/initial_program.py \
  --evaluator experiments/openevolve/evaluator.py \
  --config experiments/openevolve/config_gemini.yaml \
  --iterations 10 \
  --output experiments/openevolve/output-gemini
```

## Run with Groq

```bash
export GROQ_API_KEY="..."
python -m openevolve.cli \
  --initial-program experiments/openevolve/initial_program.py \
  --evaluator experiments/openevolve/evaluator.py \
  --config experiments/openevolve/config_groq.yaml \
  --iterations 10 \
  --output experiments/openevolve/output-groq
```

Stop after 10 iterations. If no safe candidate beats the handwritten policy, report
that result instead of forcing an improvement claim.

## What may be claimed

A winning candidate is only an **offline synthetic-policy result** on the same frozen
ledger. It is not Razorpay production revenue and it does not weaken or replace the
execution guardrails. The useful demo is the refusal comparison: recovered synthetic
rupees versus refusals preserved/dropped, with zero violations required.
