"""SSE framing per binding.md §1 (Streaming frames) and state-mapping.md §2:
each event is a ``data: {jsonrpc,id,result:<StreamResponse>}`` line, blank lines
separate events, and an error frame raises the typed error. Verified through the
frozen client; each emitted StreamResponse payload validates against the wire
schema.
"""
from __future__ import annotations

import pytest
from fuze_a2a_client import A2AClient, AgentCard
from fuze_a2a_client.errors import UnsupportedOperationError

from _harness import MockTransport, errors_for, sse

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]


def _frame(result):
    return {"jsonrpc": "2.0", "id": "req-stream", "result": result}


STATUS_UPDATE = {
    "statusUpdate": {
        "taskId": "sess-10HZ",
        "contextId": "ctx-10HZ",
        "status": {"state": "TASK_STATE_WORKING", "timestamp": "2026-07-20T10:06:00Z"},
    }
}
ARTIFACT_UPDATE = {
    "artifactUpdate": {
        "taskId": "sess-10HZ",
        "contextId": "ctx-10HZ",
        "artifact": {
            "artifactId": "art-9",
            "name": "created-tickets",
            "parts": [{"data": {"tickets": ["FP-201"]}}],
        },
        "append": False,
        "lastChunk": True,
    }
}
TERMINAL_TASK = {
    "task": {
        "id": "sess-10HZ",
        "contextId": "ctx-10HZ",
        "status": {"state": "TASK_STATE_COMPLETED", "timestamp": "2026-07-20T10:07:00Z"},
    }
}


def _client(mock_card, lines):
    return A2AClient(
        AgentCard.model_validate(mock_card),
        token="t",
        transport=MockTransport(card=mock_card, stream_lines=lines),
    )


def test_stream_yields_each_data_frame(mock_card):
    lines = [
        sse(_frame(STATUS_UPDATE)),
        "",  # event separator — must be ignored
        sse(_frame(ARTIFACT_UPDATE)),
        "",
        sse(_frame(TERMINAL_TASK)),
    ]
    c = _client(mock_card, lines)
    frames = list(c.send_streaming_message("go", skill_id="product-manager"))
    assert len(frames) == 3
    assert frames[0]["statusUpdate"]["status"]["state"] == "TASK_STATE_WORKING"
    assert frames[-1]["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_stream_ignores_non_data_lines(mock_card):
    lines = [
        ": keep-alive comment",
        "event: message",
        sse(_frame(STATUS_UPDATE)),
    ]
    c = _client(mock_card, lines)
    frames = list(c.send_streaming_message("go", skill_id="product-manager"))
    assert len(frames) == 1


def test_each_stream_frame_validates_against_schema(mock_card, wire_schema):
    for result in (STATUS_UPDATE, ARTIFACT_UPDATE, TERMINAL_TASK):
        errs = errors_for(wire_schema, "StreamResponse", result)
        assert not errs, f"stream frame violates StreamResponse: {errs}"


def test_error_frame_raises_typed_error(mock_card):
    # UnsupportedOperationError (-32004): SubscribeToTask on a terminal task.
    err_line = sse(
        {"jsonrpc": "2.0", "id": "req-x", "error": {"code": -32004, "message": "terminal"}}
    )
    c = _client(mock_card, [err_line])
    with pytest.raises(UnsupportedOperationError) as ei:
        list(c.subscribe_to_task("sess-terminal"))
    assert ei.value.code == -32004


def test_streaming_uses_bare_pascalcase_method(mock_card):
    c = _client(mock_card, [sse(_frame(TERMINAL_TASK))])
    list(c.send_streaming_message("go", skill_id="product-manager"))
    assert c._transport.sent[0]["envelope"]["method"] == "SendStreamingMessage"
    assert c._transport.sent[0]["headers"].get("A2A-Version") == "1.0"
