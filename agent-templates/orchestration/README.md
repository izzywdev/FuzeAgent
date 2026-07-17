# Agent-to-agent orchestration

Three ways agents coordinate, from cheapest to most flexible. The unifying
principle: **Managed-Agents sessions are persistent server-side** — each session
keeps its full conversation history, sandbox filesystem, and outputs, and resumes
cleanly after idling. So a handoff carries a **pointer + a summary**, never a copied
transcript, and an idle session costs nothing while it waits.

## 1. In-process fan-out — `multiagent` coordinator (same environment)

A coordinator agent delegates to a roster of sub-agents *within one session*
(threads share one sandbox + environment). Native **wait-for-reply**: the
coordinator delegates and receives `agent.thread_message_received`. Best for
parallel fan-out where every sub-agent can run in the same environment.

Limits: one level deep; **all threads share the coordinator's single environment**
— so it cannot make the devops sub-agent run on the self-hosted worker. For that,
use cross-session handoff (below). Defined via `coordinator/coordinator.json`.

## 2. Cross-session wait-for-reply — `ask_agent` (the knowledgeable replacement for issue-polling)

Instead of "open a GitHub issue → poll for a comment," an agent calls the **handoff
MCP** tool:

```
ask_agent(target, question) -> { session_id, status, reply | pending }
```

`target` is a role name (spawns a fresh session in that role's own environment) or
an existing session id (continues it). It runs the target to its next stop and
returns the reply synchronously. If the target pauses on an `always_ask` guard,
status is `blocked` and an operator answers with `approve(session_id, tool_use_id, …)`.

## 3. Resume-callback relay — `spawn_agent` + `resume_session` (hand-forward, no context copy)

The chain pattern, done right:

```
A: spawn_agent(role="devops", task="<concise>", reply_to_session_id=A.session_id)
   → returns B.session_id; A then goes IDLE (no live container while it waits)
B: …does its work in its own environment…
B: resume_session(session_id=A.session_id, summary="<concise work-state>")
   → A WAKES with its full history intact + B's summary. No transcript was copied.
```

- The originating session id is the only "context" that travels — the history lives
  server-side and is restored on resume.
- Chain arbitrarily deep (A→B→C→…); each hop passes only a summary + the session id
  to resume when done.
- **Large state?** Pass `context_ref="/repo/.fuze/handoff/<id>.md"`: the callee
  persists state to that repo file and the resumed agent reads it — state in git,
  not in the prompt.

`orchestration/relay.py` is the deterministic, orchestrator-driven version of this
chain (one session per role, each step passes its concise final report forward,
sessions archived as they hand off) — use it when *you* own the sequence.
`spawn_agent`/`resume_session` are the **agent-initiated** version — use them when an
agent should decide who to hand to, mid-task.

## The handoff MCP server (`handoff_mcp/`)

Holds `ANTHROPIC_API_KEY` **server-side** and creates/continues sessions on agents'
behalf, so the key is never in a sandbox. Declared as the `handoff` MCP server on
every role (`roles/_base/role.json`, gated by `HANDOFF_MCP_URL`). Tools:
`spawn_agent`, `resume_session`, `ask_agent`, `approve`, `memory_write`, `memory_read`.

Local run:

```bash
pip install -r handoff_mcp/requirements.txt
export ANTHROPIC_API_KEY=...      # server-side only
python handoff_mcp/server.py      # streamable-HTTP MCP on :8000/mcp; point HANDOFF_MCP_URL at it
```

Deploy as a container (the intended prod shape):

```bash
docker build -f orchestration/handoff_mcp/Dockerfile -t <registry>/agent-handoff:dev .   # context = agent-templates/
```

The image is minimal — at runtime it needs only `ANTHROPIC_API_KEY` and the id state in
`/state` (`agent-ids.json`, `vault-ids.json`, `memory-ids.json`). Those ids are produced
by the sync scripts in CI (full repo checkout) and mounted as the `handoff-state`
ConfigMap; the ids are **not** secrets. See `deploy/handoff-mcp.yaml` (Deployment +
Service; GitOps via Argo, `SealedSecret` for the key). In-cluster the role agents point
`HANDOFF_MCP_URL` at `http://handoff-mcp.fuzeinfra.svc.cluster.local:8000/mcp`.

## Memory-store handoff channel

A shared **memory store** (`memory/handoff.json`, synced by `sync_memory.py`) is attached
`read_write` to every role/relay session, mounted in the sandbox, and **persists across
sessions**. It's the durable channel for state too large to inline:

- Agents write work-state with their file tools under the mount (e.g. `/handoff/<id>.md`)
  and pass only the **path** when they hand forward or resume.
- Or use the server-side `memory_write(path, content)` / `memory_read(path)` tools to
  stash/fetch state across sessions without being in one.

So a handoff can carry any of: the **originating session id** (history restored on resume),
an inline **summary**, a **repo file pointer**, or a **memory path** — never a copied
transcript. Memory-store endpoints use the `agent-memory-2026-07-22` beta header (distinct
from the managed-agents one; never send both).

## Why not the GitHub-issue dance

Issue-dispatch + comment-polling has no shared state, re-sends context every round,
can't scope credentials/environment per step, and stalls a whole runner while it
waits. Session-native handoff keeps history server-side, scopes each hop to the right
environment, passes only summaries, and idles for free between hops.

## Other context-passing primitives (native options)

- **Session resume** (above) — default; history is already server-side.
- **Repo file pointer** (`context_ref`) — durable, reviewable state in git.
- **Managed-Agents memory store** (`agent-memory-2026-07-22` beta) — wired: a shared
  `read_write` store attached to every session (see *Memory-store handoff channel* above),
  for durable cross-session state an agent reads/writes by path.
