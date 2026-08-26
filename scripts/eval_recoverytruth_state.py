#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from bailiff.recoverytruth_eval import evaluate_resolver, load_challenge, run_baselines
from bailiff.resolver import RealEvidenceStateResolver


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "outputs" / "generated" / "recoverytruth_state_eval.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RecoveryTruth on the frozen Unseen State Challenge")
    parser.add_argument("--real-model", action="store_true", help="also evaluate the configured bounded real resolver")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    dataset_hash, baseline_summaries = run_baselines()
    summaries = list(baseline_summaries)

    if args.real_model:
        _hash_again, cases = load_challenge()
        resolver = RealEvidenceStateResolver(
            model=os.getenv("RECOVERYTRUTH_RESOLVER_MODEL") or None,
            base_url=os.getenv("RECOVERYTRUTH_RESOLVER_BASE_URL") or None,
        )
        summaries.append(evaluate_resolver("recoverytruth_real", resolver, cases))

    payload = {
        "dataset": "recoverytruth_unseen_v1",
        "dataset_sha256": dataset_hash,
        "synthetic": True,
        "claim_scope": (
            "Held-out synthetic state-resolution benchmark. These figures are not Razorpay production metrics "
            "or merchant revenue. Real-model results are included only when --real-model is explicitly requested."
        ),
        "results": [summary.as_dict() for summary in summaries],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"RecoveryTruth Unseen State Challenge · {dataset_hash}")
    print(f"{'resolver':<20} {'accuracy':>9} {'selective':>10} {'coverage':>9} {'unsafe':>8} {'missed':>8}")
    for summary in summaries:
        print(
            f"{summary.resolver:<20} {summary.state_accuracy:>9.3f} {summary.selective_accuracy:>10.3f} "
            f"{summary.automation_coverage:>9.3f} {summary.unsafe_recovery_rate:>8.3f} "
            f"{summary.missed_recovery_rate:>8.3f}"
        )
    print(f"wrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
