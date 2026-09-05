# Final verification record

Observed on 5 September 2026, Python 3.11.15, Windows with Git Bash. All financial batch figures are synthetic. Captured Razorpay Test Mode evidence is separate and was not rerun against the provider during verification.

## Verified results

| Check | Observed result |
|---|---|
| Full pytest suite | 308 passed, no failures or skips |
| Independent checker | Positive controls passed |
| Mutation gate | Unmodified scratch baseline passed; all 14 mutations caught |
| RecoveryTruth acceptance | Passed |
| Security regression | Passed |
| Release and artifact integrity | Passed |
| Claims, interpreter ablation and refusal-regret checks | Passed |
| Concurrent fallback serialization | Passed |
| Captured provider-proof hash and binding | Passed |
| Fixture-assumption sweep | All 15 settings completed; artifacts byte-identical to shipped versions |
| Final benchmark reproduction | 16 output files and FINDINGS.md reproduced byte-for-byte in a separate clean snapshot |
| Main UI | Four screens checked at desktop and 390-pixel mobile width; nine arms and nine price points present |
| Browser audit verification | All 100 batch receipt chains verified; edited receipt fails verification |
| Browser export | 605,915-byte batch JSON downloaded in Brave and parsed; 100 receipts |
| Streamlit | Six views, all seven simulator scenarios, and separate provider-proof view passed AppTest |
| JavaScript | Syntax check passed; no page errors during functional checks |

The fixture sweep places B3 on the non-dominated frontier while B2 is dominated in 35/45 regime observations; a fully guarded policy is preferred at 1x harm in 18/45. These are conditional synthetic findings, not competitive rankings.

## Reproduction provenance

- Clean local Git snapshot `42dd1ef`: `scripts/test.sh`, independent checker, mutation gate with green baseline.
- Clean snapshot `e73ddca`: release check including the full suite and acceptance gates, then the complete default fixture sweep and closing SHA256SUMS verification.
- Clean snapshot `3dde430`: `scripts/demo.sh` and `scripts/evaluate.sh`; outputs and findings matched the reviewed artifacts. The final chart-script change adds interpreter headers only.
- The original deep wrapper stopped at a Windows executable-file check. Adding Python interpreter headers fixed that portability issue; the release stage and fixture sweep were then completed successfully. Do not describe that first wrapper invocation as an uninterrupted pass.
- Final presentation edits after those snapshots: repository URLs, this record, readiness status, and the requested SVG logo. Runtime behavior was unchanged.
- Dataset SHA-256: `cbf161e2c06c35682b696e2d3bb50c54b27c35ad28aae7a63e85bb9343ef5b4e`
- Rules SHA-256: `70e2909d26598695f74ae9e4d5c81dabb4c772d1f6d376d6567923cdc8a52506`
- Policy version: `0.9.0`
- Protocol: 20 seeds, 3 regimes, 100 cases per seed/regime, 9 arms.

`outputs/manifest.json`, `outputs/evidence_manifest.json` and `SHA256SUMS.txt` contain the complete seed list and output hashes. Shipped charts are not byte reproducible across different rendering environments; the reproduction above used the same installed environment.

One non-failing dependency deprecation warning came from Starlette's AnyIO alias. Streamlit also emitted migration notices for `use_container_width`; all checked views rendered successfully.

## Publication and owner actions

The target is `https://github.com/Akshu1245/razropay`. Public visibility and the Pages deployment must be confirmed separately; local test success does not prove public availability. The owner will record/upload the five-minute video and submit the application.

No guarantee of winning, production readiness, regulatory certification, production AI accuracy or merchant recovery is made. See `MARKET_READY_ARCHITECTURE.md` for the production boundary. The earlier Linux verification is historical context only: `docs/OFFLINE_VERIFICATION_BASELINE.md`.
