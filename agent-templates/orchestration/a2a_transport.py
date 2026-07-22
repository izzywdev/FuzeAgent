#!/usr/bin/env python3
"""A2A transport for the handoff orchestration layer (CLIENT side).

This is the thin adapter that lets the handoff MCP (`handoff_mcp/server.py`) and the
relay chain (`relay.py`) reach another product/exec agent **over the A2A wire**
instead of driving a Managed-Agents session directly. The calling agent holds NO
domain tools or skills of the callee — it discovers the callee's Agent Card and
hands over a goal. That is the whole point of A2A (card-projection.md §7).

It re-uses the FROZEN generated client under
`agent-templates/contracts/a2a/v1/client/fuze_a2a_client` and hand-rolls NOTHING on
the wire: discovery, the JSON-RPC envelope, SSE framing and the typed errors all
live in that package. This module only:

  1. resolves a *target key* (a product/exec identity, or a persona) to a discovery
     URL + skill id, and fetches its Agent Card at the well-known path,
  2. issues `SendMessage` / `GetTask` / `CancelTask` through the generated client,
  3. maps the returned A2A ``Task`` onto the legacy ``{session_id, status, reply,
     pending}`` shape the existing MCP tools already return — so tool signatures and
     return shapes stay UNCHANGED (state-mapping.md §3).

Nothing here implements a task engine, a retry loop or a state machine — those live
on the callee, below the A2A seam (state-mapping.md, top).

Configuration (all optional; sensible in-cluster defaults):

  A2A_TOKEN                OIDC bearer presented on every call (held server-side,
                           never in an agent sandbox — like ANTHROPIC_API_KEY).
  A2A_TARGETS              JSON object mapping target key -> spec (see TargetSpec).
                           Alternatively a file `<state>/a2a-targets.json`.
  A2A_DISCOVERY_DOMAIN     in-cluster DNS domain for per-tenant discovery Services
                           (default: fuzeagent.svc.cluster.local).
  A2A_DISCOVERY_PORT       discovery port (default: 8080).
  A2A_DISCOVERY_SCHEME     http (in-cluster default) or https (external).
  A2A_PERSONA_PREFIX       target-key prefix used by reach_human (default: persona-).
  A2A_DEFAULT_TARGET       fallback target key used to resolve a continuation whose
                           task id is not in the in-process cache (e.g. after a
                           restart). Optional.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from typing import Any

# -- make the FROZEN generated client importable ----------------------------
# Prefer an installed `fuze_a2a_client`; otherwise add the in-repo client dir to
# sys.path. A2A_CLIENT_DIR overrides the location for the container image.
_CLIENT_DIR = os.environ.get("A2A_CLIENT_DIR")
if not _CLIENT_DIR:
    _here = os.path.dirname(os.path.abspath(__file__))                 # orchestration/
    _templates_root = os.path.dirname(_here)                           # agent-templates/
    _CLIENT_DIR = os.path.join(_templates_root, "contracts", "a2a", "v1", "client")
if os.path.isdir(_CLIENT_DIR) and _CLIENT_DIR not in sys.path:
    sys.path.insert(0, _CLIENT_DIR)

from fuze_a2a_client import (  # noqa: E402
    A2AClient,
    AgentCard,
    A2AError,
    Task,
    TaskState,
)

# Legacy status strings the existing MCP tools already return (driver.run_until_block
# used idle|blocked|error). A2A adds terminal REJECTED and the transient submitted/
# working states, which are strictly more information for the caller.
_STATUS_BY_STATE: dict[TaskState, str] = {
    TaskState.TASK_STATE_COMPLETED: "idle",
    TaskState.TASK_STATE_FAILED: "error",
    TaskState.TASK_STATE_CANCELED: "canceled",
    TaskState.TASK_STATE_REJECTED: "rejected",
    TaskState.TASK_STATE_INPUT_REQUIRED: "blocked",
    TaskState.TASK_STATE_AUTH_REQUIRED: "blocked",
    TaskState.TASK_STATE_SUBMITTED: "submitted",
    TaskState.TASK_STATE_WORKING: "working",
}


# ---------------------------------------------------------------------------
# Target resolution + discovery
# ---------------------------------------------------------------------------
class TargetSpec:
    """How to reach one A2A target.

    A spec resolves to a *discovery URL* (where the Agent Card is served at the
    well-known path) and a *skill id* (which capability to invoke). The card itself
    supplies the RPC url, tenant and protocol binding — we never assume them.
    """

    __slots__ = ("key", "discovery_url", "skill_id", "tenant", "token")

    def __init__(self, key: str, discovery_url: str, skill_id: str | None,
                 tenant: str | None = None, token: str | None = None):
        self.key = key
        self.discovery_url = discovery_url
        self.skill_id = skill_id
        self.tenant = tenant
        self.token = token


def _registry() -> dict[str, dict]:
    """Target registry from A2A_TARGETS (JSON) or `<state>/a2a-targets.json`."""
    raw = os.environ.get("A2A_TARGETS")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"A2A_TARGETS is not valid JSON: {exc}") from exc
    state = os.environ.get("FUZE_STATE_DIR")
    if state:
        path = os.path.join(state, "a2a-targets.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    return {}


def _tenant_slug(name: str) -> str:
    """DNS label for a tenant's discovery Service. `Exec-cto` -> `exec-cto`."""
    return name.strip().lower().replace("_", "-")


def _convention_discovery_url(tenant: str) -> str:
    scheme = os.environ.get("A2A_DISCOVERY_SCHEME", "http")
    domain = os.environ.get("A2A_DISCOVERY_DOMAIN", "fuzeagent.svc.cluster.local")
    port = os.environ.get("A2A_DISCOVERY_PORT", "8080")
    host = f"a2a-{_tenant_slug(tenant)}.{domain}"
    return f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"


def resolve_target(target: str) -> TargetSpec:
    """Resolve a target key to a TargetSpec.

    Order: explicit registry entry, then convention. A registry entry may set any of
    ``discovery_url``, ``skill_id``, ``tenant`` (asserted against the card), ``token``.
    The convention treats the key as the tenant, discovers it at its own per-tenant
    in-cluster Service, and uses the key as the skill id.
    """
    reg = _registry().get(target, {})
    tenant = reg.get("tenant", target)
    discovery_url = reg.get("discovery_url") or _convention_discovery_url(tenant)
    skill_id = reg.get("skill_id", target)
    token = reg.get("token") or os.environ.get("A2A_TOKEN")
    return TargetSpec(target, discovery_url, skill_id, tenant=tenant, token=token)


# ---------------------------------------------------------------------------
# Client cache + task -> client mapping (so continuations know their tenant)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_clients: dict[str, A2AClient] = {}          # target key -> client
_task_target: dict[str, str] = {}            # task/session id -> target key


def get_client(target: str) -> A2AClient:
    """Fetch the target's Agent Card (well-known path) and build a cached client.

    Discovery is a plain unauthenticated GET; the returned card carries the RPC url,
    tenant and JSONRPC binding, which the generated client validates on construction.
    """
    with _lock:
        cached = _clients.get(target)
        if cached is not None:
            return cached
    spec = resolve_target(target)
    card: AgentCard = A2AClient.fetch_card(spec.discovery_url)
    if spec.tenant and card.supportedInterfaces[0].tenant not in (None, spec.tenant):
        raise RuntimeError(
            f"target '{target}' resolved to card tenant "
            f"{card.supportedInterfaces[0].tenant!r}, expected {spec.tenant!r}"
        )
    client = A2AClient(card, token=spec.token)
    with _lock:
        _clients[target] = client
    return client


def _client_for_task(task_id: str, target_hint: str | None = None) -> A2AClient:
    """Resolve the client that owns an existing task/session id (for continuations)."""
    with _lock:
        key = _task_target.get(task_id)
    if key:
        return get_client(key)
    if target_hint:
        return get_client(target_hint)
    default = os.environ.get("A2A_DEFAULT_TARGET")
    if default:
        return get_client(default)
    raise RuntimeError(
        f"no A2A client is bound to task '{task_id}'. Continuations must reuse the "
        f"target that created the task; set A2A_DEFAULT_TARGET or pass a target hint."
    )


def _remember(task_id: str, target: str) -> None:
    if task_id:
        with _lock:
            _task_target[task_id] = target


# ---------------------------------------------------------------------------
# Task -> legacy shape mapping
# ---------------------------------------------------------------------------
def _part_text(part: Any) -> str:
    """Text of a wire Part (RootModel[Part1|..]). Non-text parts contribute nothing."""
    root = getattr(part, "root", part)
    txt = getattr(root, "text", None)
    return txt or ""


def _message_text(message: Any) -> str:
    if message is None:
        return ""
    return "".join(_part_text(p) for p in (message.parts or []))


def _final_text(task: Task) -> str:
    """Caller-facing text for a settled/interrupted task.

    For a terminal task the final agent Message is the answer; state-mapping.md §3
    routes COMPLETED text to the final agent Message and FAILED/interrupted text to
    ``TaskStatus.message``. Prefer the status message (always the freshest, and the
    REQUIRED explanation for INPUT_REQUIRED/AUTH_REQUIRED), then the last message in
    history, then any text artifact.
    """
    status_txt = _message_text(task.status.message) if task.status else ""
    if status_txt:
        return status_txt
    if task.history:
        for msg in reversed(task.history):
            txt = _message_text(msg)
            if txt:
                return txt
    for artifact in (task.artifacts or []):
        txt = "".join(_part_text(p) for p in (artifact.parts or []))
        if txt:
            return txt
    return ""


def task_to_legacy(task: Task) -> dict:
    """Map an A2A Task onto ``{session_id, status, reply, pending}``.

    ``session_id`` IS ``Task.id`` (state-mapping.md §1) so the existing tool return
    shape is preserved verbatim. ``pending`` is populated only for the interrupted
    states, and carries the REQUIRED ``TaskStatus.message`` so the caller can decide
    whether the pause is addressed to it or to a human it cannot see
    (state-mapping.md §4) — the latter is resolved via ``reach_human``.
    """
    state = task.status.state
    status = _STATUS_BY_STATE.get(state, "working")
    reply = _final_text(task)
    pending = None
    if state in (TaskState.TASK_STATE_INPUT_REQUIRED, TaskState.TASK_STATE_AUTH_REQUIRED):
        pending = {
            "state": str(state),
            "kind": "auth" if state == TaskState.TASK_STATE_AUTH_REQUIRED else "input",
            "task_id": task.id,
            "message": reply,
            # A caller MUST read `message` before assuming the pause is its own; some
            # pauses are addressed to a human via reach_human (state-mapping.md §4).
            "needs_human": None,
        }
    return {"session_id": task.id, "status": status, "reply": reply, "pending": pending}


# ---------------------------------------------------------------------------
# Public operations used by the MCP tools and the relay
# ---------------------------------------------------------------------------
def start(target: str, text: str, *, skill_id: str | None = None,
          return_immediately: bool = False) -> dict:
    """Start a NEW task on a target agent (no taskId). Returns the legacy shape."""
    spec = resolve_target(target)
    client = get_client(target)
    task = client.send_message(
        text,
        skill_id=skill_id or spec.skill_id,
        return_immediately=return_immediately,
    )
    task = _as_task(task)
    _remember(task.id, target)
    return task_to_legacy(task)


def continue_task(task_id: str, text: str, *, target_hint: str | None = None) -> dict:
    """Continue an EXISTING task (send_message with taskId). This is the wire form of
    answering an interrupted task, resuming, or approving — the callee resumes its own
    session and never replays a transcript (state-mapping.md §1, §4)."""
    client = _client_for_task(task_id, target_hint)
    task = _as_task(client.send_message(text, task_id=task_id))
    _remember(task.id, target_hint or _task_target.get(task_id, ""))
    return task_to_legacy(task)


def get_task(task_id: str, *, target_hint: str | None = None,
             history_length: int | None = None) -> dict:
    client = _client_for_task(task_id, target_hint)
    return task_to_legacy(client.get_task(task_id, history_length=history_length))


def cancel_task(task_id: str, *, target_hint: str | None = None) -> dict:
    """CancelTask -> archive_session on the callee (state-mapping.md §5)."""
    client = _client_for_task(task_id, target_hint)
    return task_to_legacy(client.cancel_task(task_id))


def _as_task(result: Any) -> Task:
    """`A2AClient.send_message` returns a Task, or a raw dict for the message-only
    response variant. Normalise to a Task (validating the wire shape)."""
    if isinstance(result, Task):
        return result
    if isinstance(result, dict) and "task" in result:
        return Task.model_validate(result["task"])
    raise A2AError(f"A2A response carried no Task: {result!r}", code=-32006)


__all__ = [
    "TargetSpec",
    "resolve_target",
    "get_client",
    "task_to_legacy",
    "start",
    "continue_task",
    "get_task",
    "cancel_task",
    "A2AError",
]
