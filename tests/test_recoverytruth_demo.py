from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_recoverytruth_three_case_demo_runs_end_to_end():
    result = subprocess.run(
        [sys.executable, "scripts/demo_recoverytruth.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CASE A" in result.stdout
    assert "ENTITLEMENT_MISMATCH" in result.stdout.upper()
    assert "TERMINAL_FAILURE" in result.stdout
    assert "MandateGuard handoff" in result.stdout
    assert "PASS · Evidence establishes state" in result.stdout
