#!/usr/bin/env bash
# =============================================================================
# Keep the mechanical copies of contracts/openapi.yaml in sync with the source.
#
# Two forced copies, for two different reasons, both silent failures if stale:
#
#   services/orchestrator/contracts/openapi.yaml
#     The orchestrator image is built with `context: services/orchestrator`
#     (.github/workflows/release.yml), so the repo-root contracts/ tree is not
#     in the build context at all. This copy ships in the image and is what
#     GET /openapi.yaml serves. A stale copy makes the deployed API publish a
#     contract for a different build.
#
#   deploy/helm/fuzeagent/files/{openapi.yaml,tools.overrides.yaml}
#     Helm can only read files inside the chart directory. These are what the
#     MCP gateway pod mounts. A stale OVERRIDES copy is the dangerous one on
#     this repo: it would serve `startTaskExecution` to a model as an ordinary
#     reversible write, when it dispatches an agent that cannot be recalled.
#
#   scripts/sync-chart-files.sh          copy source -> copies
#   scripts/sync-chart-files.sh --check  fail if they differ (for CI)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SPEC="$ROOT/contracts/openapi.yaml"
OVERRIDES="$ROOT/mcp/tools.overrides.yaml"
DESTS=(
  "$ROOT/services/orchestrator/contracts/openapi.yaml:$SPEC"
  "$ROOT/deploy/helm/fuzeagent/files/openapi.yaml:$SPEC"
  "$ROOT/deploy/helm/fuzeagent/files/tools.overrides.yaml:$OVERRIDES"
)

if [[ "${1:-}" == "--check" ]]; then
  status=0
  for pair in "${DESTS[@]}"; do
    dst="${pair%%:*}"; src="${pair#*:}"
    if ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      echo "DRIFT: ${dst#"$ROOT"/} differs from ${src#"$ROOT"/}"
      diff -u "$dst" "$src" | head -40 || true
      status=1
    fi
  done
  if [[ $status -eq 0 ]]; then
    echo "Chart/image file copies are in sync."
  else
    echo
    echo "Run scripts/sync-chart-files.sh to update the copies, then commit them."
  fi
  exit $status
fi

for pair in "${DESTS[@]}"; do
  dst="${pair%%:*}"; src="${pair#*:}"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "synced ${dst#"$ROOT"/}"
done
