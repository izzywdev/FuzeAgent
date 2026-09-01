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


# --- per-product pod (single tenant + its own endpoint) ----------------------
PER_PRODUCT_URL = "http://a2a-fuzeplan.fuzeplan.svc.cluster.local:8080/rpc"


@pytest.fixture
def per_product_client(fuzeplan_repo):
    """A pod deployed FOR ONE PRODUCT: one enabled tenant, its own Service URL.

    Same server code and same values document as the shared deployment — the only
    differences are the length of `tenants` and `inClusterUrl`.
    """
    cfg = ServerConfig(
        enabled=True,
        in_cluster_url=PER_PRODUCT_URL,
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
    auth = StaticAuthenticator({"tok-sales": "FuzeSales"})
    return TestClient(build_app(adapter, auth))


def test_per_product_pod_serves_its_own_endpoint(per_product_client):
    """Discovery on a per-product pod: no `?tenant=` needed, and the advertised URL is
    the pod's OWN Service — not `a2a-shared`. Serving the shared address from a
    per-product pod is the exact failure that kept these pods disabled."""
    r = per_product_client.get("/.well-known/agent-card.json")
    assert r.status_code == 200
    card = r.json()
    iface = card["supportedInterfaces"][0]
    assert iface["url"] == PER_PRODUCT_URL
    assert iface["tenant"] == "FuzePlan"
    assert "a2a-shared" not in json.dumps(card)


def test_per_product_pod_still_serves_and_dispatches(per_product_client):
    """The endpoint move is cosmetic to the wire: RPC on the same pod still works."""
    r = per_product_client.post(
        "/rpc", json=_rpc("SendMessage", {"tenant": "FuzePlan", "message": _msg()}), headers=_hdr()
    )
    assert r.status_code == 200
    assert r.json()["result"]["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_extended_card_on_per_product_pod_carries_the_same_endpoint(per_product_client):
    r = per_product_client.get("/extendedAgentCard?tenant=FuzePlan", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["supportedInterfaces"][0]["url"] == PER_PRODUCT_URL


def test_single_tenant_does_not_make_the_tenant_param_optional_on_rpc(per_product_client):
    """Documents a real single-tenant edge: card DISCOVERY infers the sole tenant, RPC
    does NOT. `SendMessage` with no `params.tenant` fails closed to a generic REJECTED
    even here.

    That is correct and deliberate, not a gap to paper over: the card always carries
    `AgentInterface.tenant` and A2A §4.4.6 requires the caller to echo it (the shipped
    `A2AClient` does so from the card automatically), so a compliant caller never hits
    this. It is called out because the rejection is intentionally indistinguishable from
    an authz denial (non-disclosure, authz.md §6), so a hand-rolled caller that forgets
    `tenant` will misread it as a permissions problem.
    """
    card = per_product_client.get("/.well-known/agent-card.json").json()
    tenant = card["supportedInterfaces"][0]["tenant"]

    without = per_product_client.post(
        "/rpc", json=_rpc("SendMessage", {"message": _msg()}), headers=_hdr()
    ).json()
    assert without["result"]["task"]["status"]["state"] == "TASK_STATE_REJECTED"

    with_tenant = per_product_client.post(
        "/rpc", json=_rpc("SendMessage", {"tenant": tenant, "message": _msg()}), headers=_hdr()
    ).json()
    assert with_tenant["result"]["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


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
