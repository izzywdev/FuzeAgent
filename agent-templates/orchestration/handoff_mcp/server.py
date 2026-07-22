#!/usr/bin/env python3
"""Handoff MCP server — the session-native way for one agent to hand a GOAL to
another agent, now carried **over the A2A wire**.

The tool surface is UNCHANGED (`spawn_agent`, `resume_session`, `ask_agent`,
`approve`, `reach_human`, `memory_write`, `memory_read`) — a dev agent's interface
is identical. What changed is the transport underneath: instead of creating and
driving a Managed-Agents session directly, these tools now discover the target
agent's A2A Agent Card and issue JSON-RPC `SendMessage` / `GetTask` / `CancelTask`
through the FROZEN generated client (`contracts/a2a/v1/client/fuze_a2a_client`), via
`orchestration/a2a_transport.py`.

That is the whole point of A2A: the CALLING agent holds NO domain tools, skills or
credentials of the callee — it just hands over a goal and reads back a Task
(card-projection.md §7). Discovery + addressing follow binding.md; the returned
A2A `TaskState` is mapped back onto the same `{session_id, status, reply, pending}`
shape callers already consume (state-mapping.md §3). INPUT_REQUIRED / AUTH_REQUIRED
surface as a `blocked` status whose `pending.message` a caller MUST read before
assuming the pause is its own — some pauses are addressed to a human the caller
cannot see, resolved on the callee side via `reach_human` (state-mapping.md §4).

Run (on the worker host / a small service):
    pip install -r requirements.txt
    export A2A_TOKEN=...                    # OIDC bearer, server-side only
    export A2A_TARGETS='{"FuzePlan": {"skill_id": "product-manager"}}'   # optional
    python server.py                        # serves streamable-HTTP MCP
Then set HANDOFF_MCP_URL to this server's URL when syncing agents (roles/_base
declares it as an mcp_server so every role can hand off).

The `memory_write` / `memory_read` tools remain a distinct durable-state channel
(the shared memory store) and are unchanged — they are orthogonal to the wire.
"""
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# a2a_transport lives one directory up (orchestration/); the memory tools still use
# the REST `common` helper from ../../sync. HANDOFF_SYNC_DIR overrides sync/ for the
# container image; A2A_CLIENT_DIR (handled inside a2a_transport) overrides the client.
_HERE = os.path.dirname(os.path.abspath(__file__))              # handoff_mcp/
_ORCH = os.path.dirname(_HERE)                                  # orchestration/
SYNC = os.environ.get("HANDOFF_SYNC_DIR") or os.path.join(
    os.path.dirname(_ORCH), "sync")
for _p in (_ORCH, SYNC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import a2a_transport as a2a   # noqa: E402
import common                 # noqa: E402  (memory tools only)

STATE = common.state_dir()  # honors FUZE_STATE_DIR (mounted /state volume in the container)
HANDOFF_INSTRUCTIONS = ("Shared cross-session handoff workspace. Read relevant /handoff/*.md before "
                        "starting delegated work; persist your work-state under /handoff/<id>.md.")

mcp = FastMCP("fuze-handoff",
              host=os.environ.get("HOST", "0.0.0.0"),
              port=int(os.environ.get("PORT", "8000")))


# ---------------------------------------------------------------------------
# A2A-routed handoff tools (transport = A2A; signatures unchanged)
# ---------------------------------------------------------------------------
def _context_instructions(context_ref: str) -> str:
    """Prompt suffix for large-state-by-reference. Over the A2A wire the callee
    resumes its own session and never replays a transcript, so we never inline
    state — we point at it (state-mapping.md §6, `never inline large state`)."""
    if not context_ref:
        return ""
    return (f"\n\nLarger state is passed by reference: persist/read it at '{context_ref}' "
            f"(a repo path, or a path in the shared handoff memory store) rather than inlining it.")


@mcp.tool()
def spawn_agent(role: str, task: str, reply_to_session_id: str = "", context_ref: str = "", wait: bool = False) -> str:
    """Hand a goal to a target agent over A2A, in its own session/environment.

    role: the target agent key (a product/exec identity, e.g. 'FuzePlan' or
        'Exec-cto'; mapped to a skill id via A2A_TARGETS or convention). The caller
        needs NONE of that agent's tools — it only names the outcome it wants.
    task: the goal — a concise instruction, not a pasted transcript.
    reply_to_session_id: retained for signature compatibility. Over A2A there is no
        caller-side resume callback: the result comes back as a Task the caller polls
        via ask_agent(<session_id>) / get_task, or subscribes to. Recorded in the
        returned payload so callers can correlate.
    context_ref: optional repo/memory path holding larger persisted state.
    wait: if true, block until the task settles (terminal or interrupted) and return
        {session_id, status, reply, pending}. If false, fire-and-forget: the task is
        submitted and {session_id, status:"spawned"} returns at once (poll later).
    """
    prompt = task + _context_instructions(context_ref)
    if not wait:
        res = a2a.start(role, prompt, return_immediately=True)
        return json.dumps({"session_id": res["session_id"], "status": "spawned",
                           "reply_to_session_id": reply_to_session_id or None})
    res = a2a.start(role, prompt, return_immediately=False)
    res["reply_to_session_id"] = reply_to_session_id or None
    return json.dumps(res)


@mcp.tool()
def resume_session(session_id: str, summary: str, context_ref: str = "") -> str:
    """Continue an existing A2A task with a concise work-state summary.

    Over the wire this is `SendMessage` carrying the same taskId: the callee resumes
    its own server-side session (full history + sandbox intact) — it never replays a
    transcript (state-mapping.md §1). Returns the task's mapped state after the
    continuation settles.
    """
    text = f"[handoff:resume] {summary}" + _context_instructions(context_ref)
    res = a2a.continue_task(session_id, text)
    res["resumed"] = session_id
    return json.dumps(res)


@mcp.tool()
def ask_agent(target: str, question: str) -> str:
    """Hand a goal to an agent and read back its Task. target = a target agent key
    (starts a fresh task in that agent's own environment) OR an existing session/task
    id (continues it). Returns {session_id, status, reply, pending}; a 'blocked'
    status means the task is INPUT_REQUIRED/AUTH_REQUIRED — read pending.message
    before assuming it is addressed to you (state-mapping.md §4), and answer via
    approve()/resume_session() or, if it needs a human, reach_human()."""
    if a2a.is_known_task(target):
        return json.dumps(a2a.continue_task(target, question))
    return json.dumps(a2a.start(target, question, return_immediately=False))


@mcp.tool()
def approve(session_id: str, tool_use_id: str, allow: bool = True, reason: str = "") -> str:
    """Answer an interrupted (INPUT_REQUIRED/AUTH_REQUIRED) A2A task by continuing it
    with your decision. Over the wire this is `SendMessage` with the same taskId and
    the decision in the message (state-mapping.md §4) — the callee correlates it to
    its own pending tool. Deny with a reason to steer the agent instead of blocking."""
    decision = "APPROVE: proceed." if allow else f"DENY: {reason or 'denied by caller'}"
    if tool_use_id:
        decision += f" (re: {tool_use_id})"
    res = a2a.continue_task(session_id, decision)
    res["tool_use_id"] = tool_use_id
    res["result"] = "allow" if allow else "deny"
    return json.dumps(res)


@mcp.tool()
def reach_human(human: str, message: str, reply_to_session_id: str = "", channels: str = "", wait: bool = False) -> str:
    """Reach a real human through their digital-persona agent — over A2A.

    Hands the message to the persona agent that owns this human's channel credentials
    (their vault: email/Slack/GitHub/WhatsApp/Telegram/phone). That agent — not this
    caller — contacts the human, collects their ACTUAL reply, and reports it back as
    the task result. Use this instead of stalling when a decision or approval needs a
    human. The caller holds none of the human's channel credentials.

    human: person key. Resolved to a persona target via A2A_PERSONA_PREFIX (default
        'persona-') + human, overridable in A2A_TARGETS.
    channels: comma list to prefer (e.g. "slack,email"); empty = their preferred.
    wait: if true, block until the persona reports (reply|blocked|pending); else
        fire-and-forget and return {session_id, human, status:"reaching"}.
    """
    target = a2a.persona_target(human)
    ch = f" via {channels}" if channels else " via their preferred channel"
    prompt = (f"You represent {human}. Reach the real {human}{ch} with the following, collect their "
              f"ACTUAL reply (never fabricate a binding answer), and report it.\n\nMESSAGE:\n{message}")
    if reply_to_session_id:
        prompt += (f"\n\nContext: this was requested to unblock session '{reply_to_session_id}'. "
                   f"If you cannot reach them, report 'BLOCKED: ...'.")
    if not wait:
        res = a2a.start(target, prompt, return_immediately=True)
        return json.dumps({"session_id": res["session_id"], "human": human, "status": "reaching"})
    res = a2a.start(target, prompt, return_immediately=False)
    res["human"] = human
    return json.dumps(res)


# ---------------------------------------------------------------------------
# Durable memory-store channel (unchanged — distinct from the A2A wire)
# ---------------------------------------------------------------------------
def _memory_ids():
    path = os.path.join(STATE, "memory-ids.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def _handoff_store_id():
    ids = _memory_ids()
    if not ids:
        raise RuntimeError("no memory store synced — run sync_memory.py first")
    return next(iter(ids.values()))


@mcp.tool()
def memory_write(path: str, content: str) -> str:
    """Persist durable handoff state to the shared memory store (e.g.
    path='/handoff/<id>.md'). Survives across sessions; pass the path forward instead
    of inlining large context. Creates the memory, or updates it if the path exists."""
    sid = _handoff_store_id()
    mems = common.list_all(f"/v1/memory_stores/{sid}/memories", beta=common.MEMORY_BETA)
    hit = next((m for m in mems if m.get("path") == path), None)
    if hit:
        common.request("POST", f"/v1/memory_stores/{sid}/memories/{hit['id']}",
                       body={"content": content}, beta=common.MEMORY_BETA)
        op = "updated"
    else:
        common.request("POST", f"/v1/memory_stores/{sid}/memories",
                       body={"path": path, "content": content}, beta=common.MEMORY_BETA)
        op = "created"
    return json.dumps({"store_id": sid, "path": path, "result": op})


@mcp.tool()
def memory_read(path: str) -> str:
    """Read durable handoff state back from the shared memory store by path."""
    sid = _handoff_store_id()
    mems = common.list_all(f"/v1/memory_stores/{sid}/memories", beta=common.MEMORY_BETA)
    hit = next((m for m in mems if m.get("path") == path), None)
    if not hit:
        return json.dumps({"store_id": sid, "path": path, "found": False})
    full = common.request("GET", f"/v1/memory_stores/{sid}/memories/{hit['id']}", beta=common.MEMORY_BETA)
    return json.dumps({"store_id": sid, "path": path, "found": True, "content": full.get("content", "")})


def build_app():
    """Streamable-HTTP MCP app, gated by a bearer token when HANDOFF_MCP_TOKEN is set.

    This server presents the family OIDC bearer (A2A_TOKEN) to callee agents on the
    A2A wire, so it must not be open. Managed Agents connect server-to-server and
    present the token as a vault-injected `Authorization: Bearer` credential (keyed to
    the handoff MCP url). In prod the Cloudflare Access email-OTP wildcard is bypassed
    for this hostname (a more-specific Access app), so this app-level bearer is the gate.
    """
    from starlette.responses import JSONResponse
    app = mcp.streamable_http_app()
    token = os.environ.get("HANDOFF_MCP_TOKEN")
    if token:
        expected = f"Bearer {token}"

        @app.middleware("http")
        async def _require_bearer(request, call_next):  # noqa: ANN001
            if request.headers.get("authorization") != expected:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)
    else:
        import sys as _sys
        print("WARNING: HANDOFF_MCP_TOKEN not set — the handoff MCP is UNAUTHENTICATED.", file=_sys.stderr)
    return app


if __name__ == "__main__":
    # Managed Agents connect to remote MCP servers over streamable HTTP.
    import uvicorn
    uvicorn.run(build_app(), host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")))
