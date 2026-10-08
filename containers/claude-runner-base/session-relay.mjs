#!/usr/bin/env node
/**
 * Bidirectional Agent Session Relay for FuzeAgent Sandboxes.
 * Connects to Orchestrator WebSocket Bus via native Node.js 20+ WebSocket.
 * Streams real-time agent output tokens & bash tool executions back to user chat.
 */

import { spawn } from 'node:child_process';

const wsRelayUrl = process.env.WS_RELAY_URL || '';
const agentId = process.env.AGENT_ID || 'agent-sandbox';

console.log(`[session-relay] Initializing sandbox agent ${agentId}`);

let ws = null;
let reconnectTimer = null;
let isConnected = false;

function buildTargetUrl() {
  if (!wsRelayUrl) return null;
  // If URL already ends with agentId or /stream, keep as is
  if (wsRelayUrl.endsWith(`/${agentId}`) || wsRelayUrl.endsWith('/ws/stream')) {
    return wsRelayUrl;
  }
  // Otherwise append agentId path
  return wsRelayUrl.endsWith('/') ? `${wsRelayUrl}${agentId}` : `${wsRelayUrl}/${agentId}`;
}

function connect() {
  const targetUrl = buildTargetUrl();
  if (!targetUrl) {
    console.log('[session-relay] No WS_RELAY_URL configured. Running idle watchdog.');
    return;
  }

  console.log(`[session-relay] Connecting to bus: ${targetUrl}`);

  try {
    ws = new WebSocket(targetUrl);

    ws.onopen = () => {
      isConnected = true;
      console.log(`[session-relay] ⚡ Connected to orchestrator event bus at ${targetUrl}`);
      
      // Register with orchestrator
      ws.send(JSON.stringify({
        role: 'agent',
        agentId,
        type: 'agent_status',
        status: 'online',
        currentTask: 'Pod sandbox initialized and connected to event bus. Standby for tasks.',
      }));
    };

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);

        // 1. Heartbeat
        if (msg.action === 'ping' || msg.type === 'ping') {
          ws.send(JSON.stringify({
            role: 'agent',
            agentId,
            type: 'pong',
            timestamp: new Date().toISOString(),
          }));
          return;
        }

        // 2. Chat / Prompt execution
        if (msg.action === 'chat' || msg.action === 'execute') {
          const prompt = msg.prompt || msg.message || msg.command || '';
          console.log(`[session-relay] 📥 Received execution request: ${prompt.slice(0, 60)}...`);

          ws.send(JSON.stringify({
            role: 'agent',
            agentId,
            type: 'agent_status',
            status: 'executing',
            currentTask: `Executing: ${prompt.slice(0, 40)}...`,
          }));

          ws.send(JSON.stringify({
            role: 'agent',
            agentId,
            type: 'agent_thought',
            thought: `Container sandbox executing command in /home/agent/workspace...`,
            timestamp: new Date().toISOString(),
          }));

          // Run Claude Code CLI if available, else bash
          const hasClaude = process.env.ANTHROPIC_API_KEY && process.env.USE_CLAUDE_CLI === 'true';
          const cmd = hasClaude
            ? ['claude', '-p', prompt, '--output-format', 'text']
            : ['/bin/bash', '-c', prompt.startsWith('/') || prompt.startsWith('ls') || prompt.startsWith('echo') || prompt.startsWith('python') ? prompt : `echo "Processed in container sandbox: ${prompt}"`];

          const runner = spawn(cmd[0], cmd.slice(1), {
            cwd: process.env.WORKDIR || '/workspace',
            env: { ...process.env, CI: '1', FORCE_COLOR: '0' },
          });

          let accumulated = '';

          runner.stdout.on('data', (data) => {
            const chunk = data.toString();
            accumulated += chunk;
            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_chunk',
              chunk,
              accumulated,
              isFinal: false,
            }));
          });

          runner.stderr.on('data', (data) => {
            const chunk = data.toString();
            accumulated += chunk;
            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_chunk',
              chunk,
              accumulated,
              isFinal: false,
            }));
          });

          runner.on('close', (code) => {
            const finalOutput = accumulated.trim() || `Task completed (exit code ${code})`;
            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_message',
              content: finalOutput,
              isFinal: true,
              timestamp: new Date().toISOString(),
            }));

            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_status',
              status: 'online',
              currentTask: 'Standby for commands',
            }));
          });

          runner.on('error', (err) => {
            console.error(`[session-relay] Execution error: ${err.message}`);
            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_message',
              content: `Error executing task inside sandbox: ${err.message}`,
              isFinal: true,
              timestamp: new Date().toISOString(),
            }));

            ws.send(JSON.stringify({
              role: 'agent',
              agentId,
              type: 'agent_status',
              status: 'online',
              currentTask: 'Standby for commands',
            }));
          });
        }
      } catch (err) {
        console.error('[session-relay] Error processing event:', err);
      }
    };

    ws.onclose = () => {
      isConnected = false;
      console.warn('[session-relay] Disconnected from orchestrator. Reconnecting in 5s...');
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 5000);
    };

    ws.onerror = (err) => {
      console.warn(`[session-relay] WebSocket bus error: ${err.message || 'connection failed'}`);
    };
  } catch (err) {
    console.error('[session-relay] Connect failed:', err);
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 5000);
  }
}

connect();

// Keep container process alive indefinitely
setInterval(() => {}, 60000);
