"""
Regression test: hierarchy_endpoints.py root /ws WebSocket connect-time auth.

Gap closed in PR #7 (izzywdev/FuzeAgent issue #6 re-verify
https://github.com/izzywdev/FuzeAgent/pull/7#pullrequestreview-4589798014):

  The root ``hierarchy_endpoints.py`` ``/ws`` handler called
  ``manager.connect()`` (which calls ``websocket.accept()``) on ANY socket
  before performing any authentication.  The app-level
  ``dependencies=[Depends(get_current_user)]`` is a *no-op* for WebSocket
  routes — Starlette only runs those deps for HTTP scopes. The fix mirrors
  the pattern used by all WS handlers in services/orchestrator/main.py:
  call ``authenticate_websocket()`` BEFORE ``manager.connect()``/``accept()``.

This test drives the REAL ``hierarchy_endpoints.app`` (not a synthetic
router), so it would have caught the original gap and will catch any
regression.

The ``asyncpg`` pool is stubbed out with a MagicMock so the test runs
without a live database (the /ws endpoint never touches the pool; the mock
just satisfies the ``startup`` event handler).
"""

from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Environment — set BEFORE importing auth/hierarchy_endpoints so the module
# evaluates with the correct JWT config (fail-closed, no bypass).
# ---------------------------------------------------------------------------
os.environ["JWT_SECRET"] = "test-secret-hierarchy-ws-authz"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ.pop("AUTH_DISABLED", None)
os.environ.pop("JWT_AUDIENCE", None)
os.environ.pop("JWT_ISSUER", None)
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5434/ai_context"
os.environ["ORCHESTRATOR_URL"] = "http://localhost:8000"

# Add repo root to sys.path so ``import hierarchy_endpoints`` resolves.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Add orchestrator service dir so ``import auth`` resolves inside hierarchy_endpoints.
_SVC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SVC_DIR not in sys.path:
    sys.path.insert(0, _SVC_DIR)

# ---------------------------------------------------------------------------
# Reload auth with the test JWT secret before hierarchy_endpoints imports it.
# ---------------------------------------------------------------------------
import auth as auth_module  # noqa: E402

importlib.reload(auth_module)

# Stub asyncpg.create_pool so the startup handler doesn't need a real DB.
import asyncpg  # noqa: E402

_mock_pool = MagicMock()
_mock_pool.close = AsyncMock()
asyncpg.create_pool = AsyncMock(return_value=_mock_pool)  # type: ignore[attr-defined]

# Now import the REAL hierarchy_endpoints app (it uses the already-loaded auth).
import hierarchy_endpoints  # noqa: E402

importlib.reload(hierarchy_endpoints)
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from hierarchy_endpoints import app  # noqa: E402

SECRET = os.environ["JWT_SECRET"]


def make_token(**extra) -> str:
    payload = {"sub": "user-1"}
    payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm="HS256")


@pytest.fixture(scope="module")
def hier_client():
    """TestClient wrapping the REAL hierarchy_endpoints.app."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Unauthenticated connect MUST be rejected (close 1008 = WebSocketDisconnect)
# ---------------------------------------------------------------------------


def test_hierarchy_ws_no_token_is_rejected(hier_client):
    """Connecting to /ws without any token must be refused (1008 / disconnect)."""
    with pytest.raises(WebSocketDisconnect):
        with hier_client.websocket_connect("/ws"):
            pass  # should not reach here


def test_hierarchy_ws_invalid_token_is_rejected(hier_client):
    """A malformed/invalid token must be refused (1008 / disconnect)."""
    with pytest.raises(WebSocketDisconnect):
        with hier_client.websocket_connect("/ws?token=this-is-not-a-jwt"):
            pass


# ---------------------------------------------------------------------------
# 2. Valid token → connection accepted
# ---------------------------------------------------------------------------


def test_hierarchy_ws_valid_token_query_param_connects(hier_client):
    """A valid bearer token in the query string must allow the WS connection."""
    token = make_token()
    # The handler sends "pong" on "ping"; just connecting (and receiving the
    # first message) proves the socket was accepted.
    with hier_client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text("ping")
        response = ws.receive_text()
    assert response == "pong"


def test_hierarchy_ws_valid_token_subprotocol_connects(hier_client):
    """A valid bearer token via Sec-WebSocket-Protocol must allow the connection."""
    token = make_token()
    with hier_client.websocket_connect("/ws", subprotocols=["bearer", token]) as ws:
        ws.send_text("ping")
        response = ws.receive_text()
    assert response == "pong"


def test_hierarchy_ws_valid_token_auth_header_connects(hier_client):
    """A valid bearer token in the Authorization header must allow the connection."""
    token = make_token()
    with hier_client.websocket_connect("/ws", headers={"Authorization": f"Bearer {token}"}) as ws:
        ws.send_text("ping")
        response = ws.receive_text()
    assert response == "pong"
