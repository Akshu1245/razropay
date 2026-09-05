# Deploy the demo

The submission has two supported presentation modes. Neither connects the public UI to merchant payments.

## Python-backed workspace

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --host 127.0.0.1 --port 8765
```

The server serves the UI and the fixed-workload `/api/demo/batch` and `/api/demo/scenario` endpoints. They execute only the local simulator, need no credentials and hold no persistent experiment state.

The separate `bailiff.api:app` is an in-memory experiment/webhook development API. Do not expose it as a production service or mount its optional real-model experiments in a public demo.

## Static Pages

`public/` contains the complete static demo, including generated engine evidence. The supplied Pages workflow uploads that directory.

```bash
python scripts/build_showcase.py
python -m http.server 8090 --directory public
```

Static hosting labels itself **Recorded engine evidence**. This is deliberately different from the **Python engine connected** header on the API host.

After exporting new evidence, refresh the checksum manifest before release. Push the reviewed revision to the linked repository and check the Pages deployment and public URL. A local change does not update a public site.

## Serverless

`vercel.json` routes `/api/*` to the stateless demo entrypoint and serves `public/` for the interface. It must package the project modules and static files. Local API tests verify this entrypoint; a deployed Vercel build still requires its own URL check.

## Existing Streamlit container

```bash
docker build -t mandateguard-lab .
docker run --rm -p 8501:8501 mandateguard-lab
```

The Dockerfile serves Streamlit on port 8501 (or `PORT`). It does not launch a second server on port 8000. Its evidence screens and local simulator need no provider credentials.

See [production gaps](../MARKET_READY_ARCHITECTURE.md) before considering merchant traffic.
