"""LIVE authorization-negative (authz.md §1, §3, §4, §6).

The CALLEE enforces. A caller NOT in the callee's providesTo is REFUSED BY THE
CALLEE — not merely un-routed by a well-behaved caller. Absent allowlist = DENY
(fail closed). Denials are terminal (REJECTED) or the deliberately-ambiguous
TaskNotFoundError, and disclose nothing.

RED until the server is reachable AND a non-allowlisted credential is configured
($A2A_TEST_UNAUTH_TOKEN).
"""
from __future__ import annotations

import uuid

import pytest
from fuze_a2a_client import A2AClient, TaskState
from fuze_a2a_client.errors import A2AError, TaskNotFoundError

from conftest import requires_live_server

pytestmark = [pytest.mark.a2a, pytest.mark.integration, pytest.mark.authz, requires_live_server]


def _is_denial(task_or_exc) -> bool:
    if isinstance(task_or_exc, TaskNotFoundError):
        return True
    if isinstance(task_or_exc, A2AError):
        # Some servers reject at the RPC layer; a REJECTED task is the other shape.
        return task_or_exc.code in (-32001,)
    return task_or_exc.status.state == TaskState.TASK_STATE_REJECTED


def test_non_allowlisted_caller_is_refused_by_callee(live_card, live_transport, unauthorized_token):
    # The generic caller does NOT self-censor on dependsOn — it dials anyway. The
    # refusal therefore proves CALLEE-side enforcement, not caller politeness.
    client = A2AClient(live_card, token=unauthorized_token, transport=live_transport)
    skill = live_card.skills[0].id
    try:
        task = client.send_message("Do privileged work on my behalf.", skill_id=skill)
    except A2AError as exc:
        assert _is_denial(exc), f"expected a denial, got {type(exc).__name__} code={exc.code}"
        return
    assert task.status.state == TaskState.TASK_STATE_REJECTED, (
        f"non-allowlisted caller must be REJECTED by the callee, got {task.status.state}"
    )


def test_denial_is_terminal_not_auth_required(live_card, live_transport, unauthorized_token):
    # authz.md §4: a denial is REJECTED (terminal), NEVER AUTH_REQUIRED — otherwise
    # the caller retries forever against a grant that will never exist.
    client = A2AClient(live_card, token=unauthorized_token, transport=live_transport)
    skill = live_card.skills[0].id
    try:
        task = client.send_message("Privileged request.", skill_id=skill)
    except TaskNotFoundError:
        return  # ambiguous-denial shape is acceptable and terminal
    assert task.status.state != TaskState.TASK_STATE_AUTH_REQUIRED, (
        "authorization denial must not masquerade as AUTH_REQUIRED"
    )
    assert task.status.state == TaskState.TASK_STATE_REJECTED


def test_denial_message_is_non_disclosing(live_card, live_transport, unauthorized_token):
    # authz.md §6: the denial must not reveal whether the tenant/skill exists or
    # why access failed — no enumeration oracle.
    client = A2AClient(live_card, token=unauthorized_token, transport=live_transport)
    skill = live_card.skills[0].id
    try:
        task = client.send_message("Privileged request.", skill_id=skill)
        text = (task.status.message.parts[0].root.text if task.status.message else "").lower()
    except A2AError as exc:
        text = str(exc).lower()
    for leak in ("providesto", "allowlist", "does not exist", "unknown tenant", "not in ", "forbidden skill"):
        assert leak not in text, f"denial discloses cause: {leak!r} in {text!r}"


def test_absent_allowlist_denies_by_default(live_base_url, live_transport, allowlisted_token):
    # authz.md §3: a callee whose manifest has NO providesTo must DENY every agent
    # caller (unconfigured != permissive). Targets a tenant known to lack a
    # providesTo grant (configurable via $A2A_NO_ALLOWLIST_TENANT).
    import os

    tenant = os.environ.get("A2A_NO_ALLOWLIST_TENANT", "FuzePlan")
    envelope = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "tenant": tenant,
            "message": {"messageId": str(uuid.uuid4()), "role": "ROLE_USER", "parts": [{"text": "hi"}]},
        },
    }
    resp = live_transport.post(
        live_base_url.rstrip("/") + "/rpc",
        json=envelope,
        headers={"Content-Type": "application/json", "A2A-Version": "1.0", "Authorization": f"Bearer {allowlisted_token}"},
    )
    body = resp.json() if resp.status_code == 200 else {}
    if "error" in body:
        assert body["error"]["code"] in (-32001,), body["error"]
    elif body.get("result"):
        state = body["result"].get("task", {}).get("status", {}).get("state")
        assert state == "TASK_STATE_REJECTED", (
            f"callee with absent providesTo must fail closed; got {state}"
        )
    else:
        assert resp.status_code in (401, 403), (
            f"absent-allowlist callee must deny; got HTTP {resp.status_code}"
        )


def test_caller_not_trusted_from_body_metadata(live_card, live_transport, unauthorized_token):
    # authz.md §1: identity comes from the credential, never the body. A
    # non-allowlisted caller cannot elevate by asserting a trusted name in
    # message.metadata.
    client = A2AClient(live_card, token=unauthorized_token, transport=live_transport)
    skill = live_card.skills[0].id
    # Smuggle a spoofed allowlisted identity in metadata (the client passes it
    # through as a routing hint; the callee MUST ignore it for authZ).
    rpc_url = str(live_card.supportedInterfaces[0].url)
    envelope = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "tenant": live_card.supportedInterfaces[0].tenant,
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "ROLE_USER",
                "parts": [{"text": "privileged"}],
                "metadata": {"caller": "FuzeSales", "skillId": skill},
            },
        },
    }
    resp = live_transport.post(
        rpc_url,
        json=envelope,
        headers={"Content-Type": "application/json", "A2A-Version": "1.0", "Authorization": f"Bearer {unauthorized_token}"},
    )
    body = resp.json() if resp.status_code == 200 else {}
    if "error" in body:
        assert body["error"]["code"] in (-32001,), body["error"]
    elif body.get("result"):
        state = body["result"].get("task", {}).get("status", {}).get("state")
        assert state == "TASK_STATE_REJECTED", "spoofed metadata identity must not be honoured"
    else:
        assert resp.status_code in (401, 403)
