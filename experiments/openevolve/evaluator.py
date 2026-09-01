from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from statistics import mean

from openevolve.evaluation_result import EvaluationResult

from bailiff.domain import ActionType
from bailiff.runner import FINAL_SEEDS, run_experiment
import bailiff.policies as policies

ROOT = Path(__file__).resolve().parents[2]
FROZEN_MANIFEST = ROOT / "outputs" / "manifest.json"
FORBIDDEN_SOURCE_TOKENS = (
    "guardrails.py",
    "bailiff.guardrails",
    "recovery_truth",
    "razorpay_testmode",
    "razorpay_adapter",
    "webhook",
    "httpx",
    "requests",
    "socket",
    "subprocess",
    "os.system",
)


def _reject(reason: str) -> EvaluationResult:
    return EvaluationResult(
        metrics={
            "combined_score": 0.0,
            "safety_pass": 0.0,
            "zero_violations": 0.0,
            "recovery_score": 0.0,
        },
        artifacts={"rejected": True, "reason": reason},
    )


def _load_candidate(program_path: str):
    source = Path(program_path).read_text(encoding="utf-8")
    lowered = source.lower()
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token.lower() in lowered:
            raise ValueError(f"candidate references protected execution/safety surface: {token}")
    if "EVOLVE-BLOCK-START" not in source or "EVOLVE-BLOCK-END" not in source:
        raise ValueError("candidate removed OpenEvolve boundary markers")
    spec = importlib.util.spec_from_file_location("mandateguard_evolved_candidate", program_path)
    if spec is None or spec.loader is None:
        raise ValueError("could not import candidate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    choose_action = getattr(module, "choose_action", None)
    if not callable(choose_action):
        raise ValueError("candidate must define choose_action(reason, attempt_count)")
    return choose_action


def evaluate(program_path: str) -> EvaluationResult:
    """Score only the B2 proposal logic on the exact frozen MandateGuard ledger.

    The canonical GuardrailEngine remains in the execution path. Any candidate
    with a violation, prohibited execution, or incomplete audit is assigned
    zero fitness regardless of recovered value.
    """
    manifest = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("final") is not True or manifest.get("n_per_seed") != 100:
        return _reject("frozen benchmark manifest is not the expected final ledger")
    if tuple(manifest.get("seeds", ())) != tuple(FINAL_SEEDS):
        return _reject("frozen seed set changed")

    try:
        choose_action = _load_candidate(program_path)
    except Exception as exc:
        return _reject(f"candidate load rejected: {type(exc).__name__}: {exc}")

    original = policies.proposed_action

    def evolved_proposed_action(arm: str, reason: str, *, attempt_count: int = 0) -> ActionType:
        if arm != "B2":
            return original(arm, reason, attempt_count=attempt_count)
        raw = choose_action(reason, attempt_count)
        try:
            return ActionType(str(raw))
        except ValueError as exc:
            raise ValueError(f"candidate returned unsupported action: {raw!r}") from exc

    policies.proposed_action = evolved_proposed_action
    try:
        rows, evidence, dataset_hashes = run_experiment(
            seeds=FINAL_SEEDS,
            n_per_seed=100,
            interpreter_mode="deterministic_offline",
        )
    except Exception as exc:
        return _reject(f"candidate execution failed: {type(exc).__name__}: {exc}")
    finally:
        policies.proposed_action = original

    selected = [row for row in rows if row["arm"] == "B2"]
    if len(selected) != 60:
        return _reject(f"expected 60 B2 seed/regime rows, got {len(selected)}")

    violations = sum(float(row["violations"]) for row in selected)
    prohibited_rate = max(float(row["prohibited_execution_rate"]) for row in selected)
    incomplete_audit = sum(float(row["audit_incomplete_rows"]) for row in selected)
    if violations != 0 or prohibited_rate != 0 or incomplete_audit != 0:
        return _reject(
            f"safety kill: violations={violations}, prohibited_execution_rate={prohibited_rate}, "
            f"audit_incomplete_rows={incomplete_audit}"
        )

    recovered = mean(float(row["incremental_recovered_inr"]) for row in selected)
    harm_priced_net = mean(float(row["net_value_harm_priced_inr"]) for row in selected)
    provider_calls = mean(float(row["provider_calls"]) for row in selected)
    protected = mean(float(row["protected_value_by_denial_inr"]) for row in selected)
    forgone = mean(float(row["legitimate_recovery_forgone_inr"]) for row in selected)

    combined = max(0.000001, 1.0 + harm_priced_net / 10000.0 + recovered / 20000.0 + protected / 50000.0)

    return EvaluationResult(
        metrics={
            "combined_score": combined,
            "safety_pass": 1.0,
            "zero_violations": 1.0,
            "recovery_score": recovered,
            "harm_priced_net_inr": harm_priced_net,
            "protected_value_inr": protected,
            "legitimate_recovery_forgone_inr": forgone,
            "provider_calls": provider_calls,
        },
        artifacts={
            "rejected": False,
            "frozen_dataset_sha256": manifest.get("dataset_sha256"),
            "dataset_count": len(dataset_hashes),
            "policy_surface": "B2 proposed-action logic only",
            "guardrails_mutated": False,
            "recoverytruth_mutated": False,
        },
    )
