"""Unit tests for the run_until_block -> A2A Task mapping (state-mapping.md §3/§4)."""
from __future__ import annotations

import pytest
from a2a import task_mapper as tm
from a2a._contract import TaskState


def _blocked(desc: str) -> dict:
    return {"text": "", "status": "blocked", "pending": {"event_ids": ["e1"], "tools": {"e1": desc}}}


# --- the core status table --------------------------------------------------
def test_idle_maps_to_completed_with_agent_message():
    task = tm.map_result({"text": "all done", "status": "idle", "pending": None}, session_id="s", context_id="c")
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.id == "s" and task.contextId == "c"
    assert task.status.message.role.value == "ROLE_AGENT"
    assert task.status.message.parts[0].root.text == "all done"
    assert task.status.timestamp is not None


def test_error_maps_to_failed():
    task = tm.map_result({"text": "kaboom", "status": "error", "pending": None}, session_id="s", context_id="c")
    assert task.status.state == TaskState.TASK_STATE_FAILED
    assert "kaboom" in task.status.message.parts[0].root.text


def test_blocked_tool_decision_is_input_required():
    task = tm.map_result(_blocked('open_pr({"target":"prod"})'), session_id="s", context_id="c")
    assert task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
    # message REQUIRED for interrupted states
    assert task.status.message is not None


def test_blocked_credential_is_auth_required():
    task = tm.map_result(_blocked('fetch_credential({"vault":"atlassian"})'), session_id="s", context_id="c")
    assert task.status.state == TaskState.TASK_STATE_AUTH_REQUIRED


@pytest.mark.parametrize(
    "desc,expected",
    [
        ('create_tickets({"n":12})', TaskState.TASK_STATE_INPUT_REQUIRED),
        ('open_pr({"target":"prod"})', TaskState.TASK_STATE_INPUT_REQUIRED),
        ('oauth_authorize({"provider":"github"})', TaskState.TASK_STATE_AUTH_REQUIRED),
        ('get_api_key({})', TaskState.TASK_STATE_AUTH_REQUIRED),
        ('request access_grant for repo', TaskState.TASK_STATE_AUTH_REQUIRED),
        ('use_token({})', TaskState.TASK_STATE_AUTH_REQUIRED),
    ],
)
def test_pause_classifier(desc, expected):
    pending = {"event_ids": ["e1"], "tools": {"e1": desc}}
    assert tm.classify_pause(pending) == expected


def test_pause_reason_prefers_agent_text():
    pending = {"event_ids": ["e1"], "tools": {"e1": "open_pr({})"}}
    task = tm.map_result({"text": "May I open this PR against prod?", "status": "blocked", "pending": pending}, session_id="s", context_id="c")
    assert task.status.message.parts[0].root.text == "May I open this PR against prod?"


def test_pause_reason_falls_back_to_pending_when_no_text():
    task = tm.map_result(_blocked("delete_index({})"), session_id="s", context_id="c")
    assert "delete_index" in task.status.message.parts[0].root.text


def test_pending_tool_use_id():
    assert tm.pending_tool_use_id({"event_ids": ["e9"], "tools": {"e9": "x"}}) == "e9"
    assert tm.pending_tool_use_id({"tools": {"only": "x"}}) == "only"
    assert tm.pending_tool_use_id(None) is None


def test_unmappable_status_raises_never_unspecified():
    with pytest.raises(ValueError):
        tm.map_result({"text": "", "status": "weird", "pending": None}, session_id="s", context_id="c")


# --- resting/terminal constructors -----------------------------------------
def test_submitted_and_rejected_and_canceled():
    assert tm.submitted_task("s", "c").status.state == TaskState.TASK_STATE_SUBMITTED
    rej = tm.rejected_task("s", "c")
    assert rej.status.state == TaskState.TASK_STATE_REJECTED
    # non-disclosure: generic message only
    assert rej.status.message.parts[0].root.text == "Not authorized."
    assert tm.canceled_task("s", "c").status.state == TaskState.TASK_STATE_CANCELED


def test_now_iso_has_z_suffix():
    assert tm.now_iso().endswith("Z")
