"""Typed A2A client for the Fuze family (contract v1).

This is the CALLER side. It is deliberately thin: discovery, a JSON-RPC envelope,
SSE framing, and typed errors. It contains no agent logic, no task engine, and no
provider knowledge — all of that lives on the callee, which is the entire point of
A2A (see ../../card-projection.md §7).

Frozen against A2A specification 1.0.0 (lf.a2a.v1). Binding: JSON-RPC 2.0 over
HTTP + SSE. See ../../binding.md.

Transport is injected (`transport=`) so the same client drives the real server, the
Prism mock (../../mock/), or a test double. The default transport requires `httpx`;
importing this module without httpx is fine as long as a transport is supplied.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Iterator, Protocol

from .card_models import FuzeA2AAgentCard as AgentCard
from .errors import from_json_rpc_error
from .wire_models import (
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    Task,
    TaskState,
)

A2A_VERSION = "1.0"
WELL_KNOWN_CARD_PATH = "/.well-known/agent-card.json"

#: Task states from which no further transition occurs (spec 1.0.0 §4.1.2).
TERMINAL_STATES: frozenset[TaskState] = frozenset(
    {
        TaskState.TASK_STATE_COMPLETED,
        TaskState.TASK_STATE_FAILED,
        TaskState.TASK_STATE_CANCELED,
        TaskState.TASK_STATE_REJECTED,
    }
)

#: States where the task is alive but waiting on someone. NOT necessarily on *you* —
#: the callee may be waiting on a human via reach_human (state-mapping.md §4).
INTERRUPTED_STATES: frozenset[TaskState] = frozenset(
    {
        TaskState.TASK_STATE_INPUT_REQUIRED,
        TaskState.TASK_STATE_AUTH_REQUIRED,
    }
)


class Transport(Protocol):
    """Minimal HTTP seam so the client can be pointed at a mock."""

    def post(self, url: str, *, json: dict, headers: dict) -> Any: ...
    def get(self, url: str, *, headers: dict) -> Any: ...
    def stream(self, method: str, url: str, *, json: dict, headers: dict) -> Any: ...


class A2AClient:
    """Calls one A2A agent, identified by its Agent Card.

    Typical use — no tools of the callee's domain are needed here, only its card::

        card = A2AClient.fetch_card("http://a2a-shared.fuzeagent.svc.cluster.local:8080")
        client = A2AClient(card, token=my_oidc_token)
        task = client.send_message("Create Jira tickets for these requirements.",
                                   skill_id="product-manager")
    """

    def __init__(
        self,
        card: AgentCard,
        *,
        token: str | None = None,
        transport: Transport | None = None,
    ):
        self.card = card
        self._token = token
        iface = card.supportedInterfaces[0]
        if iface.protocolBinding != "JSONRPC":
            raise ValueError(
                f"contract v1 supports only the JSONRPC binding, card offers "
                f"{iface.protocolBinding!r} (binding.md §2)"
            )
        self.url = str(iface.url)
        self.tenant = iface.tenant
        self.protocol_version = iface.protocolVersion
        self._transport = transport or _default_transport()

    # -- discovery ----------------------------------------------------------
    @staticmethod
    def fetch_card(base_url: str, *, transport: Transport | None = None) -> AgentCard:
        """GET {base_url}/.well-known/agent-card.json (spec §8.2)."""
        t = transport or _default_transport()
        resp = t.get(base_url.rstrip("/") + WELL_KNOWN_CARD_PATH, headers={})
        return AgentCard.model_validate(resp.json())

    def fetch_extended_card(self) -> AgentCard:
        """Authenticated card. May expose more skills than the public one, and is
        computed per caller (authz.md §5)."""
        return AgentCard.model_validate(self._call("GetExtendedAgentCard", {}))

    # -- core methods -------------------------------------------------------
    def send_message(
        self,
        text: str,
        *,
        skill_id: str | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        return_immediately: bool = False,
    ) -> Task:
        """Send a goal. Omit `task_id` to start work; pass it to answer an
        interrupted task (the callee resumes its session — it never replays a
        transcript; state-mapping.md §1)."""
        params = self._message_params(
            text,
            skill_id=skill_id,
            task_id=task_id,
            context_id=context_id,
            return_immediately=return_immediately,
        )
        result = self._call("SendMessage", params)
        return Task.model_validate(result["task"]) if "task" in result else result

    def send_streaming_message(
        self,
        text: str,
        *,
        skill_id: str | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
    ) -> Iterator[dict]:
        """Same call as `send_message`, framed as SSE. Yields StreamResponse dicts."""
        params = self._message_params(
            text, skill_id=skill_id, task_id=task_id, context_id=context_id
        )
        yield from self._stream("SendStreamingMessage", params)

    def get_task(self, task_id: str, *, history_length: int | None = None) -> Task:
        params: dict[str, Any] = {"id": task_id, "tenant": self.tenant}
        if history_length is not None:
            params["historyLength"] = history_length
        return Task.model_validate(self._call("GetTask", params))

    def list_tasks(self, *, page_size: int | None = None, page_token: str | None = None) -> dict:
        """Only ever returns the caller's OWN tasks (state-mapping.md §5)."""
        params: dict[str, Any] = {"tenant": self.tenant}
        if page_size is not None:
            params["pageSize"] = page_size
        if page_token:
            params["pageToken"] = page_token
        return self._call("ListTasks", params)

    def cancel_task(self, task_id: str) -> Task:
        """Maps to archive_session on the callee."""
        return Task.model_validate(
            self._call("CancelTask", {"id": task_id, "tenant": self.tenant})
        )

    def subscribe_to_task(self, task_id: str) -> Iterator[dict]:
        """Re-attach to a live task's event stream. Raises UnsupportedOperationError
        (-32004) if the task is already terminal."""
        yield from self._stream("SubscribeToTask", {"id": task_id, "tenant": self.tenant})

    # -- helpers ------------------------------------------------------------
    def _message_params(
        self,
        text: str,
        *,
        skill_id: str | None,
        task_id: str | None,
        context_id: str | None,
        return_immediately: bool = False,
    ) -> dict:
        message = Message(
            messageId=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text=text)],
            taskId=task_id,
            contextId=context_id,
        )
        payload = message.model_dump(exclude_none=True, by_alias=True)
        if skill_id:
            # Skill selection travels as message metadata; the callee resolves it
            # against its own role manifests and is free to reject it.
            payload.setdefault("metadata", {})["skillId"] = skill_id
        params: dict[str, Any] = {"tenant": self.tenant, "message": payload}
        if return_immediately:
            params["configuration"] = SendMessageConfiguration(
                returnImmediately=True
            ).model_dump(exclude_none=True)
        return params

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "A2A-Version": A2A_VERSION}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _envelope(self, method: str, params: dict) -> dict:
        return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}

    def _call(self, method: str, params: dict) -> Any:
        resp = self._transport.post(self.url, json=self._envelope(method, params), headers=self._headers())
        body = resp.json()
        if "error" in body and body["error"] is not None:
            raise from_json_rpc_error(body["error"])
        return body.get("result")

    def _stream(self, method: str, params: dict) -> Iterator[dict]:
        with self._transport.stream(
            "POST", self.url, json=self._envelope(method, params), headers=self._headers()
        ) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line.startswith("data:"):
                    continue
                frame = json.loads(line[len("data:") :].strip())
                if "error" in frame and frame["error"] is not None:
                    raise from_json_rpc_error(frame["error"])
                yield frame.get("result", {})


def _default_transport() -> Transport:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "fuze_a2a_client's default transport needs httpx; install it or pass transport="
        ) from exc
    return httpx.Client(timeout=None)  # no timeout: exec escalations legitimately block on a human
