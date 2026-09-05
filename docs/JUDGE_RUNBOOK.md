# Judge runbook

## Start here

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

Open [the local workspace](http://127.0.0.1:8765). Its header should say **Python engine connected**.

1. Click **Run recovery batch**. The Python engine runs all nine policies on one 100-case frozen ledger.
2. Filter **Recovered**, open a receipt, and click **Verify audit chain**. Verification happens in the browser.
3. Open **Failure lab**. Run revoked, ambiguous and timeout scenarios. A timeout reports one call and unknown outcome; it does not masquerade as a zero-call refusal.
4. Open **Razorpay proof**. These are captured Test Mode artifacts; no credentials or provider access are used by this screen.
5. Open **Policy comparison**. Review the full price sweep beside the recovery/harm metrics.

The batch INR is synthetic. The separate Test Mode action is a Standard Payment Link fallback, not an AutoPay retry.

## Offline fallback

```bash
python scripts/demo60.py
python -m http.server 8090 --directory public
```

The static site labels itself **Recorded engine evidence**. Its buttons replay exported engine results. It never pretends to run the Python backend.

## Further evidence

- [Generated report](../outputs/report.md)
- [Sensitivity](../outputs/sensitivity.json)
- [Fixture robustness](../ROBUSTNESS.md)
- [Final verification](../FINAL_VERIFICATION.md)
- [Five-minute script](../VIDEO_SCRIPT.md)

Run `python scripts/interpreter_ablation.py` to compare B2 and B3, and `python scripts/refusal_regret.py` to inspect the cost of refusals.
