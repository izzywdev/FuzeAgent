#!/usr/bin/env python3
"""Handoff MCP server — the knowledgeable, session-native way for one agent to
inject a prompt into another agent (instead of the primitive "open a GitHub issue
and poll for a comment").

Runs on YOUR infra and holds ANTHROPIC_API_KEY, so agents never carry the key in
their sandbox. It's declared as an MCP server on each role agent; agents call its
tools. It creates/continues Managed-Agents sessions on their behalf.

Core idea — sessions are persistent server-side (full history + sandbox state),
so handoff carries only a POINTER + a SUMMARY, never a copied transcript:

  spawn_agent(role, task, reply_to_session_id=A) -> B.session_id
      A launches B, then goes idle (no live container while it waits).
  resume_session(A.session_id, summary)          # B's callback when done
      A wakes with its FULL history intact + B's concise work-state summary.
  ask_agent(target, question) -> reply           # synchronous wait-for-reply
  approve(session_id, tool_use_id, allow, reason) # answer an always_ask pause

`context_ref` (a repo path like .fuze/handoff/<id>.md) is an alternative/companion
to the inline summary for large state: the callee persists state there and the
resumed agent reads the file itself.

Run (on the worker host / a small service):
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...            # server-side only
    python server.py                        # serves streamable-HTTP MCP
Then set HANDOFF_MCP_URL to this server's URL when syncing agents (roles/_base
declares it as an mcp_server so every role can hand off).
"""
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# reuse the REST helper + session driver from ../../sync (HANDOFF_SYNC_DIR overrides
# for the container image, where sync/ is copied to a fixed path).
SYNC = os.environ.get("HANDOFF_SYNC_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sync")
sys.path.insert(0, SYNC)
import common   # noqa: E402
import driver   # noqa: E402

STATE = common.state_dir()  # honors FUZE_STATE_DIR (mounted /state volume in the container)
HANDOFF_INSTRUCTIONS = ("Shared cross-session handoff workspace. Read relevant /handoff/*.md before "
                        "starting delegated work; persist your work-state under /handoff/<id>.md.")

mcp = FastMCP("fuze-handoff",
              host=os.environ.get("HOST", "0.0.0.0"),
              port=int(os.environ.get("PORT", "8000")))


def _roles():
    path = os.path.join(STATE, "agent-ids.json")
    if not os.path.exists(path):
        raise RuntimeError("agent-ids.json missing — run sync_agents.py first")
    return json.load(open(path, encoding="utf-8"))


def _vault_ids():
    path = os.path.join(STATE, "vault-ids.json")
    return list(json.load(open(path, encoding="utf-8")).values()) if os.path.exists(path) else []


def _memory_ids():
    path = os.path.join(STATE, "memory-ids.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def _memory_resources():
    return [driver.memory_resource(sid, "read_write", HANDOFF_INSTRUCTIONS) for sid in _memory_ids().values()]


def _handoff_store_id():
    ids = _memory_ids()
    if not ids:
        raise RuntimeError("no memory store synced — run sync_memory.py first")
    return next(iter(ids.values()))


def _new_session(role):
    roles = _roles()
    if role not in roles:
        raise RuntimeError(f"unknown role '{role}'. Known: {', '.join(roles)}")
    e = roles[role]
    s = driver.create_session(e["id"], e["version"], e["environment_id"],
                              vault_ids=_vault_ids(), resources=_memory_resources(),
                              title=f"handoff:{role}")
    return s["id"]


def _callback_instructions(reply_to, context_ref):
    parts = []
    if reply_to:
        parts.append(
            f"When you finish, hand back by calling resume_session(session_id='{reply_to}', "
            f"summary=<concise work-state>). Send ONLY a concise state summary — never paste your "
            f"transcript; the originating session already holds its full history."
        )
    if context_ref:
        parts.append(f"Persist any larger state to '{context_ref}' and reference it in your summary "
                     f"(a repo path, or a memory path under the mounted handoff store).")
    if reply_to:
        parts.append("For durable/large state prefer the shared handoff memory store (mounted in this "
                     "session, or via the memory_write tool) over inlining — pass only the path back.")
    return ("\n\n" + "\n".join(parts)) if parts else ""


@mcp.tool()
def spawn_agent(role: str, task: str, reply_to_session_id: str = "", context_ref: str = "", wait: bool = False) -> str:
    """Launch a role agent in its own session/environment with a compact task.

    role: frontend|backend|qa|devops (or any synced role/coordinator).
    task: the work to do — a concise instruction, not a pasted transcript.
    reply_to_session_id: if set, the spawned agent is told to resume_session() back
        to this (the caller's) session when done, passing a summary.
    context_ref: optional repo path holding larger persisted state to read/append.
    wait: if true, run to the next stop and return {session_id, status, reply|pending}.
          if false, fire-and-forget; returns {session_id, status:"spawned"}.
    """
    sid = _new_session(role)
    prompt = task + _callback_instructions(reply_to_session_id, context_ref)
    if not wait:
        driver.send_message(sid, prompt)
        return json.dumps({"session_id": sid, "status": "spawned"})
    res = driver.run_until_block(sid, prompt)
    return json.dumps({"session_id": sid, "status": res["status"],
                       "reply": res["text"], "pending": res["pending"]})


@mcp.tool()
def resume_session(session_id: str, summary: str, context_ref: str = "") -> str:
    """Wake an existing (originating) session with a concise work-state summary.

    The session's full history and sandbox state are intact server-side — this only
    delivers your summary (plus an optional repo file pointer). Use this to hand work
    BACK to whoever spawned you.
    """
    msg = f"[handoff:resume] {summary}"
    if context_ref:
        msg += f"\n\nPersisted state: {context_ref} (read it for details)."
    driver.send_message(session_id, msg)
    return json.dumps({"resumed": session_id})


@mcp.tool()
def ask_agent(target: str, question: str) -> str:
    """Synchronous wait-for-reply. target = a role name (spawns a fresh session) OR
    an existing session id (continues it). Returns the agent's reply text, or a
    'blocked' status if it paused for an approval (answer via approve())."""
    sid = _new_session(target) if target in _roles() else target
    res = driver.run_until_block(sid, question)
    return json.dumps({"session_id": sid, "status": res["status"],
                       "reply": res["text"], "pending": res["pending"]})


@mcp.tool()
def approve(session_id: str, tool_use_id: str, allow: bool = True, reason: str = "") -> str:
    """Answer an always_ask pause in a spawned/continued session (e.g. a prod-affecting
    devops action). Deny with a reason to steer the agent instead of blocking it."""
    driver.confirm_tool(session_id, tool_use_id, allow=allow, deny_message=reason or None)
    return json.dumps({"session_id": session_id, "tool_use_id": tool_use_id, "result": "allow" if allow else "deny"})


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


def _vault_id_by_name(name):
    path = os.path.join(STATE, "vault-ids.json")
    ids = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    return ids.get(name)


@mcp.tool()
def reach_human(human: str, message: str, reply_to_session_id: str = "", channels: str = "", wait: bool = False) -> str:
    """Reach a real human through their digital persona and relay their answer back.

    Spawns the `digital-persona` agent bound to this human's vault (their channel
    credentials: email/Slack/GitHub/WhatsApp/Telegram/phone) and tells it to contact
    the human with `message`, collect their ACTUAL reply, and — if reply_to_session_id
    is set — resume_session() that session with the human's answer. Use this instead of
    stalling when a session needs a human's decision or approval.

    human: person key (matches vault 'persona-<human>' + the persona's metadata).
    channels: comma list to prefer (e.g. "slack,email"); empty = their preferred.
    wait: if true, block until the persona reports (reply|blocked|pending); else fire-and-forget
          (the persona resumes the origin session itself when the human replies).
    """
    roles = _roles()
    if "digital-persona" not in roles:
        raise RuntimeError("digital-persona agent not provisioned — run providers/provision.py")
    e = roles["digital-persona"]
    vid = _vault_id_by_name(f"persona-{human}")
    if not vid:
        raise RuntimeError(f"no vault 'persona-{human}' — create vaults/persona-{human}.json and provision it")
    sid = driver.create_session(e["id"], e["version"], e["environment_id"],
                                vault_ids=[vid], resources=_memory_resources(),
                                title=f"persona:{human}")["id"]
    ch = f" via {channels}" if channels else " via their preferred channel"
    prompt = (f"You represent {human}. Reach the real {human}{ch} with the following, collect their "
              f"ACTUAL reply (never fabricate a binding answer), and report it.\n\nMESSAGE:\n{message}")
    if reply_to_session_id:
        prompt += (f"\n\nWhen you have their real answer, call resume_session(session_id='{reply_to_session_id}', "
                   f"summary=<their verbatim answer + your read>). If you cannot reach them, resume with 'BLOCKED: ...'.")
    if not wait:
        driver.send_message(sid, prompt)
        return json.dumps({"session_id": sid, "human": human, "status": "reaching"})
    res = driver.run_until_block(sid, prompt)
    return json.dumps({"session_id": sid, "human": human, "status": res["status"],
                       "reply": res["text"], "pending": res["pending"]})


def build_app():
    """Streamable-HTTP MCP app, gated by a bearer token when HANDOFF_MCP_TOKEN is set.

    This server creates sessions with our ANTHROPIC_API_KEY, so it must not be open.
    Managed Agents connect server-to-server and present the token as a vault-injected
    `Authorization: Bearer` credential (keyed to the handoff MCP url). In prod the
    Cloudflare Access email-OTP wildcard is bypassed for this hostname (a more-specific
    Access app), so this app-level bearer is the gate.
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
