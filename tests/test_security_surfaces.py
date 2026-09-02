"""Protected-surface attacks that used to live only in scripts/.

./scripts/test.sh can stay green while security_regression_check.py is skipped
outside CI. These pytest cases close that hole. They do not claim distributed
exactly-once; WebhookGate state is in-memory and single-process.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_security_regression():
    spec = importlib.util.spec_from_file_location(
        "security_regression_check_for_pytest",
        ROOT / "scripts" / "security_regression_check.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def sec():
    return _load_security_regression()


def test_authority_identity_reuse_is_denied_with_zero_provider_calls(sec):
    """A reused envelope with the wrong identity fields cannot authorize a write."""
    sec.check_authority_identity_binding()


def test_denied_decision_cannot_replay_a_prior_allow_provider_result(sec):
    """Forcing DENY on a previously ALLOWED decision must not reuse the provider call."""
    sec.check_denied_decision_cannot_reuse_prior_provider_result()


def test_payment_identity_mismatch_is_refused(sec):
    """Provider GET that echoes a different payment or link id must fail closed."""
    sec.check_provider_identity_echo()


def test_signed_webhook_with_valid_hmac_but_no_created_at_is_refused(sec):
    """HMAC over raw bytes is not enough: missing created_at is MISSING_CREATED_AT."""
    sec.check_signed_webhook_requires_created_at()
