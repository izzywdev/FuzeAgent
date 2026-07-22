# Shared A2A server image (the ONE server that fronts every tenant).
#
# Build context = agent-templates/  (mirrors orchestration/handoff_mcp/Dockerfile):
#   docker build -f a2a/Dockerfile -t ghcr.io/izzywdev/fuzeagent-a2a:dev .   # ctx = agent-templates/
#
# Runtime surface is fixed by the FROZEN contract (agent-templates/contracts/a2a/v1):
#   POST /rpc                             (JSON-RPC 2.0, binding.md §1)
#   GET  /.well-known/agent-card.json     (unauthenticated card discovery)
# on the port from the values file (service.port, 8080). Identity/authZ are enforced
# callee-side (authz.md) from the OIDC bearer — never the request body.
#
# Entrypoint is agent-templates/a2a/runtime.py:main() -> `python -m a2a.runtime`, which
# build_from_env() composes from:
#   A2A_VALUES_FILE  JSON of the values-interface `a2a` block (mounted ConfigMap)
#   A2A_REPOS_DIR    tenant repo checkouts the LocalRepoResolver reads (/repos)
#   AGENT_PROVIDER   Managed-Agents provider id (default anthropic)
#   HOST             bind address (chart sets 0.0.0.0; server defaults to loopback)
# runtime imports `providers` (top-level) and the anthropic provider delegates to the
# `sync/` modules, so both packages are vendored below.
FROM python:3.12-slim

WORKDIR /app

# Runtime deps (server-owned set + `cryptography` for JWKS RS256/ES256 verification).
COPY a2a/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Typed wire/card models from the frozen contract — a2a/_contract.py imports
# `fuze_a2a_client` so request/response shapes cannot drift from the spec.
COPY contracts/a2a/v1/client/ /app/contract-client/
RUN pip install --no-cache-dir /app/contract-client

# The shared A2A server + its runtime deps within the templates tree:
#   a2a/        the server itself (python -m a2a.runtime)
#   providers/  `from providers import get_provider` (Managed-Agents binding)
#   sync/       common/driver/role_loader the anthropic provider delegates to
COPY a2a/ /app/a2a/
COPY providers/ /app/providers/
COPY sync/ /app/sync/

# Run as a non-root user (defence in depth; also satisfies a runAsNonRoot
# PodSecurity policy). Code is read-only; config at /config, repo checkouts at /repos.
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin a2a \
    && chown -R a2a:a2a /app
USER 10001

# Only vars runtime.py / the provider actually read. HOST is set explicitly so the
# in-cluster Service can reach the pod (server defaults to loopback, CWE-605-safe).
# The listen PORT is NOT an env var — the server reads it from the values file
# (service.port), so image and chart stay consistent via one source.
ENV HOST=0.0.0.0 \
    A2A_VALUES_FILE=/config/values.json \
    A2A_REPOS_DIR=/repos \
    AGENT_PROVIDER=anthropic \
    FUZE_STATE_DIR=/state \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "a2a.runtime"]
