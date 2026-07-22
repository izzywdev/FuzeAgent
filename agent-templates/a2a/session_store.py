"""The task store — a REFLECTION of provider sessions, not a task engine.

state-mapping.md §1/§7 is emphatic: ``Task.id`` IS the session id and the adapter MUST
NOT persist its own task table that duplicates state. This store therefore holds only:

  * caller OWNERSHIP (so ``ListTasks``/``GetTask`` can scope to the caller and so
    other-caller tasks are indistinguishable from unknown ones — authz.md §6), and
  * a CACHED snapshot of the last ``Task`` the provider result mapped to, because the
    ``AgentProvider`` seam exposes no "query current session state" primitive — the
    only status a session reports is what ``run_until_block`` returned. The snapshot is
    a reflection of that result; the adapter never invents a transition.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class SessionRecord:
    session_id: str
    caller: str
    tenant: str
    context_id: str
    #: latest Task snapshot as a wire dict (reflection of the last provider result).
    task: dict | None = None
    terminal: bool = False
    #: tool_use_id of an outstanding always_ask pause, for confirm_tool on continuation.
    pending_tool_use_id: str | None = None


class SessionStore:
    def __init__(self) -> None:
        self._by_id: dict[str, SessionRecord] = {}
        self._lock = threading.RLock()

    def create(self, session_id: str, caller: str, tenant: str, context_id: str) -> SessionRecord:
        with self._lock:
            rec = SessionRecord(session_id, caller, tenant, context_id)
            self._by_id[session_id] = rec
            return rec

    def get(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self._by_id.get(session_id)

    def owned(self, session_id: str, caller: str) -> SessionRecord | None:
        """Return the record only if ``caller`` owns it — else None (no oracle)."""
        rec = self.get(session_id)
        if rec is None or rec.caller != caller:
            return None
        return rec

    def update(
        self, session_id: str, *, task: dict, terminal: bool, pending_tool_use_id=None
    ) -> None:
        with self._lock:
            rec = self._by_id.get(session_id)
            if rec is None:
                return
            rec.task = task
            rec.terminal = terminal
            rec.pending_tool_use_id = pending_tool_use_id

    def list_for(self, caller: str, tenant: str | None = None) -> list[SessionRecord]:
        with self._lock:
            return [
                r
                for r in self._by_id.values()
                if r.caller == caller and (tenant is None or r.tenant == tenant)
            ]
