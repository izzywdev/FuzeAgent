"""The frozen schemas are themselves valid JSON Schema (Draft 2020-12).

If a schema does not even compile, nothing downstream that claims to conform to
it can be trusted. This is the floor of the conformance suite.
"""
from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]


def test_wire_schema_is_valid_draft2020(wire_schema):
    Draft202012Validator.check_schema(wire_schema)


def test_card_schema_is_valid_draft2020(card_schema):
    Draft202012Validator.check_schema(card_schema)


def test_wire_schema_declares_full_taskstate_enum(wire_schema):
    states = set(wire_schema["$defs"]["TaskState"]["enum"])
    # Every A2A 1.0 TaskState, incl. both interrupted states, must be expressible.
    assert states == {
        "TASK_STATE_UNSPECIFIED",
        "TASK_STATE_SUBMITTED",
        "TASK_STATE_WORKING",
        "TASK_STATE_COMPLETED",
        "TASK_STATE_FAILED",
        "TASK_STATE_CANCELED",
        "TASK_STATE_INPUT_REQUIRED",
        "TASK_STATE_REJECTED",
        "TASK_STATE_AUTH_REQUIRED",
    }


def test_jsonrpc_method_enum_is_bare_pascalcase(wire_schema):
    methods = set(wire_schema["$defs"]["JsonRpcRequest"]["properties"]["method"]["enum"])
    # binding.md §1: bare PascalCase, NOT 0.x 'message/send', NOT namespaced.
    assert methods == {
        "SendMessage",
        "SendStreamingMessage",
        "GetTask",
        "ListTasks",
        "CancelTask",
        "SubscribeToTask",
        "GetExtendedAgentCard",
    }
    for m in methods:
        assert "/" not in m, "0.x slash style leaked into v1"
        assert "." not in m, "namespaced method style leaked into v1"


def test_push_notification_methods_absent_from_wire(wire_schema):
    # binding.md §1 / state-mapping.md §5: push-notification config methods are
    # out of v1 and must return -32003; they must not be advertised as callable.
    methods = wire_schema["$defs"]["JsonRpcRequest"]["properties"]["method"]["enum"]
    for banned in (
        "CreateTaskPushNotificationConfig",
        "GetTaskPushNotificationConfig",
        "ListTaskPushNotificationConfigs",
        "DeleteTaskPushNotificationConfig",
    ):
        assert banned not in methods


def test_card_schema_forbids_toplevel_url(card_schema):
    # card-projection.md §2 / A2A 1.0 replaced 0.x url+preferredTransport with
    # supportedInterfaces. additionalProperties:false + no 'url' prop enforces it.
    assert card_schema["additionalProperties"] is False
    assert "url" not in card_schema["properties"]
    assert "preferredTransport" not in card_schema["properties"]


def test_bad_schema_is_rejected():
    # Guard: our validator genuinely rejects malformed schemas (no false green).
    with pytest.raises(SchemaError):
        Draft202012Validator.check_schema({"type": "not-a-real-type"})
