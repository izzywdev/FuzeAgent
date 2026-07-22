"""Unit tests for the HTTP + SSE transport (binding.md)."""

from __future__ import annotations

import json

import pytest
from a2a.adapter import A2AAdapter
from a2a.config import ProviderBinding, ServerConfig, TenantConfig
from a2a.identity import StaticAuthenticator
from a2a.loader import load_repo
from a2a.server import build_app
from starlette.testclient import TestClient

from .test_adapter import FakeProvider


@pytest.fixture
def client(fuzeplan_repo):
    cfg = ServerConfig(
        enabled=True,
        tenants=(
            TenantConfig(
                tenant="FuzePlan",
                repo="izzywdev/FuzePlan",
                enabled=True,
                entry_role="product-manager",
                provider=ProviderBinding(name="fake"),
            ),
        ),
    )
    adapter = A2AAdapter(cfg, FakeProvider(), lambda t: load_repo(fuzeplan_repo))
    auth = StaticAuthenticator({"tok-sales": "FuzeSales", "tok-mal": "FuzeMalory"})
    app = build_app(adapter, auth)
    return TestClient(app)


def _hdr(token="tok-sales"):
    return {
        "Authorization": f"Bearer {token}",
        "A2A-Version": "1.0",
        "Content-Type": "application/json",
    }


def _rpc(method, params, req_id="req-1"):
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


def _msg(text="hi", **extra):
    m = {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": text}]}
    m.update(extra)
    return m


# --- discovery --------------------------------------------------------------
def test_well_known_card_unauthenticated(client):
    r = client.get("/.well-known/agent-card.json?tenant=FuzePlan")
    assert r.status_code == 200
    card = r.json()
    assert card["supportedInterfaces"][0]["tenant"] == "FuzePlan"
    assert card["signatures"]


def test_well_known_single_tenant_default(client):
    r = client.get("/.well-known/agent-card.json")
    assert r.status_code == 200


def test_healthz(client):
    assert client.get("/healthz").text == "ok"


# --- SendMessage ------------------------------------------------------------
def test_send_message_completed(client):
    r = client.post(
        "/rpc", json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}), headers=_hdr()
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "req-1"
    assert body["result"]["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_unauthenticated_rpc_is_401(client):
    r = client.post(
        "/rpc",
        json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}),
        headers={"A2A-Version": "1.0"},
    )
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_denied_caller_gets_rejected_task(client):
    r = client.post(
        "/rpc",
        json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}),
        headers=_hdr("tok-mal"),
    )
    assert r.status_code == 200
    assert r.json()["result"]["task"]["status"]["state"] == "TASK_STATE_REJECTED"


# --- version + method errors ------------------------------------------------
def test_wrong_version_header_is_32009(client):
    h = _hdr()
    h["A2A-Version"] = "2.0"
    r = client.post(
        "/rpc", json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}), headers=h
    )
    assert r.json()["error"]["code"] == -32009


def test_unknown_method_is_32601(client):
    r = client.post("/rpc", json=_rpc("Frobnicate", {}), headers=_hdr())
    assert r.json()["error"]["code"] == -32601


def test_push_notification_method_is_32003(client):
    r = client.post("/rpc", json=_rpc("CreateTaskPushNotificationConfig", {}), headers=_hdr())
    assert r.json()["error"]["code"] == -32003


def test_parse_error_is_32700(client):
    r = client.post("/rpc", content=b"{not json", headers=_hdr())
    assert r.json()["error"]["code"] == -32700


def test_invalid_request_missing_method(client):
    r = client.post("/rpc", json={"jsonrpc": "2.0", "id": "x"}, headers=_hdr())
    assert r.json()["error"]["code"] == -32600


# --- GetTask ----------------------------------------------------------------
def test_get_task_roundtrip(client):
    send = client.post(
        "/rpc", json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}), headers=_hdr()
    ).json()
    sid = send["result"]["task"]["id"]
    r = client.post("/rpc", json=_rpc("GetTask", {"id": sid, "tenant": "FuzePlan"}), headers=_hdr())
    assert r.json()["result"]["id"] == sid


def test_get_task_other_caller_is_32001(client):
    send = client.post(
        "/rpc",
        json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}),
        headers=_hdr("tok-sales"),
    ).json()
    sid = send["result"]["task"]["id"]
    # FuzeMalory isn't even allowlisted, but the point is disclosure parity: -32001
    r = client.post("/rpc", json=_rpc("GetTask", {"id": sid}), headers=_hdr("tok-mal"))
    assert r.json()["error"]["code"] == -32001


# --- streaming --------------------------------------------------------------
def test_streaming_sse_frames(client):
    payload = _rpc("SendStreamingMessage", {"tenant": "FuzePlan", "message": _msg()})
    with client.stream("POST", "/rpc", json=payload, headers=_hdr()) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        states = []
        for line in resp.iter_lines():
            if not line:
                continue
            line = line if isinstance(line, str) else line.decode()
            if line.startswith("data:"):
                frame = json.loads(line[len("data:") :].strip())
                result = frame["result"]
                if "task" in result:
                    states.append(result["task"]["status"]["state"])
                elif "statusUpdate" in result:
                    states.append(result["statusUpdate"]["status"]["state"])
    assert states[0] == "TASK_STATE_SUBMITTED"
    assert states[-1] == "TASK_STATE_COMPLETED"


# --- extended card ----------------------------------------------------------
def test_extended_card_requires_auth(client):
    assert client.get("/extendedAgentCard?tenant=FuzePlan").status_code == 401


def test_extended_card_allowlisted(client):
    r = client.get("/extendedAgentCard?tenant=FuzePlan", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["skills"]


def test_extended_card_denied_is_404(client):
    r = client.get("/extendedAgentCard?tenant=FuzePlan", headers=_hdr("tok-mal"))
    assert r.status_code == 404
