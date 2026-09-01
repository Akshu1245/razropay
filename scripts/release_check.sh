#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MANDATEGUARD_OFFLINE="${MANDATEGUARD_OFFLINE:-1}"

for script in scripts/test.sh scripts/demo.sh scripts/evaluate.sh scripts/release_check.sh scripts/make_frontier.py scripts/make_sensitivity_chart.py scripts/make_findings.py; do
  test -x "$script"
done

if grep -RInE '^(<<<<<<<|=======|>>>>>>>)( |$)' \
  --exclude-dir=.git --exclude-dir=outputs/generated \
  --exclude-dir=.venv --exclude-dir=venv \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache --exclude-dir=.hypothesis \
  --exclude-dir=build --exclude-dir=dist --exclude-dir='*.egg-info' \
  --exclude-dir=node_modules .; then
  echo "release check failed: merge conflict markers found" >&2
  exit 1
fi
if grep -RInE '\{\{[^}]+\}\}' README.md docs outputs FINDINGS.md; then
  echo "release check failed: unresolved placeholders found" >&2
  exit 1
fi

python3 -m compileall -q bailiff tests scripts
python3 -m pytest -q

# RecoveryTruth is kept outside the frozen 283-test benchmark count so the
# original benchmark evidence does not silently move. It is nevertheless a
# mandatory release gate: financial-truth resolution, stale-event precedence,
# in-flight duplicate-collection blocking, write-time fencing, exactly-once
# fallback creation and postcondition proof must all pass before packaging.
python3 scripts/recoverytruth_check.py

python3 -m bailiff.demo
rm -rf outputs/demo
python3 -m bailiff.runner --seeds 5 --n 12 --output-dir outputs/demo >/dev/null
if [[ ! -f outputs/evidence_manifest.json || ! -f outputs/breakeven.json || ! -f outputs/frontier.png || ! -f outputs/sensitivity.png || ! -f outputs/sensitivity.json || ! -f outputs/generated/evidence_ledger_full.json || ! -f FINDINGS.md ]]; then
  _preserved_charts="$(mktemp -d)"
  for _chart in outputs/architecture.png outputs/frontier.png outputs/sensitivity.png; do
    [[ -f "$_chart" ]] && cp -p "$_chart" "$_preserved_charts/$(basename "$_chart")"
  done

  ./scripts/evaluate.sh >/dev/null

  for _chart in outputs/architecture.png outputs/frontier.png outputs/sensitivity.png; do
    _saved="$_preserved_charts/$(basename "$_chart")"
    [[ -f "$_saved" ]] && cp -p "$_saved" "$_chart"
  done
  rm -rf "$_preserved_charts"
fi
python3 scripts/check_release.py
