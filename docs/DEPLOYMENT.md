# Deployment

The submission has one canonical interactive application: **FastAPI + `public/`** via `api/index.py`.

No public demo mode connects to merchant payments or provider credentials.

## Local judge run

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

The header says **Python engine connected** and the bounded `/api/demo/*` endpoints execute the local simulator.

## Docker — canonical portable deployment

```bash
docker build -t mandateguard .
docker run --rm -p 8765:8765 mandateguard
```

The image launches the same `api.index:app` and `public/` interface used by the judge flow. It needs no credentials. `MANDATEGUARD_OFFLINE=1` is set in the image.

Health check:

```text
GET /api/health
```

Expected mode: `local_simulator`.

## Vercel/serverless

`vercel.json` routes `/api/*` to `api/index.py` and serves `public/` for the interface.

A Vercel deployment must be checked independently after deployment; a valid configuration file or local test does not prove a public URL is reachable.

## Static recorded-evidence replay

For hosts that can only serve static files:

```bash
python scripts/build_showcase.py
python -m http.server 8090 --directory public
```

Static mode is intentionally labelled **Recorded engine evidence**. It replays `public/evidence.json`; it does not execute Python.

This mode is useful as a portable fallback, but the Python-backed application is the canonical interactive submission.

## Release discipline

Before publishing a new final revision:

```bash
./scripts/test.sh
./scripts/demo.sh
./scripts/evaluate.sh
./scripts/verify_all.sh
python scripts/build_showcase.py
python scripts/make_checksum_manifest.py > /tmp/SHA256SUMS.candidate
```

Compare the candidate with `SHA256SUMS.txt` after intentional generation. CI independently checks the final tree and browser flow.

## Production boundary

This deployment is a hackathon/demo deployment. Merchant traffic still requires durable state/idempotency, tenant isolation, managed secrets, approved provider capabilities, scheduling/cancellation, cross-process reconciliation, evidence-retention controls and production validation. See `ARCHITECTURE.md`.
