"""Map Managed-Agents runtime results to A2A wire objects (state-mapping.md §3).

THE CORE TABLE. This module is the entire reason the A2A pod is called an *adapter*:
it translates the ``{'text','status','pending'}`` returned by
``AgentProvider.run_until_block`` into an A2A ``Task``. It holds no state and drives
no execution — if you are adding a scheduler or a transcript store here, you have
missed state-mapping.md.

    provider status   A2A TaskState
    ---------------   -----------------------------
    idle              TASK_STATE_COMPLETED   (terminal)
    error             TASK_STATE_FAILED      (terminal)
    blocked + tool    TASK_STATE_INPUT_REQUIRED  (interrupted)
    blocked + cred    TASK_STATE_AUTH_REQUIRED   (interrupted)

``TASK_STATE_UNSPECIFIED`` MUST never be emitted.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ._contract import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

__all__ = [
    "Artifact",
    "Message",
    "Part",
    "Role",
    "Task",
    "TaskArtifactUpdateEvent",
    "TaskState",
    "TaskStatus",
    "TaskStatusUpdateEvent",
    "now_iso",
    "agent_message",
    "classify_pause",
    "pending_tool_use_id",
    "map_result",
    "submitted_task",
    "working_status",
    "rejected_task",
    "canceled_task",
]

# Signals in a pending tool descriptor that mark a pause as a CREDENTIAL / AUTH grant
# request rather than an ordinary decision. Discriminating these two is the most
# likely adapter bug (state-mapping.md §3), so the rule is explicit and testable.
# No word boundaries: tool descriptors glue words with underscores (``oauth_authorize``,
# ``get_api_key``, ``use_token``), where ``\b`` would not fire. Substring match is the
# right granularity for the ``name(input)`` descriptor shape the driver produces.
_AUTH_SIGNALS = re.compile(
    r"(credential|auth|oauth|token|api[_-]?key|apikey|secret|vault|"
    r"login|sign[_-]?in|access[_-]?grant|scope)",
    re.IGNORECASE,
)


def now_iso() -> str:
    """ISO 8601, UTC, ``Z`` suffix (binding.md)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def agent_message(
    text: str, *, context_id: str | None = None, task_id: str | None = None
) -> Message:
    """An agent-role Message carrying a single text part."""
    return Message(
        messageId=str(uuid.uuid4()),
        role=Role.ROLE_AGENT,
        parts=[Part(root={"text": text or ""})],
        contextId=context_id,
        taskId=task_id,
    )


# --------------------------------------------------------------------------- #
# pause classification (state-mapping.md §3/§4)
# --------------------------------------------------------------------------- #
def _pending_descriptions(pending: dict | None) -> list[str]:
    if not pending:
        return []
    tools = pending.get("tools") or {}
    return [str(v) for v in tools.values()]


def classify_pause(pending: dict | None) -> TaskState:
    """A ``blocked`` pause is AUTH_REQUIRED iff what is missing is a credential/grant;
    otherwise it is the ordinary ``always_ask`` decision pause -> INPUT_REQUIRED.

    We branch on the ``pending`` payload (never on the status string alone), per
    state-mapping.md §3. The default is INPUT_REQUIRED — the common case.
    """
    for desc in _pending_descriptions(pending):
        if _AUTH_SIGNALS.search(desc):
            return TaskState.TASK_STATE_AUTH_REQUIRED
    return TaskState.TASK_STATE_INPUT_REQUIRED


def pending_tool_use_id(pending: dict | None) -> str | None:
    """The tool_use_id the caller's reply resolves via ``confirm_tool`` (state-mapping §4)."""
    if not pending:
        return None
    ids = pending.get("event_ids") or []
    if ids:
        return ids[0]
    tools = pending.get("tools") or {}
    return next(iter(tools), None)


def _pause_reason(pending: dict | None, text: str) -> str:
    """Human-facing 'what is being asked and why' — REQUIRED for INPUT/AUTH_REQUIRED.

    Prefers the agent's own text (it explains the ask); falls back to the pending tool
    descriptor so a pause is never uninterpretable (a pause a caller cannot read is a
    hang, state-mapping.md §4).
    """
    if text and text.strip():
        return text.strip()
    descs = _pending_descriptions(pending)
    if descs:
        return "Awaiting approval for: " + "; ".join(descs)
    return "The agent is waiting on input or authorization to continue."


# --------------------------------------------------------------------------- #
# terminal / interrupted task construction
# --------------------------------------------------------------------------- #
def _status(state: TaskState, message: Message | None = None) -> TaskStatus:
    return TaskStatus(state=state, message=message, timestamp=now_iso())


def map_result(
    result: dict[str, Any],
    *,
    session_id: str,
    context_id: str,
    artifacts: list[Artifact] | None = None,
) -> Task:
    """Map a ``run_until_block`` result onto a settled/interrupted ``Task``.

    ``Task.id`` IS the session id (state-mapping.md §1); no side table.
    """
    status = result.get("status")
    text = result.get("text", "") or ""
    pending = result.get("pending")

    if status == "idle":
        state = TaskState.TASK_STATE_COMPLETED
        message = agent_message(text, context_id=context_id, task_id=session_id) if text else None
    elif status == "error":
        state = TaskState.TASK_STATE_FAILED
        message = agent_message(
            text or "The task failed.", context_id=context_id, task_id=session_id
        )
    elif status == "blocked":
        state = classify_pause(pending)
        message = agent_message(
            _pause_reason(pending, text), context_id=context_id, task_id=session_id
        )
    else:  # pragma: no cover - guarded upstream; never emit UNSPECIFIED
        raise ValueError(f"unmappable provider status {status!r}")

    return Task(
        id=session_id,
        contextId=context_id,
        status=_status(state, message),
        artifacts=artifacts or None,
    )


def submitted_task(session_id: str, context_id: str) -> Task:
    """Pre-dispatch resting state for ``returnImmediately: true`` (state-mapping §2)."""
    return Task(id=session_id, contextId=context_id, status=_status(TaskState.TASK_STATE_SUBMITTED))


def working_status(session_id: str, context_id: str) -> TaskStatus:
    """Emitted on the stream while dispatched; not a resting state."""
    return _status(TaskState.TASK_STATE_WORKING)


def rejected_task(session_id: str, context_id: str) -> Task:
    """Terminal REJECTED with a GENERIC message (authz.md §6 non-disclosure)."""
    return Task(
        id=session_id,
        contextId=context_id,
        status=_status(
            TaskState.TASK_STATE_REJECTED,
            agent_message("Not authorized.", context_id=context_id, task_id=session_id),
        ),
    )


def canceled_task(session_id: str, context_id: str) -> Task:
    return Task(id=session_id, contextId=context_id, status=_status(TaskState.TASK_STATE_CANCELED))
