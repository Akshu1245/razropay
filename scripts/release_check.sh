#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MANDATEGUARD_OFFLINE="${MANDATEGUARD_OFFLINE:-1}"

for script in scripts/test.sh scripts/demo.sh scripts/evaluate.sh scripts/release_check.sh scripts/make_frontier.py scripts/make_sensitivity_chart.py scripts/make_findings.py; do
  test -x "$script"
done

if grep -RInE '^(<<<<<<<|=======|>>>>>>>)( |$)' --exclude-dir=.git --exclude-dir=outputs/generated .; then
  echo "release check failed: merge conflict markers found" >&2
  exit 1
fi
if grep -RInE '\{\{[^}]+\}\}' README.md docs outputs FINDINGS.md; then
  echo "release check failed: unresolved placeholders found" >&2
  exit 1
fi

python3 -m compileall -q bailiff tests scripts
python3 -m pytest -q
python3 -m bailiff.demo
rm -rf outputs/demo
python3 -m bailiff.runner --seeds 5 --n 12 --output-dir outputs/demo >/dev/null
if [[ ! -f outputs/evidence_manifest.json || ! -f outputs/breakeven.json || ! -f outputs/frontier.png || ! -f outputs/sensitivity.png || ! -f outputs/sensitivity.json || ! -f outputs/generated/evidence_ledger_full.json || ! -f FINDINGS.md ]]; then
  # This branch always fires in a fresh extraction, because outputs/generated
  # is deliberately not shipped. It rebuilds the derived evidence — which is
  # byte reproducible everywhere — but it also calls the chart renderers, and
  # rendered PNGs are NOT byte reproducible across environments (Matplotlib
  # 3.10.9 and 3.11.1 disagree on all three from identical input data).
  #
  # Left alone, that means a reviewer whose only difference is a newer
  # Matplotlib runs the release gate and then watches `sha256sum -c
  # SHA256SUMS.txt` fail on three files, for no reason connected to the
  # release. The shipped PNGs are the release artefact; verifying a release
  # must not re-render it. So the shipped bytes are preserved across the
  # rebuild, and only the data artefacts are regenerated.
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
