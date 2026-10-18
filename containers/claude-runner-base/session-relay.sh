#!/bin/bash
# Starts Node.js bidirectional relay or runs bash standby loop.
# Streams output to WS_RELAY_URL for human supervision.
set -e

# 1. Prefer Node.js 20+ native bidirectional WebSocket runner
if command -v node &>/dev/null && [ -f /usr/local/bin/session-relay.mjs ]; then
    echo "[session-relay] Launching Node.js bidirectional WebSocket relay..."
    exec node /usr/local/bin/session-relay.mjs
fi

# 2. Legacy claude CLI mode if arguments supplied
if [ $# -gt 0 ]; then
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
    exit 0
fi

# 3. Idle standby watchdog so container never terminates prematurely
echo "[session-relay] Agent ${AGENT_ID:-sandbox} container standby..."
while true; do
    sleep 3600 &
    wait $!
done
