"""Every frozen wire fixture validates against a2a-wire.schema.json, and the
ProtoJSON encoding rules from binding.md hold across all of them.

These fixtures are the canonical shapes a conformant server must be able to emit.
If a fixture is malformed, the whole downstream (server, tests, clients) is built
on sand.
"""
from __future__ import annotations

import pytest

from _harness import errors_for

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]

# Which wire $def each fixture's `result` conforms to.
RESULT_DEF = {
    "SendMessage.completed": "SendMessageResponse",
    "SendMessage.inputRequired": "SendMessageResponse",
    "SendMessage.authRequired": "SendMessageResponse",
    "SendMessage.rejected": "SendMessageResponse",
    "GetTask.working": "Task",
    "CancelTask.canceled": "Task",
    "ListTasks.empty": "ListTasksResponse",
}
ERROR_FIXTURES = {"error.taskNotFound", "error.pushNotSupported", "error.versionNotSupported"}


def test_every_fixture_is_a_valid_jsonrpc_response(wire_schema, mock_responses):
    for name, fixture in mock_responses.items():
        errs = errors_for(wire_schema, "JsonRpcResponse", fixture)
        assert not errs, f"{name}: not a valid JsonRpcResponse: {errs}"


def test_result_fixtures_validate_against_their_def(wire_schema, mock_responses):
    for name, def_name in RESULT_DEF.items():
        result = mock_responses[name]["result"]
        errs = errors_for(wire_schema, def_name, result)
        assert not errs, f"{name}: result violates {def_name}: {errs}"


def test_error_fixtures_validate_against_error_def(wire_schema, mock_responses):
    for name in ERROR_FIXTURES:
        err = mock_responses[name]["error"]
        errs = errors_for(wire_schema, "JsonRpcError", err)
        assert not errs, f"{name}: error violates JsonRpcError: {errs}"


def test_task_state_unspecified_never_emitted(mock_responses):
    # wire schema / state-mapping.md §3: UNSPECIFIED must never appear on the wire.
    import json

    blob = json.dumps(mock_responses)
    assert "TASK_STATE_UNSPECIFIED" not in blob


def _iter_states(obj):
    if isinstance(obj, dict):
        if "state" in obj and isinstance(obj["state"], str):
            yield obj
        for v in obj.values():
            yield from _iter_states(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_states(v)


def test_interrupted_fixtures_carry_status_message(mock_responses):
    # a2a-wire.schema / state-mapping.md §4: INPUT_REQUIRED & AUTH_REQUIRED MUST
    # carry TaskStatus.message explaining what is asked and of whom.
    for name, fixture in mock_responses.items():
        for status in _iter_states(fixture):
            if status["state"] in ("TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"):
                assert status.get("message"), (
                    f"{name}: interrupted state {status['state']} lacks TaskStatus.message"
                )
                parts = status["message"].get("parts", [])
                assert parts and parts[0].get("text"), f"{name}: empty pause message"


def test_timestamps_are_utc_z(mock_responses):
    # binding.md §1: ISO 8601, UTC, Z suffix.
    for name, fixture in mock_responses.items():
        for status in _iter_states(fixture):
            ts = status.get("timestamp")
            if ts is not None:
                assert ts.endswith("Z"), f"{name}: timestamp {ts!r} is not UTC-Z"
                assert "+" not in ts, f"{name}: timestamp {ts!r} carries an offset, not Z"


def test_enum_names_are_screaming_snake(mock_responses):
    # binding.md §1: ProtoJSON enum names, SCREAMING_SNAKE_CASE.
    for status in _iter_states(mock_responses):
        st = status["state"]
        assert st.isupper() and st.startswith("TASK_STATE_"), f"bad enum encoding {st!r}"


def test_roles_are_protojson_screaming_snake(mock_responses):
    def walk(obj):
        if isinstance(obj, dict):
            if "role" in obj and isinstance(obj["role"], str):
                assert obj["role"] in ("ROLE_USER", "ROLE_AGENT", "ROLE_UNSPECIFIED"), (
                    f"role {obj['role']!r} not ProtoJSON encoded"
                )
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(mock_responses)


def test_error_data_is_array_of_typed_any(wire_schema, mock_responses):
    # binding.md §3: error.data is an ARRAY, each element carrying @type.
    for name in ERROR_FIXTURES:
        data = mock_responses[name]["error"].get("data")
        assert isinstance(data, list) and data, f"{name}: error.data must be a non-empty array"
        for element in data:
            assert "@type" in element, f"{name}: error.data element missing @type"
