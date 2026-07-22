# Shared A2A server image (the ONE server that fronts every tenant).
#
# Build context = agent-templates/  (mirrors orchestration/handoff_mcp/Dockerfile):
#   docker build -f a2a/Dockerfile -t ghcr.io/izzywdev/fuzeagent-a2a:dev .   # ctx = agent-templates/
#
# Runtime surface is fixed by the FROZEN contract (agent-templates/contracts/a2a/v1):
#   POST /rpc                             (JSON-RPC 2.0, binding.md §1)
#   GET  /.well-known/agent-card.json     (unauthenticated card discovery)
# on PORT (8080). Identity/authZ are enforced callee-side (authz.md) from the OIDC
# bearer — never the request body. Tenants are DATA (mounted /config/tenants.yaml).
#
# The server CODE lives in a2a/*.py and is owned by backend-engineer (built in
# parallel). This Dockerfile only PACKAGES it + the typed contract client. Until
# the server lands, the chart ships enabled:false so this image is built/tagged
# but never run.
FROM python:3.12-slim

WORKDIR /app

# Runtime deps (starter — backend-engineer owns the server's dependency set).
COPY a2a/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Typed wire/card models from the frozen contract — the server imports
# `fuze_a2a_client` so request/response shapes cannot drift from the spec.
COPY contracts/a2a/v1/client/ /app/contract-client/
RUN pip install --no-cache-dir /app/contract-client

# The shared A2A server implementation (agent-templates/a2a/).
COPY a2a/ /app/a2a/

# Run as a non-root user (defence in depth; also satisfies a runAsNonRoot
# PodSecurity policy). Code is read-only at runtime; config is mounted at /config.
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin a2a \
    && chown -R a2a:a2a /app
USER 10001

ENV HOST=0.0.0.0 \
    PORT=8080 \
    A2A_PROTOCOL_VERSION=1.0 \
    A2A_TENANTS_FILE=/config/tenants.yaml \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# TODO(server-entrypoint): backend-engineer's server module. Assumed `a2a.server`
# per the packaging layout; adjust to the real entrypoint when a2a/*.py lands.
CMD ["python", "-m", "a2a.server"]
