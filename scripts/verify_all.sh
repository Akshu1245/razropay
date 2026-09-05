#!/usr/bin/env bash
# Deep verification. Slower than release_check.sh and strictly stronger.
#
# The deep verifier intentionally runs generation-heavy checks in an isolated
# scratch copy. This keeps the checked-out release tree byte-for-byte unchanged
# while still exercising the full suite, mutation testing, release gate, and
# hostile fixture sweep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SHIPPED_CHARTS=(outputs/architecture.png outputs/frontier.png outputs/sensitivity.png)
_CHART_HASHES_BEFORE="$(sha256sum "${SHIPPED_CHARTS[@]}")"

_VERIFY_TMP="$(mktemp -d)"
cleanup() {
  rm -rf "$_VERIFY_TMP"
}
trap cleanup EXIT

# Copy the repository source/evidence into a disposable verification workspace.
# Build caches, VCS metadata and local environments are intentionally excluded.
mkdir -p "$_VERIFY_TMP/repo"
tar \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='./.pytest_cache' \
  --exclude='./.hypothesis' \
  --exclude='./node_modules' \
  --exclude='./build' \
  --exclude='./dist' \
  --exclude='*.egg-info' \
  --exclude='*/__pycache__' \
  -cf - . | tar -xf - -C "$_VERIFY_TMP/repo"

cd "$_VERIFY_TMP/repo"

echo "==> 1/4  full test suite"
./scripts/test.sh

echo
echo "==> 2/4  mutation check: does the suite have teeth"
python3 scripts/mutation_check.py

echo
echo "==> 3/4  release gate"
./scripts/release_check.sh

echo
echo "==> 4/4  fixture assumption sweep"
python3 scripts/fixture_sensitivity.py --seeds "${SWEEP_SEEDS:-5}" --n "${SWEEP_N:-100}"

# The scratch tree is allowed to contain regenerated evidence. The real release
# checkout is not. Return to it and verify its immutable shipped bytes directly.
cd "$ROOT"

echo
echo "==> chart immutability guard"
if [[ "$(sha256sum "${SHIPPED_CHARTS[@]}")" != "$_CHART_HASHES_BEFORE" ]]; then
  echo "FAIL: deep verification modified a shipped chart PNG." >&2
  echo "Before:" >&2; echo "$_CHART_HASHES_BEFORE" >&2
  echo "After:" >&2; sha256sum "${SHIPPED_CHARTS[@]}" >&2
  exit 1
fi
echo "shipped chart PNGs unchanged by verification (3/3)"

echo
echo "==> shipped artefact integrity"
sha256sum -c SHA256SUMS.txt >/dev/null
echo "SHA256SUMS.txt verifies after the full isolated verification workflow (all files)"

echo
echo "All four verification stages passed."
echo "Read ROBUSTNESS.md for the shipped robustness evidence and rerun the sweep to reproduce it."
