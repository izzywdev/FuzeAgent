"""The TaskState classification a caller must rely on (state-mapping.md §3–§4),
verified through the frozen client + fixtures. This is conformance of the CONTRACT
shapes and the client's state constants; the live server's real transitions are in
test_live_state_machine.py.
"""
from __future__ import annotations

import pytest
from fuze_a2a_client import (
    INTERRUPTED_STATES,
    TERMINAL_STATES,
    A2AClient,
    AgentCard,
    TaskState,
)

from _harness import MockTransport

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]


def _send(mock_card, fixture):
    c = A2AClient(
        AgentCard.model_validate(mock_card),
        token="t",
        transport=MockTransport(responses={"SendMessage": fixture}, card=mock_card),
    )
    return c.send_message("goal", skill_id="product-manager")


def test_terminal_and_interrupted_partition():
    # state-mapping.md §3: the two sets are disjoint and the interrupted set is
    # exactly the two waiting states.
    assert TERMINAL_STATES.isdisjoint(INTERRUPTED_STATES)
    assert INTERRUPTED_STATES == {
        TaskState.TASK_STATE_INPUT_REQUIRED,
        TaskState.TASK_STATE_AUTH_REQUIRED,
    }
    assert TERMINAL_STATES == {
        TaskState.TASK_STATE_COMPLETED,
        TaskState.TASK_STATE_FAILED,
        TaskState.TASK_STATE_CANCELED,
        TaskState.TASK_STATE_REJECTED,
    }


def test_completed_is_terminal_with_artifacts(mock_card, mock_responses):
    task = _send(mock_card, mock_responses["SendMessage.completed"])
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.status.state in TERMINAL_STATES
    assert task.artifacts, "completed task should carry produced artifacts"


def test_input_required_is_interrupted_and_explained(mock_card, mock_responses):
    task = _send(mock_card, mock_responses["SendMessage.inputRequired"])
    assert task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
    assert task.status.state in INTERRUPTED_STATES
    assert task.status.state not in TERMINAL_STATES
    # §4: the pause MUST be explained so the caller can interpret it.
    assert task.status.message is not None
    assert task.status.message.parts[0].root.text


def test_auth_required_is_distinct_from_input_required(mock_card, mock_responses):
    task = _send(mock_card, mock_responses["SendMessage.authRequired"])
    assert task.status.state == TaskState.TASK_STATE_AUTH_REQUIRED
    assert task.status.state in INTERRUPTED_STATES
    assert task.status.message is not None


def test_rejected_is_terminal_not_interrupted(mock_card, mock_responses):
    # authz.md §4: a denial is REJECTED (terminal) — never AUTH_REQUIRED. A caller
    # must not retry it forever.
    task = _send(mock_card, mock_responses["SendMessage.rejected"])
    assert task.status.state == TaskState.TASK_STATE_REJECTED
    assert task.status.state in TERMINAL_STATES
    assert task.status.state not in INTERRUPTED_STATES


def test_rejected_message_is_generic(mock_card, mock_responses):
    # authz.md §6: never leak WHY beyond "not authorized".
    task = _send(mock_card, mock_responses["SendMessage.rejected"])
    text = task.status.message.parts[0].root.text.lower()
    assert "not authorized" in text
    for leak in ("providesto", "allowlist", "does not exist", "unknown tenant"):
        assert leak not in text


def test_working_is_not_a_resting_state(mock_card, mock_responses):
    # state-mapping.md §3: WORKING is emitted on the stream, not a settled result.
    task_dict = mock_responses["GetTask.working"]["result"]
    assert task_dict["status"]["state"] == "TASK_STATE_WORKING"
    assert task_dict["status"]["state"] not in {s.value for s in TERMINAL_STATES}
    assert task_dict["status"]["state"] not in {s.value for s in INTERRUPTED_STATES}
