"""The A2A adapter — wire methods dispatched onto an ``AgentProvider``.

This is the translation layer and NOTHING more (state-mapping.md): A2A wire objects
in, provider calls out, provider results mapped back through ``task_mapper``. It owns
no scheduler, no retry loop, no transcript store — those live below the
``providers/base.py`` seam already.

The adapter is transport-agnostic: the Starlette ``server`` module handles HTTP/SSE and
credential validation, then calls these methods with an already-resolved, TRUSTED
``AuthContext``. Skill selection travels as ``message.metadata.skillId`` (routing, which
the callee may reject); it is NEVER trusted for authorization (authz.md §1).
"""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any, Callable, Iterator, Protocol

from . import card_generator as cg
from . import task_mapper as tm
from . import wire_errors as we
from .authz import AuthContext, Decision, authorize
from .config import ServerConfig, TenantConfig
from .session_store import SessionStore

#: Resolve a tenant's projection inputs (manifest, roles) from its git ref.
RepoResolver = Callable[[TenantConfig], "tuple[dict, dict]"]


class AgentProviderLike(Protocol):
    def ensure_agent(self, manifest, multiagent=None) -> dict: ...
    def create_session(
        self, agent_id, version, environment_id, vault_ids=None, memory_resources=None, title=None
    ) -> str: ...
    def run_until_block(self, session_id, prompt=None) -> dict: ...
    def confirm_tool(self, session_id, tool_use_id, allow=True, deny_message=None) -> None: ...
    def resume_session(self, session_id, summary, context_ref="") -> None: ...
    def archive_session(self, session_id) -> None: ...


def _dump(task) -> dict:
    return task.model_dump(mode="json", exclude_none=True, by_alias=True)


def _join_parts(parts: list[dict]) -> str:
    """Concatenate a message's parts into a prompt (state-mapping.md §6).

    ``text`` joined in order; ``data`` serialized as fenced JSON; ``url``/``raw`` inputs
    are rejected with ContentTypeNotSupportedError (-32005) — large state passes by
    reference through the handoff memory store, never inline.
    """
    chunks: list[str] = []
    for part in parts or []:
        if not isinstance(part, dict):
            continue
        if part.get("url") is not None or part.get("raw") is not None:
            raise we.with_info(
                we.ContentTypeNotSupportedError,
                "url/raw parts are not accepted on input in v1",
                "CONTENT_TYPE_NOT_SUPPORTED",
                {"note": "pass large state by reference via the handoff memory store"},
            )
        if part.get("text") is not None:
            chunks.append(str(part["text"]))
        elif part.get("data") is not None:
            chunks.append("```json\n" + json.dumps(part["data"], sort_keys=True) + "\n```")
    return "\n".join(chunks)


def _parse_decision(text: str) -> tuple[bool, str | None]:
    """A caller's reply to an always_ask pause -> (allow, deny_message)."""
    head = (text or "").strip().lower()
    if head.startswith(("deny", "no", "reject", "decline", "disallow")):
        return False, (text.strip() or "denied by caller")
    return True, None


class A2AAdapter:
    def __init__(
        self,
        config: ServerConfig,
        provider: AgentProviderLike,
        repo_resolver: RepoResolver,
        *,
        signer: cg.Signer | None = None,
    ):
        self.config = config
        self.provider = provider
        self.resolve_repo = repo_resolver
        self.signer = signer
        self.store = SessionStore()

    # ------------------------------------------------------------------ #
    # cards
    # ------------------------------------------------------------------ #
    def _tenant_or_none(self, tenant_name: str | None) -> TenantConfig | None:
        return self.config.tenant(tenant_name) if tenant_name else None

    def _issuer(self) -> str:
        return self.config.auth.oidc_issuer_url if self.config.auth else cg.DEFAULT_ISSUER

    def _card_for(self, tenant: TenantConfig, *, visibility: str) -> dict:
        manifest, roles = self.resolve_repo(tenant)
        # exec tenants (Exec-<role>) project a single exec role card
        if tenant.tenant.startswith("Exec-"):
            role_key = tenant.tenant[len("Exec-") :]
            role = roles.get(role_key)
            if role is None:
                raise we.task_not_found()
            return cg.project_exec_card(
                role_key, role, manifest, issuer_url=self._issuer(), signer=self.signer
            )
        return cg.project_product_card(
            manifest, roles, issuer_url=self._issuer(), visibility=visibility, signer=self.signer
        )

    def well_known_card(self, tenant_name: str) -> dict:
        """Public, unauthenticated card (only publish:true, non-extendedOnly skills)."""
        tenant = self._tenant_or_none(tenant_name)
        if tenant is None:
            raise we.task_not_found()
        return self._card_for(tenant, visibility="public")

    def extended_card(self, tenant_name: str, ctx: AuthContext) -> dict:
        """Authenticated extended card, computed per caller (authz.md §5)."""
        tenant = self._tenant_or_none(tenant_name)
        if tenant is None:
            raise we.task_not_found()
        manifest, _ = self.resolve_repo(tenant)
        res = authorize(ctx, manifest)
        if res.decision is Decision.DENY:
            # non-disclosure: an unauthorized caller cannot enumerate skills
            raise we.task_not_found()
        return self._card_for(tenant, visibility="extended")

    # ------------------------------------------------------------------ #
    # SendMessage / SendStreamingMessage
    # ------------------------------------------------------------------ #
    def _resolve_role(self, roles: dict, manifest: dict, tenant: TenantConfig, message: dict):
        """(skill_id, role_dict, known) from message.metadata.skillId or the entry role."""
        skill_id = (message.get("metadata") or {}).get("skillId")
        if not skill_id:
            skill_id = tenant.entry_role or (manifest.get("a2a") or {}).get("entryRole")
        if tenant.tenant.startswith("Exec-") and not skill_id:
            skill_id = tenant.tenant[len("Exec-") :]
        role = roles.get(skill_id) if skill_id else None
        return skill_id, role, role is not None

    def _provision(self, tenant: TenantConfig, role: dict):
        agent = self.provider.ensure_agent(role)
        environment_id = tenant.provider.environment_id or agent.get("environment_id")
        return agent["id"], agent.get("version"), environment_id

    def send_message(self, params: dict, ctx: AuthContext) -> dict:
        task = self._send(params, ctx, streaming=False)
        return {"task": task}

    def send_streaming_message(self, params: dict, ctx: AuthContext) -> Iterator[dict]:
        message = params.get("message") or {}
        if message.get("taskId"):
            # continuation on a stream: resolve then re-attach
            task = self._continue(message, ctx)
            yield {"task": _dump(task)}
            return
        yield from self._send_stream(params, ctx)

    def _send(self, params: dict, ctx: AuthContext, *, streaming: bool):
        message = params.get("message") or {}
        if message.get("taskId"):
            return _dump(self._continue(message, ctx))

        prep = self._prepare(params, ctx)
        if isinstance(prep, tuple) is False:  # a rejected/settled Task
            return _dump(prep)
        session_id, context_id, prompt = prep

        cfg = params.get("configuration") or {}
        if bool(cfg.get("returnImmediately", False)):
            self._run_background(session_id, context_id, prompt)
            return _dump(tm.submitted_task(session_id, context_id))

        return _dump(self._run_and_store(session_id, context_id, prompt))

    def _prepare(self, params: dict, ctx: AuthContext):
        """Authorize + provision + create session. Returns (session_id, context_id,
        prompt) on success, or a terminal Task (REJECTED / AUTH_REQUIRED) to return."""
        tenant_name = params.get("tenant")
        message = params.get("message") or {}
        context_id = message.get("contextId") or f"ctx-{uuid.uuid4().hex[:16]}"
        synth = f"rej-{uuid.uuid4().hex[:16]}"

        tenant = self._tenant_or_none(tenant_name)
        if tenant is None:
            # unknown/disabled tenant -> generic REJECTED (non-disclosure, authz.md §6)
            return tm.rejected_task(synth, context_id)

        manifest, roles = self.resolve_repo(tenant)
        skill_id, role, known = self._resolve_role(roles, manifest, tenant, message)
        res = authorize(ctx, manifest, skill_role=role, skill_known=known)

        if res.decision is Decision.DENY:
            return tm.rejected_task(synth, context_id)
        if res.decision is Decision.SCOPE_REQUIRED:
            # allowlisted but token lacks a scope it could obtain -> AUTH_REQUIRED
            t = tm.map_result(
                {
                    "text": f"This skill requires scope(s): {', '.join(res.missing_scopes)}.",
                    "status": "blocked",
                    "pending": {
                        "event_ids": [],
                        "tools": {"scope": "request_scope(" + ",".join(res.missing_scopes) + ")"},
                    },
                },
                session_id=synth,
                context_id=context_id,
            )
            return t

        # authorized -> provision + create session (prompt built now to fail fast on url/raw)
        prompt = _join_parts(message.get("parts") or [])
        agent_id, version, environment_id = self._provision(tenant, role)
        title = f"{ctx.caller}: {prompt[:80]}"
        session_id = self.provider.create_session(
            agent_id,
            version,
            environment_id,
            vault_ids=list(tenant.provider.vault_ids) or None,
            memory_resources=list(tenant.provider.memory_resources) or None,
            title=title,
        )
        self.store.create(session_id, ctx.caller, tenant.tenant, context_id)
        self.store.update(
            session_id, task=_dump(tm.submitted_task(session_id, context_id)), terminal=False
        )
        return session_id, context_id, prompt

    def _run_and_store(self, session_id: str, context_id: str, prompt: str | None):
        result = self.provider.run_until_block(session_id, prompt=prompt)
        task = tm.map_result(result, session_id=session_id, context_id=context_id)
        terminal = task.status.state in _TERMINAL
        self.store.update(
            session_id,
            task=_dump(task),
            terminal=terminal,
            pending_tool_use_id=tm.pending_tool_use_id(result.get("pending")),
        )
        return task

    def _run_background(self, session_id: str, context_id: str, prompt: str | None):
        # mark WORKING immediately, then run out of band (returnImmediately: true)
        working = tm.map_result(
            {"text": "", "status": "idle", "pending": None},
            session_id=session_id,
            context_id=context_id,
        )
        working.status.state = tm.TaskState.TASK_STATE_WORKING
        self.store.update(session_id, task=_dump(working), terminal=False)

        def _run():
            try:
                self._run_and_store(session_id, context_id, prompt)
            except Exception:  # pragma: no cover - background best-effort
                fail = tm.map_result(
                    {"text": "background execution failed", "status": "error", "pending": None},
                    session_id=session_id,
                    context_id=context_id,
                )
                self.store.update(session_id, task=_dump(fail), terminal=True)

        threading.Thread(target=_run, daemon=True).start()

    def _send_stream(self, params: dict, ctx: AuthContext) -> Iterator[dict]:
        prep = self._prepare(params, ctx)
        if not isinstance(prep, tuple):  # terminal Task (rejected / auth-required)
            yield {"task": _dump(prep)}
            return
        session_id, context_id, prompt = prep

        yield {"task": self.store.get(session_id).task}  # SUBMITTED
        yield {
            "statusUpdate": tm.TaskStatusUpdateEvent(
                taskId=session_id,
                contextId=context_id,
                status=tm.working_status(session_id, context_id),
            ).model_dump(mode="json", exclude_none=True, by_alias=True)
        }
        task = self._run_and_store(session_id, context_id, prompt)
        yield {"task": _dump(task)}

    def _continue(self, message: dict, ctx: AuthContext):
        """Resolve an interrupted task (state-mapping.md §4): confirm_tool then continue.

        Continuations use ``confirm_tool`` / ``resume_session`` — never a transcript
        replay. The callee's session already holds its own history server-side.
        """
        session_id = message.get("taskId")
        rec = self.store.owned(session_id, ctx.caller)
        if rec is None:
            raise we.task_not_found()

        reply = _join_parts(message.get("parts") or [])
        if rec.pending_tool_use_id:
            allow, deny_message = _parse_decision(reply)
            self.provider.confirm_tool(
                session_id, rec.pending_tool_use_id, allow=allow, deny_message=deny_message
            )
        elif reply:
            self.provider.resume_session(session_id, summary=reply)
        return self._run_and_store(session_id, rec.context_id, None)

    # ------------------------------------------------------------------ #
    # GetTask / ListTasks / CancelTask / SubscribeToTask
    # ------------------------------------------------------------------ #
    def get_task(self, params: dict, ctx: AuthContext) -> dict:
        rec = self.store.owned(params.get("id"), ctx.caller)
        if rec is None or rec.task is None:
            raise we.task_not_found()
        return rec.task

    def list_tasks(self, params: dict, ctx: AuthContext) -> dict:
        tenant = params.get("tenant")
        tasks = [r.task for r in self.store.list_for(ctx.caller, tenant) if r.task]
        return {"tasks": tasks}

    def cancel_task(self, params: dict, ctx: AuthContext) -> dict:
        session_id = params.get("id")
        rec = self.store.owned(session_id, ctx.caller)
        if rec is None:
            raise we.task_not_found()
        if rec.terminal:
            raise we.with_info(
                we.TaskNotCancelableError, "Task is already terminal", "TASK_NOT_CANCELABLE"
            )
        try:
            self.provider.archive_session(session_id)
        except Exception as exc:  # archival failed -> not canceled
            raise we.with_info(
                we.TaskNotCancelableError, "archive_session failed", "TASK_NOT_CANCELABLE"
            ) from exc
        task = tm.canceled_task(session_id, rec.context_id)
        self.store.update(session_id, task=_dump(task), terminal=True)
        return _dump(task)

    def subscribe_to_task(self, params: dict, ctx: AuthContext) -> Iterator[dict]:
        session_id = params.get("id")
        rec = self.store.owned(session_id, ctx.caller)
        if rec is None:
            raise we.task_not_found()
        if rec.terminal:
            raise we.with_info(
                we.UnsupportedOperationError,
                "Cannot subscribe to a terminal task",
                "UNSUPPORTED_OPERATION",
            )
        # re-attach: reflect the current snapshot, then continue running to settle
        if rec.task:
            yield {"task": rec.task}
        task = self._run_and_store(session_id, rec.context_id, None)
        yield {"task": _dump(task)}


_TERMINAL = frozenset(
    {
        tm.TaskState.TASK_STATE_COMPLETED,
        tm.TaskState.TASK_STATE_FAILED,
        tm.TaskState.TASK_STATE_CANCELED,
        tm.TaskState.TASK_STATE_REJECTED,
    }
)
