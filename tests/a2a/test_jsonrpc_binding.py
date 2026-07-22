"""The JSON-RPC 2.0 envelope and HTTP framing the caller puts on the wire conform
to binding.md — regardless of server. Verified through the FROZEN client so the
harness itself is proven to speak the contract.
"""
from __future__ import annotations

import pytest
from fuze_a2a_client import A2AClient, AgentCard

from _harness import MockTransport, errors_for

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]


def _client(mock_card, responses):
    return A2AClient(
        AgentCard.model_validate(mock_card),
        token="test-oidc-token",
        transport=MockTransport(responses=responses, card=mock_card),
    )


def _completed(mock_responses):
    return mock_responses["SendMessage.completed"]


def test_envelope_is_jsonrpc_2_0(mock_card, mock_responses, wire_schema):
    c = _client(mock_card, {"SendMessage": _completed(mock_responses)})
    c.send_message("Create Jira tickets", skill_id="product-manager")
    env = c._transport.sent[0]["envelope"]
    assert env["jsonrpc"] == "2.0"
    assert "id" in env and env["id"]
    assert env["method"] == "SendMessage"
    # The outgoing request must itself validate against the wire request schema.
    errs = errors_for(wire_schema, "JsonRpcRequest", env)
    assert not errs, f"outgoing envelope violates JsonRpcRequest: {errs}"


def test_method_names_are_bare_pascalcase(mock_card, mock_responses):
    fixtures = {
        "SendMessage": _completed(mock_responses),
        "GetTask": mock_responses["GetTask.working"],
        "CancelTask": mock_responses["CancelTask.canceled"],
        "ListTasks": mock_responses["ListTasks.empty"],
    }
    c = _client(mock_card, fixtures)
    c.send_message("x", skill_id="product-manager")
    c.get_task("sess-05HZ")
    c.cancel_task("sess-05HZ")
    c.list_tasks()
    for rec in c._transport.sent:
        m = rec["envelope"]["method"]
        assert "/" not in m, f"0.x slash method leaked: {m}"
        assert "." not in m, f"namespaced method leaked: {m}"
        assert m[0].isupper(), f"method not PascalCase: {m}"


def test_a2a_version_header_on_every_request(mock_card, mock_responses):
    fixtures = {
        "SendMessage": _completed(mock_responses),
        "GetTask": mock_responses["GetTask.working"],
        "ListTasks": mock_responses["ListTasks.empty"],
    }
    c = _client(mock_card, fixtures)
    c.send_message("x", skill_id="product-manager")
    c.get_task("sess-05HZ")
    c.list_tasks()
    # binding.md §1: clients MUST send A2A-Version: 1.0 on every request.
    assert c._transport.sent, "no request captured"
    for rec in c._transport.sent:
        assert rec["headers"].get("A2A-Version") == "1.0", f"missing/wrong version header on {rec}"
        assert rec["headers"].get("Content-Type") == "application/json"


def test_bearer_token_carried(mock_card, mock_responses):
    c = _client(mock_card, {"SendMessage": _completed(mock_responses)})
    c.send_message("x", skill_id="product-manager")
    assert c._transport.sent[0]["headers"].get("Authorization") == "Bearer test-oidc-token"


def test_tenant_echoed_in_params(mock_card, mock_responses):
    # card AgentInterface.tenant (MockTenant) MUST be echoed in the request tenant.
    c = _client(mock_card, {"SendMessage": _completed(mock_responses)})
    c.send_message("x", skill_id="product-manager")
    params = c._transport.sent[0]["envelope"]["params"]
    assert params["tenant"] == "MockTenant", "client must echo the card's interface tenant"


def test_skill_id_travels_as_message_metadata_not_authz(mock_card, mock_responses):
    # authz.md §1: nothing in the body is trusted for authZ. Skill selection is a
    # routing hint in message.metadata, which the callee is free to reject.
    c = _client(mock_card, {"SendMessage": _completed(mock_responses)})
    c.send_message("x", skill_id="product-manager")
    params = c._transport.sent[0]["envelope"]["params"]
    assert params["message"]["metadata"]["skillId"] == "product-manager"


def test_continuation_carries_task_id(mock_card, mock_responses):
    # state-mapping.md §2/§4: answering an interrupted task re-sends the SAME
    # taskId; its presence is what makes the callee resume rather than recreate.
    c = _client(mock_card, {"SendMessage": _completed(mock_responses)})
    c.send_message("yes, proceed", task_id="sess-02HZ")
    params = c._transport.sent[0]["envelope"]["params"]
    assert params["message"]["taskId"] == "sess-02HZ"


def test_client_rejects_non_jsonrpc_card(mock_card):
    # binding.md §2: v1 supports only the JSONRPC binding.
    bad = dict(mock_card)
    bad_iface = dict(bad["supportedInterfaces"][0])
    bad_iface["protocolBinding"] = "GRPC"
    bad["supportedInterfaces"] = [bad_iface]
    with pytest.raises(ValueError):
        A2AClient(AgentCard.model_validate(bad), token="t", transport=MockTransport())
