"""
Regression tests for the *residual* auth/authorization fixes on PR #7
(izzywdev/FuzeAgent issue #6, re-verification review
https://github.com/izzywdev/FuzeAgent/pull/7#pullrequestreview-4587291559).

Covers the three residuals:

  1. The actually-published app surface requires authN. The root
     docker-compose.yml used to publish ``simple_main:app`` with zero authN and
     wildcard CORS. simple_main.py now mounts the SAME global
     ``Depends(get_current_user)`` and a non-wildcard env CORS allowlist — so an
     unauthenticated request to a non-public route is 401, and CORS does not
     reflect ``*`` with credentials.

  2. Object-level BOLA on the long-tail endpoints: file-operations
     approve/rollback (task -> agent -> org) and the A2A endpoints
     (agent -> org / a2a_task -> agent -> org). A non-owner is 403.

  3. WebSocket connect-time auth: ``authenticate_websocket`` rejects an
     unauthenticated WS handshake (close 1008) — app-level deps don't cover WS.

These run without a database: the BOLA tests mirror the locked endpoint shapes
(the org-resolution is monkeypatched to a fixed org so the *authorization* logic
is what is exercised), matching test_auth_authz.py's approach.
"""

import importlib
import os
import sys

import pytest

# Configure verification material BEFORE importing auth so it runs fail-closed.
os.environ["JWT_SECRET"] = "test-secret-for-issue-6-authz"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ.pop("AUTH_DISABLED", None)
os.environ.pop("JWT_AUDIENCE", None)
os.environ.pop("JWT_ISSUER", None)
# Non-wildcard CORS allowlist for the published-app test.
os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:3000,http://localhost:3031"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth as auth_module  # noqa: E402
from fastapi import Body, Depends, FastAPI, Path, WebSocket  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

importlib.reload(auth_module)
from auth import (CurrentUser, authenticate_websocket,  # noqa: E402
                  get_current_user, require_org_access, require_user)

SECRET = os.environ["JWT_SECRET"]
ORG_A = "11111111-1111-1111-1111-111111111111"
ORG_B = "22222222-2222-2222-2222-222222222222"


def make_token(**claims) -> str:
    payload = {"sub": "user-1"}
    payload.update(claims)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def auth_header(**claims):
    return {"Authorization": f"Bearer {make_token(**claims)}"}


# ===========================================================================
# 1. The actually-published app (simple_main) requires authN + non-wildcard CORS
# ===========================================================================


@pytest.fixture(scope="module")
def published_client():
    import simple_main  # imported with the global auth dependency mounted

    return TestClient(simple_main.app)


def test_published_health_is_public(published_client):
    assert published_client.get("/health").status_code == 200


def test_published_agents_without_token_is_401(published_client):
    # /agents is NOT on the public allowlist -> must be 401 unauthenticated.
    r = published_client.get("/agents")
    assert r.status_code == 401


def test_published_create_agent_without_token_is_401(published_client):
    r = published_client.post("/agents", json={"name": "x", "type": "dev"})
    assert r.status_code == 401


def test_published_agents_with_valid_token_is_not_401(published_client):
    r = published_client.get("/agents", headers=auth_header())
    assert r.status_code != 401


def test_published_cors_does_not_reflect_wildcard_with_credentials(published_client):
    # An origin NOT on the allowlist must not be echoed back as allowed.
    r = published_client.get("/health", headers={"Origin": "https://evil.example.com"})
    allow_origin = r.headers.get("access-control-allow-origin")
    assert allow_origin != "*"
    assert allow_origin != "https://evil.example.com"


def test_published_cors_allows_configured_origin(published_client):
    r = published_client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ===========================================================================
# 2. Object-level BOLA on the long-tail endpoints (file-ops + A2A)
# ===========================================================================
#
# These mirror the real handler shapes. The org-resolution helper is stubbed to
# return a fixed owning org (ORG_A) so the AUTHORIZATION decision is what's
# under test (the real handlers resolve the same org via the DB).


def build_bola_app() -> FastAPI:
    app = FastAPI(dependencies=[Depends(get_current_user)])

    OWNING_ORG = ORG_A

    async def _authorize_task_org(task_id: str, user: CurrentUser) -> None:
        # mirrors main._authorize_task_org once the org is resolved
        require_org_access(OWNING_ORG, user)

    async def _authorize_agent_org(agent_id: str, user: CurrentUser):
        # mirrors main_with_hierarchy._authorize_agent_org once resolved
        require_org_access(OWNING_ORG, user)
        return {"id": agent_id, "organization_id": OWNING_ORG}

    # ---- file-operations approve / rollback ----
    @app.post("/tasks/{task_id}/file-operations/{batch_id}/approve")
    async def approve(
        task_id: str, batch_id: str, user: CurrentUser = Depends(require_user)
    ):
        await _authorize_task_org(task_id, user)
        return {"task_id": task_id, "batch_id": batch_id, "approved": True}

    @app.post("/tasks/{task_id}/file-operations/{batch_id}/rollback")
    async def rollback(
        task_id: str, batch_id: str, user: CurrentUser = Depends(require_user)
    ):
        await _authorize_task_org(task_id, user)
        return {"task_id": task_id, "batch_id": batch_id, "status": "rolled_back"}

    # ---- A2A: agent card / send message / tasks / messages / task status ----
    @app.get("/a2a/agents/{agent_id}/card")
    async def agent_card(agent_id: str, user: CurrentUser = Depends(require_user)):
        await _authorize_agent_org(agent_id, user)
        return {"agent_id": agent_id}

    @app.post("/a2a/agents/{sender_agent_id}/message")
    async def send_message(
        sender_agent_id: str,
        message_data: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ):
        await _authorize_agent_org(sender_agent_id, user)
        return {"status": "sent"}

    @app.get("/a2a/agents/{agent_id}/tasks")
    async def agent_tasks(agent_id: str, user: CurrentUser = Depends(require_user)):
        await _authorize_agent_org(agent_id, user)
        return {"agent_id": agent_id, "tasks": []}

    @app.get("/a2a/agents/{agent_id}/messages")
    async def agent_messages(agent_id: str, user: CurrentUser = Depends(require_user)):
        await _authorize_agent_org(agent_id, user)
        return {"agent_id": agent_id, "messages": []}

    @app.put("/a2a/tasks/{task_id}/status")
    async def task_status(
        task_id: str,
        status_data: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ):
        await _authorize_task_org(task_id, user)
        return {"task_id": task_id, "status": "updated"}

    return app


@pytest.fixture
def bola_client():
    return TestClient(build_bola_app())


# ---- file-operations ----


def test_approve_requires_token(bola_client):
    assert bola_client.post("/tasks/t1/file-operations/b1/approve").status_code == 401


def test_approve_non_owner_is_403(bola_client):
    r = bola_client.post(
        "/tasks/t1/file-operations/b1/approve",
        headers=auth_header(organizations=[ORG_B]),
    )
    assert r.status_code == 403


def test_approve_owner_is_200(bola_client):
    r = bola_client.post(
        "/tasks/t1/file-operations/b1/approve",
        headers=auth_header(organizations=[ORG_A]),
    )
    assert r.status_code == 200


def test_rollback_non_owner_is_403(bola_client):
    r = bola_client.post(
        "/tasks/t1/file-operations/b1/rollback",
        headers=auth_header(organizations=[ORG_B]),
    )
    assert r.status_code == 403


def test_rollback_owner_is_200(bola_client):
    r = bola_client.post(
        "/tasks/t1/file-operations/b1/rollback",
        headers=auth_header(organizations=[ORG_A]),
    )
    assert r.status_code == 200


# ---- A2A ----


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/a2a/agents/ag1/card"),
        ("get", "/a2a/agents/ag1/tasks"),
        ("get", "/a2a/agents/ag1/messages"),
    ],
)
def test_a2a_get_requires_token(bola_client, method, path):
    assert getattr(bola_client, method)(path).status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/a2a/agents/ag1/card"),
        ("get", "/a2a/agents/ag1/tasks"),
        ("get", "/a2a/agents/ag1/messages"),
    ],
)
def test_a2a_get_non_owner_is_403(bola_client, method, path):
    r = getattr(bola_client, method)(path, headers=auth_header(organizations=[ORG_B]))
    assert r.status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/a2a/agents/ag1/card"),
        ("get", "/a2a/agents/ag1/tasks"),
        ("get", "/a2a/agents/ag1/messages"),
    ],
)
def test_a2a_get_owner_is_200(bola_client, method, path):
    r = getattr(bola_client, method)(path, headers=auth_header(organizations=[ORG_A]))
    assert r.status_code == 200


def test_a2a_send_message_non_owner_is_403(bola_client):
    r = bola_client.post(
        "/a2a/agents/ag1/message",
        json={"recipient_agent_id": "ag2", "content": "hi"},
        headers=auth_header(organizations=[ORG_B]),
    )
    assert r.status_code == 403


def test_a2a_send_message_owner_is_200(bola_client):
    r = bola_client.post(
        "/a2a/agents/ag1/message",
        json={"recipient_agent_id": "ag2", "content": "hi"},
        headers=auth_header(organizations=[ORG_A]),
    )
    assert r.status_code == 200


def test_a2a_update_task_status_non_owner_is_403(bola_client):
    r = bola_client.put(
        "/a2a/tasks/t1/status",
        json={"status": "completed"},
        headers=auth_header(organizations=[ORG_B]),
    )
    assert r.status_code == 403


def test_a2a_update_task_status_owner_is_200(bola_client):
    r = bola_client.put(
        "/a2a/tasks/t1/status",
        json={"status": "completed"},
        headers=auth_header(organizations=[ORG_A]),
    )
    assert r.status_code == 200


def test_a2a_admin_bypasses_org_check(bola_client):
    r = bola_client.get("/a2a/agents/ag1/card", headers=auth_header(is_admin=True))
    assert r.status_code == 200


# ===========================================================================
# 3. WebSocket connect-time auth (app deps don't cover WS)
# ===========================================================================


def build_ws_app() -> FastAPI:
    app = FastAPI(dependencies=[Depends(get_current_user)])

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        user = await authenticate_websocket(websocket)
        if user is None:
            return
        await websocket.accept()
        await websocket.send_json({"hello": user.id})
        await websocket.close()

    @app.websocket("/ws/organization/{organization_id}/updates")
    async def ws_org(websocket: WebSocket, organization_id: str):
        user = await authenticate_websocket(websocket)
        if user is None:
            return
        if not user.can_access_org(str(organization_id)):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        await websocket.send_json({"org": organization_id})
        await websocket.close()

    return app


@pytest.fixture
def ws_client():
    return TestClient(build_ws_app())


def test_ws_without_token_is_rejected(ws_client):
    with pytest.raises(WebSocketDisconnect):
        with ws_client.websocket_connect("/ws"):
            pass  # handshake should be refused (close 1008) before accept


def test_ws_with_invalid_token_is_rejected(ws_client):
    with pytest.raises(WebSocketDisconnect):
        with ws_client.websocket_connect("/ws?token=not-a-jwt"):
            pass


def test_ws_with_valid_token_query_param_connects(ws_client):
    token = make_token()
    with ws_client.websocket_connect(f"/ws?token={token}") as ws:
        data = ws.receive_json()
        assert data["hello"] == "user-1"


def test_ws_with_valid_token_subprotocol_connects(ws_client):
    token = make_token()
    with ws_client.websocket_connect("/ws", subprotocols=["bearer", token]) as ws:
        data = ws.receive_json()
        assert data["hello"] == "user-1"


def test_ws_org_non_member_is_rejected(ws_client):
    token = make_token(organizations=[ORG_B])
    with pytest.raises(WebSocketDisconnect):
        with ws_client.websocket_connect(
            f"/ws/organization/{ORG_A}/updates?token={token}"
        ):
            pass


def test_ws_org_member_connects(ws_client):
    token = make_token(organizations=[ORG_A])
    with ws_client.websocket_connect(
        f"/ws/organization/{ORG_A}/updates?token={token}"
    ) as ws:
        data = ws.receive_json()
        assert data["org"] == ORG_A
