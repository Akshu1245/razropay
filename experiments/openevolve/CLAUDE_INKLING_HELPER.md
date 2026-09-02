# Claude Code / Inkling helper boundary

Use this only as a coding/writing helper. It must not run the policy evolution loop and must not edit the frozen submission safety surface.

## Allowed work

- `experiments/openevolve/evaluator.py`
- files under `experiments/openevolve/` used for reports/configuration
- refusal-report templates
- judge-facing copy and pitch drafts
- documentation explaining observed results

## Forbidden work

Do not edit or propose edits to:

- `bailiff/guardrails.py`
- `bailiff/webhook.py`
- `bailiff/recovery_truth.py`
- `bailiff/recovery_runtime.py`
- `bailiff/razorpay_testmode.py`
- canonical policy files on the frozen submission branch
- frozen benchmark outputs or checksums

Do not claim Razorpay Test Mode results unless the exact receipt/proof artifacts from a real Test Mode run are present. Do not describe the Payment Link fallback as an AutoPay retry. Do not describe a hash chain as tamper-proof.

## Helper prompt

You are helping with MandateGuard, a Razorpay Buildathon Track 03 project. Treat the frozen safety and execution code as read-only. Your job is to improve only evaluator code, experiment reports, and pitch copy. OpenEvolve mutates only the isolated proposed-action function in `experiments/openevolve/initial_program.py`. Every candidate must still pass the unchanged MandateGuard guardrails. If a candidate causes any violation or prohibited provider action, the evaluator must assign zero fitness. Synthetic benchmark rupees must stay explicitly synthetic. Never invent Test Mode evidence, recovery receipts, provider IDs, payment IDs, or RecoveryProof hashes.

Before producing any edit, state which files you will touch. If a requested change would alter a forbidden file, refuse that edit and suggest an experiment-side alternative.
