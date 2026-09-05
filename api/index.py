"""Stateless, offline showcase API. No credentials or payment provider access."""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from bailiff._version import RELEASE_VERSION
from bailiff.showcase import run_batch, run_scenario

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="MandateGuard demo", version=RELEASE_VERSION)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["recover", "revoked", "optout", "notice", "ambiguous", "forged", "timeout"]


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "local_simulator", "version": RELEASE_VERSION}


@app.post("/api/demo/scenario")
def scenario(request: ScenarioRequest):
    return run_scenario(request.scenario)


@app.post("/api/demo/batch")
def batch():
    # Fixed workload keeps this public, stateless demonstration bounded.
    return run_batch()


@app.get("/")
def index():
    return FileResponse(ROOT / "public" / "index.html")


app.mount("/", StaticFiles(directory=ROOT / "public"), name="showcase")
