#!/usr/bin/env bash
# Deep verification. Slower than release_check.sh and strictly stronger.
#
# release_check.sh answers "does the release build and behave".
# This answers "is the evidence worth believing", which is a different question:
#   1. the whole suite, including the adversarial and property based tests
#   2. mutation check    — do the tests actually catch the bugs they name
#   3. release gate      — packaging, determinism, generated artefacts
#   4. fixture sweep     — do the conclusions survive assumptions hostile to them
#
# Run before submitting. Expect a few minutes.
set -euo pipefail
cd "$(dirname "$0")/.."

# Chart immutability guard.
#
# The three rendered PNGs under outputs/ are the only shipped artefacts that
# are not byte reproducible across environments: Matplotlib version, FreeType
# version, and font fallback all change the rendered bytes, and this was
# measured, not assumed (Matplotlib 3.10.9 and 3.11.1 render all three
# differently from identical input data).
#
# Verification must therefore never regenerate them, or `sha256sum -c
# SHA256SUMS.txt` would start failing on a machine whose only sin is a
# different Matplotlib. Regeneration belongs to scripts/evaluate.sh, which is
# a generation step, not a verification step.
#
# Rather than assert that property in prose, this script enforces it: the
# chart hashes are captured before stage 1 and re-checked after stage 4.
SHIPPED_CHARTS=(outputs/architecture.png outputs/frontier.png outputs/sensitivity.png)
_CHART_HASHES_BEFORE="$(sha256sum "${SHIPPED_CHARTS[@]}")"

# The hostile fixture sweep deliberately writes its report artifacts. Deep
# verification is documented as non-mutating, so preserve the shipped copies
# and restore them after the sweep before checking the release manifest.
_SWEEP_TMP="$(mktemp -d)"
cp ROBUSTNESS.md "$_SWEEP_TMP/ROBUSTNESS.md"
cp outputs/fixture_sensitivity.json "$_SWEEP_TMP/fixture_sensitivity.json"
_restore_sweep_outputs() {
  cp "$_SWEEP_TMP/ROBUSTNESS.md" ROBUSTNESS.md
  cp "$_SWEEP_TMP/fixture_sensitivity.json" outputs/fixture_sensitivity.json
  rm -rf "$_SWEEP_TMP"
}
trap _restore_sweep_outputs EXIT

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

# Restore the shipped report artifacts immediately. The sweep result has
# already been exercised and printed; the release tree must remain unchanged.
_restore_sweep_outputs
trap - EXIT

echo
echo "==> chart immutability guard"
if [[ "$(sha256sum "${SHIPPED_CHARTS[@]}")" != "$_CHART_HASHES_BEFORE" ]]; then
  echo "FAIL: verification modified a shipped chart PNG." >&2
  echo "Verification must never regenerate charts; only scripts/evaluate.sh may." >&2
  echo "Before:" >&2; echo "$_CHART_HASHES_BEFORE" >&2
  echo "After:" >&2;  sha256sum "${SHIPPED_CHARTS[@]}" >&2
  exit 1
fi
echo "shipped chart PNGs unchanged by verification (3/3)"

echo
echo "==> shipped artefact integrity"
sha256sum -c SHA256SUMS.txt >/dev/null
echo "SHA256SUMS.txt verifies after the full verification workflow (all files)"

echo
echo "All four verification stages passed."
echo "Read ROBUSTNESS.md for where the conclusions hold and where they do not."
