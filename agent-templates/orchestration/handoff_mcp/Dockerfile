# Handoff MCP server image (minimal — server + REST/driver helpers only).
#
# At runtime the server needs just: ANTHROPIC_API_KEY (Secret) + the id state in
# /state (agent-ids.json, vault-ids.json, memory-ids.json). It does NOT need the
# role/persona config — that's only used by the sync scripts, which run in CI (with
# the full repo checkout) and publish .state as a mounted ConfigMap (ids are not
# secrets). See deploy/handoff-mcp.yaml.
#
#   docker build -f orchestration/handoff_mcp/Dockerfile -t <registry>/agent-handoff:dev .   # context = agent-templates/
FROM python:3.12-slim

WORKDIR /app
COPY orchestration/handoff_mcp/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY sync/ /app/sync/
COPY orchestration/handoff_mcp/ /app/handoff_mcp/

ENV HANDOFF_SYNC_DIR=/app/sync \
    FUZE_STATE_DIR=/state \
    PYTHONPATH=/app/sync \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
# streamable-HTTP MCP is served at /mcp — point HANDOFF_MCP_URL at http://<host>:8000/mcp
CMD ["python", "/app/handoff_mcp/server.py"]
