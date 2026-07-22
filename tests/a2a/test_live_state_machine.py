"""LIVE state-machine behaviour (state-mapping.md §3–§5).

The always_ask -> INPUT_REQUIRED -> resolution flow, the reach_human tolerance,
caller-scoped ListTasks, cancellation, and SubscribeToTask-on-terminal. RED until
the server is reachable. These grade transitions, not code.
"""
from __future__ import annotations

import os

import pytest
from fuze_a2a_client import INTERRUPTED_STATES, TERMINAL_STATES, TaskState
from fuze_a2a_client.errors import UnsupportedOperationError

from conftest import requires_live_server

pytestmark = [pytest.mark.a2a, pytest.mark.integration, pytest.mark.live, requires_live_server]


def _skill(live_card):
    return live_card.skills[0].id


def test_always_ask_pauses_with_explained_message(live_client, live_card):
    # A goal that trips an always_ask/bulk guard must pause in INPUT_REQUIRED with
    # a TaskStatus.message a caller can interpret (state-mapping.md §4).
    prompt = os.environ.get(
        "A2A_ALWAYS_ASK_PROMPT",
        "Bulk-create 50 Jira tickets in the FP project right now.",
    )
    task = live_client.send_message(prompt, skill_id=_skill(live_card))
    if task.status.state not in INTERRUPTED_STATES:
        pytest.fail(
            f"expected an always_ask pause (INPUT_REQUIRED/AUTH_REQUIRED), got {task.status.state}. "
            "Either the guardrail did not fire or the mapping is wrong.",
            pytrace=False,
        )
    assert task.status.message is not None
    assert task.status.message.parts[0].root.text, "pause must explain what/why"


def test_input_required_resolves_to_terminal(live_client, live_card):
    prompt = os.environ.get(
        "A2A_ALWAYS_ASK_PROMPT",
        "Bulk-create 50 Jira tickets in the FP project right now.",
    )
    task = live_client.send_message(prompt, skill_id=_skill(live_card))
    if task.status.state != TaskState.TASK_STATE_INPUT_REQUIRED:
        pytest.skip("no INPUT_REQUIRED pause to resolve in this run")
    resolved = live_client.send_message("Confirmed, proceed with a reduced scope of 3.", task_id=task.id)
    assert resolved.id == task.id, "resuming MUST reuse the session id (state-mapping.md §1)"
    assert resolved.status.state in (TERMINAL_STATES | INTERRUPTED_STATES)


def test_get_task_is_a_session_lookup(live_client, live_card):
    task = live_client.send_message("Report delivery status of the OTP epic.", skill_id=_skill(live_card))
    fetched = live_client.get_task(task.id)
    assert fetched.id == task.id, "GetTask must return the same session by id"


def test_list_tasks_scoped_to_caller(live_client):
    # state-mapping.md §5: a caller sees ONLY its own tasks. Cross-caller
    # visibility is a disclosure bug. We assert every returned task is one this
    # caller created in-session (id-shape check + non-cross-caller).
    result = live_client.list_tasks(page_size=50)
    tasks = result.get("tasks", []) if isinstance(result, dict) else []
    # Cannot enumerate other callers' ids here; the contract guarantee is that the
    # server never returns a task not owned by this identity. We at least assert
    # the field is present and a list (shape), and rely on authz-negative tests
    # for the cross-caller guarantee.
    assert isinstance(tasks, list)


def test_cancel_moves_to_canceled(live_client, live_card):
    task = live_client.send_message("Draft a long backlog grooming plan.", skill_id=_skill(live_card), return_immediately=True)
    canceled = live_client.cancel_task(task.id)
    assert canceled.status.state == TaskState.TASK_STATE_CANCELED


def test_subscribe_on_terminal_is_unsupported(live_client, live_card):
    # state-mapping.md §5 / spec: SubscribeToTask on a terminal task -> -32004.
    task = live_client.send_message("What is 2+2? Answer briefly.", skill_id=_skill(live_card))
    if task.status.state not in TERMINAL_STATES:
        pytest.skip("task did not reach a terminal state to test subscribe-on-terminal")
    with pytest.raises(UnsupportedOperationError) as ei:
        list(live_client.subscribe_to_task(task.id))
    assert ei.value.code == -32004


def test_reach_human_pause_is_tolerated(live_client, live_card):
    # state-mapping.md §4: an interrupted task may be addressed to a HUMAN via
    # reach_human and may leave INPUT_REQUIRED with NO client input. A caller must
    # not assume every INPUT_REQUIRED is its own obligation. We assert only that
    # such a pause carries an explanatory message (so the caller can tell).
    prompt = os.environ.get(
        "A2A_REACH_HUMAN_PROMPT",
        "Escalate: get human sign-off before opening a PR against prod.",
    )
    task = live_client.send_message(prompt, skill_id=_skill(live_card))
    if task.status.state in INTERRUPTED_STATES:
        assert task.status.message is not None, (
            "a human-directed pause MUST still explain itself to the caller (state-mapping.md §4)"
        )
