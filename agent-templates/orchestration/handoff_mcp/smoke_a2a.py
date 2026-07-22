#!/usr/bin/env python3
"""Tool-call smoke harness for the A2A transport (no network, no real server).

Drives the FROZEN generated client through a fake transport backed by the frozen
mock fixtures (`contracts/a2a/v1/mock/`), then asserts that `a2a_transport` maps each
A2A TaskState onto the legacy `{session_id, status, reply, pending}` shape the MCP
tools return. This exercises discovery (well-known card), SendMessage (completed /
inputRequired / authRequired / rejected), GetTask, CancelTask and the taskNotFound
error — the scenarios state-mapping.md and mock/README call out as easy to mishandle.

Run:  python handoff_mcp/smoke_a2a.py
Exit 0 on success; prints a compact PASS/FAIL line per case.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))                     # handoff_mcp/
ORCH = os.path.dirname(HERE)                                          # orchestration/
TEMPLATES_ROOT = os.path.dirname(ORCH)                               # agent-templates/
CLIENT_DIR = os.path.join(TEMPLATES_ROOT, "contracts", "a2a", "v1", "client")
MOCK_DIR = os.path.join(TEMPLATES_ROOT, "contracts", "a2a", "v1", "mock")
for _p in (ORCH, CLIENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import a2a_transport as t  # noqa: E402
from fuze_a2a_client import A2AError, TaskNotFoundError  # noqa: E402

CARD = json.load(open(os.path.join(MOCK_DIR, "agent-card.mock.json"), encoding="utf-8"))
RESP = json.load(open(os.path.join(MOCK_DIR, "responses.mock.json"), encoding="utf-8"))


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeTransport:
    """Routes GET -> the mock card, POST -> a fixture chosen by JSON-RPC method +
    a per-method script so successive calls can walk COMPLETED/INPUT_REQUIRED/etc."""

    def __init__(self, script):
        self._script = list(script)
        self._i = 0

    def get(self, url, *, headers):
        assert url.endswith("/.well-known/agent-card.json"), url  # nosec B101 — test fixture assertion
        return _Resp(CARD)

    def post(self, url, *, json, headers):
        assert json["method"], "missing method"  # nosec B101 — test fixture assertion
        fixture_key = self._script[self._i]
        self._i += 1
        return _Resp(RESP[fixture_key])

    def stream(self, method, url, *, json, headers):  # not used here
        raise NotImplementedError


def _mk_client(script):
    from fuze_a2a_client import A2AClient, AgentCard
    card = AgentCard.model_validate(CARD)
    return A2AClient(card, token="smoke", transport=FakeTransport(script))  # nosec B106 — test fixture, not a real credential


def _bind(target, client):
    t._clients[target] = client  # inject the fake-transport client into the cache


def check(name, got, **expect):
    ok = all(got.get(k) == v for k, v in expect.items())
    detail = "" if ok else f"  expected {expect}, got {{k: got.get(k) for k in expect}}"
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + ("" if ok else f"  got={json.dumps(got, default=str)[:240]}"))
    return ok


def main() -> int:
    passed = True

    # 1. discovery: fetch the well-known card and build a client for a target.
    from fuze_a2a_client import A2AClient, AgentCard
    card = A2AClient.fetch_card(
        "http://a2a-fuzeplan.fuzeagent.svc.cluster.local:8080",
        transport=FakeTransport([]),
    )
    passed &= check("discovery.card", {"status": card.supportedInterfaces[0].tenant},
                    status=AgentCard.model_validate(CARD).supportedInterfaces[0].tenant)

    # 2. SendMessage.completed -> idle, reply = final agent message text.
    _bind("FuzePlan", _mk_client(["SendMessage.completed"]))
    r = t.start("FuzePlan", "Create tickets", skill_id="product-manager")
    passed &= check("start.completed", r, session_id="sess-01HZ", status="idle",
                    reply="Created 3 Jira tickets: FP-101, FP-102, FP-103.")

    # 3. SendMessage.inputRequired -> blocked/input, pending carries the ask message.
    _bind("FuzePlan", _mk_client(["SendMessage.inputRequired"]))
    r = t.start("FuzePlan", "Create 12 tickets")
    ok = (r["status"] == "blocked" and r["pending"] and r["pending"]["kind"] == "input"
          and "always_ask" in r["pending"]["message"])
    print(f"[{'PASS' if ok else 'FAIL'}] start.inputRequired  pending={json.dumps(r['pending'])[:120]}")
    passed &= ok

    # 4. SendMessage.authRequired -> blocked/auth (distinct from input).
    _bind("FuzePlan", _mk_client(["SendMessage.authRequired"]))
    r = t.start("FuzePlan", "Write to FP")
    ok = r["status"] == "blocked" and r["pending"]["kind"] == "auth"
    print(f"[{'PASS' if ok else 'FAIL'}] start.authRequired  kind={r['pending'] and r['pending']['kind']}")
    passed &= ok

    # 5. SendMessage.rejected -> terminal 'rejected', not blocked/retryable.
    _bind("FuzePlan", _mk_client(["SendMessage.rejected"]))
    r = t.start("FuzePlan", "Do a forbidden thing")
    passed &= check("start.rejected", r, status="rejected", reply="Not authorized.")
    passed &= check("start.rejected.pending_is_none", {"p": r["pending"]}, p=None)

    # 6. GetTask.working -> working, no pending.
    _bind("FuzePlan", _mk_client(["GetTask.working"]))
    t._task_target["sess-05HZ"] = "FuzePlan"
    r = t.get_task("sess-05HZ")
    passed &= check("get_task.working", r, status="working", session_id="sess-05HZ")

    # 7. CancelTask.canceled -> maps CANCELED (terminal) with no pending.
    _bind("FuzePlan", _mk_client(["CancelTask.canceled"]))
    r = t.cancel_task("sess-05HZ")
    passed &= check("cancel_task.canceled", r, status="canceled",
                    session_id="sess-05HZ", pending=None)

    # 7b. ask_agent-style continuation: after start, the task is known and a
    #     follow-up resolves to the SAME client/tenant (continue_task).
    _bind("FuzePlan", _mk_client(["SendMessage.inputRequired", "SendMessage.completed"]))
    r = t.start("FuzePlan", "Create 12 tickets")
    ok = t.is_known_task(r["session_id"]) and r["status"] == "blocked"
    r2 = t.continue_task(r["session_id"], "APPROVE: proceed.")
    ok = ok and r2["status"] == "idle" and "FP-101" in r2["reply"]
    print(f"[{'PASS' if ok else 'FAIL'}] continue_task.resolves_pause  {r['status']}->{r2['status']}")
    passed &= ok

    # 7c. relay hop: _run_hop drives a paused task to completion under --auto allow.
    import relay
    _bind("FuzePlan", _mk_client(["SendMessage.inputRequired", "SendMessage.completed"]))
    hop = relay._run_hop("FuzePlan", "Plan the rollout", "allow")
    passed &= check("relay._run_hop.auto_allow", hop, status="idle")

    # 8. taskNotFound (-32001) surfaces as the typed error from the generated client.
    _bind("FuzePlan", _mk_client(["error.taskNotFound"]))
    t._task_target["ghost"] = "FuzePlan"
    try:
        t.get_task("ghost")
        print("[FAIL] error.taskNotFound  (no exception raised)")
        passed = False
    except TaskNotFoundError as exc:
        print(f"[PASS] error.taskNotFound  -> {type(exc).__name__} code={exc.code}")
    except A2AError as exc:
        print(f"[FAIL] error.taskNotFound  wrong type {type(exc).__name__}")
        passed = False

    print("\n" + ("ALL PASS" if passed else "FAILURES PRESENT"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
