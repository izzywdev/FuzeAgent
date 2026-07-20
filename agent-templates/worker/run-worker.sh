#!/usr/bin/env bash
# Always-on self-hosted worker for the FuzeInfra devops environment.
#
# Claims work items from the `self_hosted` environment queue and runs the agent's
# tools locally (in this container, on our infra). Credentials the tools use
# (KUBECONFIG, GH_TOKEN, cloud keys) come from the container environment / mounted
# secrets — never from a cloud sandbox.
#
# Required:
#   ANTHROPIC_ENVIRONMENT_ID   env_...   (self_hosted environment id)
#   ANTHROPIC_ENVIRONMENT_KEY  sk-ant-oat01-...  (Console-generated environment key)
# Optional:
#   KUBECONFIG (defaults to /workspace/.kube/config if mounted), GH_TOKEN, etc.
set -euo pipefail

: "${ANTHROPIC_ENVIRONMENT_ID:?set ANTHROPIC_ENVIRONMENT_ID (self_hosted env id)}"
: "${ANTHROPIC_ENVIRONMENT_KEY:?set ANTHROPIC_ENVIRONMENT_KEY (Console-generated environment key)}"

WORKDIR="${WORKER_WORKDIR:-/workspace}"
mkdir -p "$WORKDIR"

# Re-assert the guard shims are ahead of the real CLIs (defense in depth).
export PATH="/opt/guards:${PATH}"
command -v ant >/dev/null 2>&1 || {
  echo "FATAL: the 'ant' CLI is not installed. Install it per the Managed Agents" >&2
  echo "quickstart and/or rebuild with --build-arg ANT_CLI_PKG=<correct-package>." >&2
  exit 1
}

echo "Starting self-hosted worker for environment ${ANTHROPIC_ENVIRONMENT_ID} (workdir ${WORKDIR})"
# Flags per docs/en/managed-agents/reference#self-hosted-worker. Always-on poll.
exec ant beta:worker \
  --environment-id "${ANTHROPIC_ENVIRONMENT_ID}" \
  --workdir "${WORKDIR}" \
  --log-format json
