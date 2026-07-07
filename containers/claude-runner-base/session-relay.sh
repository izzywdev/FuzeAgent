#!/bin/bash
# Starts Claude Code as subprocess, streams output to WS_RELAY_URL for human supervision.
# The relay forwards all agent stdout events to the orchestrator WebSocket endpoint.
set -e

if [ -z "$WS_RELAY_URL" ]; then
    echo "[session-relay] No WS_RELAY_URL — running claude directly"
    exec claude "$@"
fi

if ! command -v wscat &>/dev/null; then
    npm install -g wscat 2>/dev/null || true
fi

echo "[session-relay] Agent $AGENT_ID starting, relay: $WS_RELAY_URL"

send_event() {
    local type="$1"
    local data="$2"
    local payload="{\"agentId\":\"$AGENT_ID\",\"type\":\"$type\",\"data\":$data}"
    wscat --connect "$WS_RELAY_URL" --no-stdin --execute "" <<< "$payload" 2>/dev/null || true
}

send_event "start" "\"started\""

claude "$@" 2>&1 | while IFS= read -r line; do
    echo "$line"
    data=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$line" 2>/dev/null || echo "\"$line\"")
    send_event "output" "$data"
done

send_event "exit" "\"done\""
