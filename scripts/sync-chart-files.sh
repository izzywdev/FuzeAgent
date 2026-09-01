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
#   deploy/helm/fuzeagent/files/registration/{manifest.json,policy.json,register.sh}
#     What the registration init container mounts and executes. ADDED after both
#     had silently drifted from the source, with real consequences:
#
#       manifest.json  the vendored copy declared slug "agent" while the source
#                      said "fuzeagent". The init container PUTs the VENDORED
#                      copy, so the product self-registered under a slug that
#                      does not match FuzeFront's own seed (builtins.ts:35,
#                      slug: 'fuzeagent') — two registry rows for one product.
#       register.sh    the vendored copy still carried the
#                      `command -v jq || die` preflight. The init image is
#                      curlimages/curl:8.8.0, which has NO jq, so the container
#                      died BEFORE it ever contacted the registry and the pod
#                      CrashLoopBackOff'd with a state indistinguishable from a
#                      bad token. The curl-only rewrite landed in the source and
#                      never reached the copy that actually runs.
#
#     Neither was a bad edit. Both were correct fixes applied to the file a human
#     reads, in a repo where nothing checked that the file the CLUSTER reads had
#     kept up.
#
#   scripts/sync-chart-files.sh          copy source -> copies
#   scripts/sync-chart-files.sh --check  fail if they differ (for CI)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SPEC="$ROOT/contracts/openapi.yaml"
OVERRIDES="$ROOT/mcp/tools.overrides.yaml"
REG="$ROOT/registration"
CHART_REG="$ROOT/deploy/helm/fuzeagent/files/registration"
DESTS=(
  "$ROOT/services/orchestrator/contracts/openapi.yaml:$SPEC"
  "$ROOT/deploy/helm/fuzeagent/files/openapi.yaml:$SPEC"
  "$ROOT/deploy/helm/fuzeagent/files/tools.overrides.yaml:$OVERRIDES"
  "$CHART_REG/manifest.json:$REG/manifest.json"
  "$CHART_REG/policy.json:$REG/policy.json"
  "$CHART_REG/register.sh:$REG/register.sh"
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
