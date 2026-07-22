"""Echo provider — a deterministic, self-contained ``AgentProvider`` for the
Phase-3 A2A acceptance gate.

It stands in for the Managed-Agents runtime BELOW the ``providers/base.py`` seam so a
real A2A server (transport + adapter + card projection + callee-enforced authZ) can be
exercised end-to-end in CI without any external agent backend. It returns the
``{'text','status','pending'}`` shape ``AgentProvider.run_until_block`` promises, and
drives exactly the state-machine transitions the acceptance suite grades:

* an ``always_ask``/bulk goal pauses in a decision pause (-> INPUT_REQUIRED) with an
  explanatory message, and resolves to COMPLETED once confirmed;
* a ``reach_human`` escalation pauses with an explanatory message;
* a long/background goal blocks long enough to be cancelled (-> CANCELED);
* everything else completes immediately (-> COMPLETED).

To exercise the ARTIFACT CHANNEL end-to-end in CI it returns a single generic
``echo-output`` artifact on an ordinary completion (state-mapping.md §6: idle ->
structured outputs -> Artifacts). That artifact only echoes the caller's own request;
it deliberately does NOT fabricate cross-product side effects (e.g. Jira tickets):
the pending descriptors carry no credential/auth signals, and no domain content is
invented. The motivating cross-product ticket-creation acceptance needs a REAL
FuzePlan agent holding real Atlassian credentials and is a STAGING gate, not pure CI.

NOT FOR PRODUCTION. Selected only via ``AGENT_PROVIDER=echo``.
"""
from __future__ import annotations

import threading
import time

from providers.base import AgentProvider

# Prompt cues -> scripted transition. Substring match on the lowercased prompt.
_ALWAYS_ASK_CUES = ("bulk", "50 jira", "50 tickets", "delete", "wipe", "drop all")
_REACH_HUMAN_CUES = ("escalate", "human sign-off", "human sign off", "sign-off", "reach a human")
_LONG_CUES = ("long", "draft", "grooming", "backlog grooming")

# How long a background/long task blocks so a concurrent CancelTask reliably wins the
# race (the foreground SendMessage returns SUBMITTED immediately; this runs in a thread).
_LONG_BLOCK_SECONDS = 12.0


class _Session:
    __slots__ = ("confirmed", "archived", "cue")

    def __init__(self) -> None:
        self.confirmed = False
        self.archived = threading.Event()
        self.cue: str | None = None


def _matches(text: str, cues) -> bool:
    return any(cue in text for cue in cues)


class EchoProvider(AgentProvider):
    name = "echo"
    capabilities = {"self_hosted": True, "vaults": False, "memory": False, "multiagent": False}

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()
        self._n = 0

    # ---- provisioning -------------------------------------------------------
    def ensure_environment(self, manifest):
        return {"name": "echo-env", "id": "echo-env-1"}

    def ensure_agent(self, manifest, multiagent=None):
        role = (manifest or {}).get("role", "echo")
        return {"name": role, "id": f"echo-agent-{role}", "version": "1", "environment_id": "echo-env-1"}

    # ---- runtime ------------------------------------------------------------
    def create_session(
        self, agent_id, version, environment_id, vault_ids=None, memory_resources=None, title=None
    ):
        with self._lock:
            self._n += 1
            sid = f"echo-sess-{self._n:06d}"
            self._sessions[sid] = _Session()
        return sid

    def _session(self, session_id) -> _Session:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                sess = self._sessions[session_id] = _Session()
            return sess

    def run_until_block(self, session_id, prompt=None):
        sess = self._session(session_id)
        text = (prompt or "").strip()
        low = text.lower()

        # Continuation turn (no new prompt): the caller has answered a pause. If it was
        # an always_ask decision pause and got confirmed, complete; otherwise complete.
        if not text:
            return self._completed("Confirmed. Work completed." if sess.confirmed else "Done.")

        # always_ask / bulk guardrail -> INPUT_REQUIRED (decision pause). No auth/
        # credential words in the descriptor, so task_mapper classifies it as
        # INPUT_REQUIRED (an ordinary decision), never AUTH_REQUIRED.
        if not sess.confirmed and _matches(low, _ALWAYS_ASK_CUES):
            sess.cue = "always_ask"
            return {
                "text": (
                    "This is a bulk/irreversible action. Confirm before I proceed, "
                    "and tell me the intended scope."
                ),
                "status": "blocked",
                "pending": {
                    # NB: the descriptor must carry NO credential/auth words (see
                    # task_mapper._AUTH_SIGNALS — "scope","token", etc.) or the pause
                    # would misclassify as AUTH_REQUIRED instead of INPUT_REQUIRED.
                    "event_ids": ["echo-decision-1"],
                    "tools": {"echo-decision-1": "confirm_bulk_action(count=requested)"},
                },
            }

        # reach_human escalation -> INPUT_REQUIRED, addressed to a human. Still carries
        # an explanatory message so the caller can tell it is not its own obligation.
        if _matches(low, _REACH_HUMAN_CUES):
            sess.cue = "reach_human"
            return {
                "text": (
                    "Paused for human sign-off. A human approver has been reached via "
                    "their digital persona; no action is required from you."
                ),
                "status": "blocked",
                "pending": {
                    "event_ids": ["echo-human-1"],
                    "tools": {"echo-human-1": "await_human_decision(reason=policy)"},
                },
            }

        # long / background goal -> block so a concurrent cancel wins, then complete.
        if _matches(low, _LONG_CUES):
            sess.archived.wait(timeout=_LONG_BLOCK_SECONDS)
            if sess.archived.is_set():
                # Cancelled out from under us; surface a terminal-ish idle. The adapter
                # has already written CANCELED via archive_session.
                return self._completed("Cancelled.")
            return self._completed("Long task completed.")

        # ordinary goal -> COMPLETED immediately, WITH a representative artifact so the
        # artifact channel (provider -> adapter -> task_mapper -> Task.artifacts) is
        # exercisable in CI. Generic echo only; no fabricated tickets/side effects.
        echoed = text[:280]
        return self._completed(
            f"Echo: {echoed}",
            artifacts=[
                {
                    "name": "echo-output",
                    "description": "Deterministic echo of the caller's request (channel probe).",
                    "parts": [
                        {"text": f"Echo: {echoed}"},
                        {"data": {"echoed": echoed, "provider": "echo"}},
                    ],
                }
            ],
        )

    @staticmethod
    def _completed(text: str, artifacts: list[dict] | None = None) -> dict:
        result: dict = {"text": text, "status": "idle", "pending": None}
        if artifacts:
            result["artifacts"] = artifacts
        return result

    def confirm_tool(self, session_id, tool_use_id, allow=True, deny_message=None):
        sess = self._session(session_id)
        sess.confirmed = bool(allow)

    def resume_session(self, session_id, summary, context_ref=""):
        # A plain resume (no pending tool) is treated as confirmation to proceed.
        self._session(session_id).confirmed = True

    def archive_session(self, session_id):
        self._session(session_id).archived.set()

    # ---- unused abstract surface (never called by the A2A adapter) ----------
    def send_message(self, session_id, text):  # pragma: no cover
        return None

    def run_turn(self, session_id, prompt, approver, echo=True):  # pragma: no cover
        return self.run_until_block(session_id, prompt).get("text", "")
