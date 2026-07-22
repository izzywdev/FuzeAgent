"""LIVE conformance: a running A2A server obeys binding.md on the wire.

RED until backend-engineer's server (agent-templates/a2a/) is reachable via
$A2A_SERVER_BASE_URL. These are the honest-grader's behavioural checks — they
never inspect the server's code, only its wire behaviour against the frozen spec.
"""
from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from conftest import requires_live_server

pytestmark = [pytest.mark.a2a, pytest.mark.integration, pytest.mark.live, requires_live_server]


def test_wellknown_card_is_schema_valid(live_card, card_schema):
    # spec §8.2 / card-projection.md: served unauthenticated, schema-valid.
    errs = [
        f"{list(e.absolute_path)}: {e.message}"
        for e in Draft202012Validator(card_schema).iter_errors(
            live_card.model_dump(by_alias=True, exclude_none=True, mode="json")
        )
    ]
    assert not errs, f"served card violates agent-card.schema.json: {errs}"


def test_card_offers_single_jsonrpc_v1_interface(live_card):
    ifaces = live_card.supportedInterfaces
    assert len(ifaces) == 1
    assert ifaces[0].protocolBinding == "JSONRPC"
    assert ifaces[0].protocolVersion == "1.0"
    assert ifaces[0].tenant, "shared server must disambiguate by tenant"


def test_send_message_returns_schema_valid_response(live_client, live_card, wire_schema):
    from _harness import errors_for

    skill = live_card.skills[0].id
    task = live_client.send_message("Health probe: describe your capability.", skill_id=skill)
    # Re-serialize and validate the Task the server produced.
    errs = errors_for(wire_schema, "Task", task.model_dump(by_alias=True, exclude_none=True, mode="json"))
    assert not errs, f"server Task violates wire schema: {errs}"
    assert task.status.state.value != "TASK_STATE_UNSPECIFIED"


def test_push_notification_method_is_unsupported(live_raw):
    # binding.md §1/§3: every push-notification-config method → -32003.
    status, body = live_raw("CreateTaskPushNotificationConfig", {"tenant": "x"})
    assert "error" in body, f"expected an error, got {body}"
    assert body["error"]["code"] == -32003, body["error"]


def test_wrong_a2a_version_is_rejected(live_raw):
    # binding.md §3: A2A-Version other than 1.0 → VersionNotSupportedError (-32009).
    status, body = live_raw("GetExtendedAgentCard", {}, version="0.9")
    assert "error" in body, f"expected version error, got {body}"
    assert body["error"]["code"] == -32009, body["error"]


def test_unknown_method_is_method_not_found(live_raw):
    status, body = live_raw("TotallyNotAMethod", {})
    assert "error" in body
    assert body["error"]["code"] == -32601, body["error"]


def test_extended_card_requires_auth(live_base_url, live_transport):
    # authz.md §5: GetExtendedAgentCard is authenticated. An unauthenticated call
    # must not return a full extended card.
    import uuid

    envelope = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "GetExtendedAgentCard", "params": {}}
    resp = live_transport.post(
        live_base_url + "/rpc", json=envelope, headers={"Content-Type": "application/json", "A2A-Version": "1.0"}
    )
    # Either transport-level 401/403 or a JSON-RPC error — but never a 200 result.
    if resp.status_code == 200:
        body = resp.json()
        assert "error" in body and body.get("result") is None, (
            "extended card served without authentication (authz.md §5)"
        )
