"""Unit tests for the A2A adapter (state-mapping.md + authz.md) with a fake provider.

The fake stands in for the Managed-Agents runtime below the providers/base.py seam, so
these tests exercise the TRANSLATION only — the adapter's entire responsibility.
"""

from __future__ import annotations

import pytest
from a2a.adapter import A2AAdapter
from a2a.authz import AuthContext
from a2a.config import ProviderBinding, ServerConfig, TenantConfig
from a2a.loader import load_repo


class FakeProvider:
    """Scripted provider. ``script`` maps session_id -> list of run_until_block results."""

    def __init__(self, results=None):
        self.results = results or {}
        self.default = {"text": "done", "status": "idle", "pending": None}
        self.sessions = []
        self.confirmed = []
        self.resumed = []
        self.archived = []
        self._n = 0

    def ensure_agent(self, manifest, multiagent=None):
        return {"name": manifest.get("role", "x"), "id": "agent-1", "version": "1"}

    def create_session(
        self, agent_id, version, environment_id, vault_ids=None, memory_resources=None, title=None
    ):
        self._n += 1
        sid = f"sess-{self._n}"
        self.sessions.append({"id": sid, "title": title, "vault_ids": vault_ids})
        return sid

    def run_until_block(self, session_id, prompt=None):
        seq = self.results.get(session_id)
        if seq:
            return seq.pop(0)
        return dict(self.default)

    def confirm_tool(self, session_id, tool_use_id, allow=True, deny_message=None):
        self.confirmed.append((session_id, tool_use_id, allow, deny_message))

    def resume_session(self, session_id, summary, context_ref=""):
        self.resumed.append((session_id, summary))

    def archive_session(self, session_id):
        self.archived.append(session_id)


@pytest.fixture
def fuzeplan_cfg():
    return ServerConfig(
        enabled=True,
        tenants=(
            TenantConfig(
                tenant="FuzePlan",
                repo="izzywdev/FuzePlan",
                enabled=True,
                entry_role="product-manager",
                provider=ProviderBinding(name="fake", vault_ids=("v1",)),
            ),
        ),
    )


@pytest.fixture
def resolver(fuzeplan_repo):
    def _resolve(tenant):
        return load_repo(fuzeplan_repo)

    return _resolve


def _ctx(caller="FuzeSales"):
    return AuthContext(caller=caller)


def _adapter(cfg, provider, resolver):
    return A2AAdapter(cfg, provider, resolver)


# --- SendMessage happy path -------------------------------------------------
def test_send_message_completed(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m1",
            "role": "ROLE_USER",
            "parts": [{"text": "Create tickets"}],
            "metadata": {"skillId": "product-manager"},
        },
    }
    out = a.send_message(params, _ctx())
    task = out["task"]
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["id"] == "sess-1"
    # session titled with caller identity + prompt head
    assert prov.sessions[0]["title"].startswith("FuzeSales:")
    assert prov.sessions[0]["vault_ids"] == ["v1"]


def test_entry_role_used_when_no_skill(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": "hi"}]},
    }
    out = a.send_message(params, _ctx())
    assert out["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


# --- authz denials ----------------------------------------------------------
def test_unauthorized_caller_rejected(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
    }
    out = a.send_message(params, _ctx(caller="FuzeMalory"))
    assert out["task"]["status"]["state"] == "TASK_STATE_REJECTED"
    assert out["task"]["status"]["message"]["parts"][0]["text"] == "Not authorized."
    # no session created for a denied caller
    assert prov.sessions == []


def test_unknown_tenant_is_generic_rejected(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "Nope",
        "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
    }
    out = a.send_message(params, _ctx())
    assert out["task"]["status"]["state"] == "TASK_STATE_REJECTED"


def test_unknown_skill_rejected(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m",
            "role": "ROLE_USER",
            "parts": [{"text": "x"}],
            "metadata": {"skillId": "does-not-exist"},
        },
    }
    out = a.send_message(params, _ctx())
    assert out["task"]["status"]["state"] == "TASK_STATE_REJECTED"


# --- interrupted + continuation ---------------------------------------------
def test_input_required_then_continue_confirms_tool(fuzeplan_cfg, resolver):
    prov = FakeProvider(
        results={
            "sess-1": [
                {
                    "text": "May I create 12 tickets?",
                    "status": "blocked",
                    "pending": {
                        "event_ids": ["tu-1"],
                        "tools": {"tu-1": 'create_tickets({"n":12})'},
                    },
                },
                {"text": "created", "status": "idle", "pending": None},
            ]
        }
    )
    a = _adapter(fuzeplan_cfg, prov, resolver)
    p1 = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m1",
            "role": "ROLE_USER",
            "parts": [{"text": "Create 12 tickets"}],
            "metadata": {"skillId": "product-manager"},
        },
    }
    t1 = a.send_message(p1, _ctx())["task"]
    assert t1["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    sid = t1["id"]

    # caller answers on the SAME taskId
    p2 = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m2",
            "role": "ROLE_USER",
            "taskId": sid,
            "parts": [{"text": "yes, go ahead"}],
        },
    }
    t2 = a.send_message(p2, _ctx())["task"]
    assert t2["status"]["state"] == "TASK_STATE_COMPLETED"
    assert prov.confirmed == [(sid, "tu-1", True, None)]


def test_continue_deny_passes_reason(fuzeplan_cfg, resolver):
    prov = FakeProvider(
        results={
            "sess-1": [
                {
                    "text": "may I?",
                    "status": "blocked",
                    "pending": {"event_ids": ["tu-9"], "tools": {"tu-9": "open_pr({})"}},
                },
                {"text": "ok, stopped", "status": "idle", "pending": None},
            ]
        }
    )
    a = _adapter(fuzeplan_cfg, prov, resolver)
    p1 = {
        "tenant": "FuzePlan",
        "message": {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": "open a PR"}]},
    }
    sid = a.send_message(p1, _ctx())["task"]["id"]
    p2 = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m2",
            "role": "ROLE_USER",
            "taskId": sid,
            "parts": [{"text": "deny - too risky"}],
        },
    }
    a.send_message(p2, _ctx())
    assert prov.confirmed[0][2] is False
    assert "too risky" in prov.confirmed[0][3]


def test_continue_foreign_task_is_not_found(fuzeplan_cfg, resolver):
    prov = FakeProvider(
        results={
            "sess-1": [
                {
                    "text": "?",
                    "status": "blocked",
                    "pending": {"event_ids": ["t"], "tools": {"t": "x"}},
                }
            ]
        }
    )
    a = _adapter(fuzeplan_cfg, prov, resolver)
    sid = a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
        },
        _ctx(caller="FuzeSales"),
    )["task"]["id"]
    # a DIFFERENT allowlisted caller may not touch it
    from a2a.wire_errors import TaskNotFoundError

    with pytest.raises(TaskNotFoundError):
        a.send_message(
            {
                "tenant": "FuzePlan",
                "message": {
                    "messageId": "m2",
                    "role": "ROLE_USER",
                    "taskId": sid,
                    "parts": [{"text": "yes"}],
                },
            },
            _ctx(caller="FuzeService"),
        )


# --- parts handling ---------------------------------------------------------
def test_url_part_rejected_content_type(fuzeplan_cfg, resolver):
    from a2a.wire_errors import ContentTypeNotSupportedError

    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"url": "http://x/y"}]},
    }
    with pytest.raises(ContentTypeNotSupportedError):
        a.send_message(params, _ctx())


# --- GetTask / ListTasks / CancelTask --------------------------------------
def test_get_task_scoped_to_caller(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    sid = a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
        },
        _ctx(caller="FuzeSales"),
    )["task"]["id"]
    got = a.get_task({"id": sid, "tenant": "FuzePlan"}, _ctx(caller="FuzeSales"))
    assert got["id"] == sid

    from a2a.wire_errors import TaskNotFoundError

    with pytest.raises(TaskNotFoundError):
        a.get_task({"id": sid}, _ctx(caller="FuzeService"))


def test_list_tasks_only_own(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
        },
        _ctx(caller="FuzeSales"),
    )
    a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "y"}]},
        },
        _ctx(caller="FuzeService"),
    )
    sales = a.list_tasks({"tenant": "FuzePlan"}, _ctx(caller="FuzeSales"))
    assert len(sales["tasks"]) == 1


def test_cancel_task_archives_and_marks_canceled(fuzeplan_cfg, resolver):
    prov = FakeProvider(
        results={
            "sess-1": [
                {
                    "text": "?",
                    "status": "blocked",
                    "pending": {"event_ids": ["t"], "tools": {"t": "x"}},
                }
            ]
        }
    )
    a = _adapter(fuzeplan_cfg, prov, resolver)
    sid = a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
        },
        _ctx(),
    )["task"]["id"]
    out = a.cancel_task({"id": sid, "tenant": "FuzePlan"}, _ctx())
    assert out["status"]["state"] == "TASK_STATE_CANCELED"
    assert prov.archived == [sid]


def test_cancel_terminal_task_not_cancelable(fuzeplan_cfg, resolver):
    from a2a.wire_errors import TaskNotCancelableError

    prov = FakeProvider()  # completes immediately -> terminal
    a = _adapter(fuzeplan_cfg, prov, resolver)
    sid = a.send_message(
        {
            "tenant": "FuzePlan",
            "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
        },
        _ctx(),
    )["task"]["id"]
    with pytest.raises(TaskNotCancelableError):
        a.cancel_task({"id": sid, "tenant": "FuzePlan"}, _ctx())


# --- streaming --------------------------------------------------------------
def test_streaming_yields_working_then_terminal(fuzeplan_cfg, resolver):
    prov = FakeProvider()
    a = _adapter(fuzeplan_cfg, prov, resolver)
    params = {
        "tenant": "FuzePlan",
        "message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]},
    }
    frames = list(a.send_streaming_message(params, _ctx()))
    states = []
    for f in frames:
        if "task" in f:
            states.append(f["task"]["status"]["state"])
        elif "statusUpdate" in f:
            states.append(f["statusUpdate"]["status"]["state"])
    assert states[0] == "TASK_STATE_SUBMITTED"
    assert "TASK_STATE_WORKING" in states
    assert states[-1] == "TASK_STATE_COMPLETED"


# --- cards ------------------------------------------------------------------
def test_well_known_card_public(fuzeplan_cfg, resolver):
    a = _adapter(fuzeplan_cfg, FakeProvider(), resolver)
    card = a.well_known_card("FuzePlan")
    assert card["supportedInterfaces"][0]["tenant"] == "FuzePlan"


def test_extended_card_requires_authorization(fuzeplan_cfg, resolver):
    from a2a.wire_errors import TaskNotFoundError

    a = _adapter(fuzeplan_cfg, FakeProvider(), resolver)
    # allowlisted caller gets it
    card = a.extended_card("FuzePlan", _ctx(caller="FuzeSales"))
    assert card["skills"]
    # non-allowlisted caller cannot enumerate -> not found
    with pytest.raises(TaskNotFoundError):
        a.extended_card("FuzePlan", _ctx(caller="FuzeMalory"))
