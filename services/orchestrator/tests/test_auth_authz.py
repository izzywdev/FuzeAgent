"""
Regression tests for the authentication / authorization remediation
(izzywdev/FuzeAgent issue #6).

These exercise the real ``auth.py`` dependencies (``get_current_user``,
``require_user``, ``require_admin``, ``require_org_access``) against a minimal
FastAPI app that mirrors the dangerous-endpoint shapes locked in the
orchestrator. They run without a database so they verify the *security* logic
in isolation:

  * 401 when no/invalid bearer token is presented (CRITICAL-1).
  * 403 on object-level org mismatch (HIGH-2 / BOLA) and on admin-only
    migration control by a non-admin (HIGH-1).
  * 200 for the authorized principal.
  * public allowlist (health) stays reachable without a token.
  * mass-assignment: unknown body fields are rejected (MEDIUM-1).

A JWT secret is configured *before* importing ``auth`` so signature
verification is active.
"""

import importlib
import os
import sys

import pytest

# Configure verification material before importing the auth module so that
# get_current_user runs in its prod-like (fail-closed) mode.
os.environ["JWT_SECRET"] = "test-secret-for-issue-6-authz"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ.pop("AUTH_DISABLED", None)
os.environ.pop("JWT_AUDIENCE", None)
os.environ.pop("JWT_ISSUER", None)

# Ensure the orchestrator package dir is importable (tests run from there).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth as auth_module
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import BaseModel, ConfigDict

importlib.reload(auth_module)
from auth import require_admin  # noqa: E402
from auth import (
    CurrentUser,
    get_current_user,
    require_org_access,
    require_user,
)

SECRET = os.environ["JWT_SECRET"]
ORG_A = "11111111-1111-1111-1111-111111111111"
ORG_B = "22222222-2222-2222-2222-222222222222"


def make_token(**claims) -> str:
    payload = {"sub": "user-1"}
    payload.update(claims)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def auth_header(**claims):
    return {"Authorization": f"Bearer {make_token(**claims)}"}


# ---------------------------------------------------------------------------
# Minimal app mirroring the locked endpoint shapes.
# ---------------------------------------------------------------------------


class ExecBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str


def build_app() -> FastAPI:
    app = FastAPI(dependencies=[Depends(get_current_user)])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/sandboxes/{sandbox_id}/execute")
    async def execute(
        sandbox_id: str, body: ExecBody, user: CurrentUser = Depends(require_user)
    ):
        return {"sandbox_id": sandbox_id, "command": body.command, "user": user.id}

    @app.post("/organizations/{org_id}/credentials")
    async def store_creds(org_id: str, user: CurrentUser = Depends(require_user)):
        require_org_access(org_id, user)
        return {"org_id": org_id, "stored": True}

    @app.post("/migrations/apply")
    async def migrate(user: CurrentUser = Depends(require_admin)):
        return {"applied": True}

    return app


@pytest.fixture
def client():
    return TestClient(build_app())


# ---------------------------------------------------------------------------
# CRITICAL-1: authN required on dangerous endpoints
# ---------------------------------------------------------------------------


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_execute_without_token_is_401(client):
    r = client.post("/sandboxes/abc/execute", json={"command": "ls"})
    assert r.status_code == 401


def test_execute_with_invalid_token_is_401(client):
    r = client.post(
        "/sandboxes/abc/execute",
        json={"command": "ls"},
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert r.status_code == 401


def test_execute_with_token_signed_by_wrong_secret_is_401(client):
    bad = jwt.encode({"sub": "u"}, "the-wrong-secret", algorithm="HS256")
    r = client.post(
        "/sandboxes/abc/execute",
        json={"command": "ls"},
        headers={"Authorization": f"Bearer {bad}"},
    )
    assert r.status_code == 401


def test_execute_with_valid_token_is_200(client):
    r = client.post(
        "/sandboxes/abc/execute",
        json={"command": "ls"},
        headers=auth_header(),
    )
    assert r.status_code == 200
    assert r.json()["command"] == "ls"


# ---------------------------------------------------------------------------
# MEDIUM-1: mass assignment rejected
# ---------------------------------------------------------------------------


def test_execute_rejects_unknown_body_fields(client):
    r = client.post(
        "/sandboxes/abc/execute",
        json={"command": "ls", "evil": "injected"},
        headers=auth_header(),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# CRITICAL-2 / HIGH-2: object-level authz (BOLA)
# ---------------------------------------------------------------------------


def test_credentials_requires_token(client):
    assert client.post(f"/organizations/{ORG_A}/credentials").status_code == 401


def test_credentials_non_member_is_403(client):
    # Token grants ORG_B only; request targets ORG_A.
    r = client.post(
        f"/organizations/{ORG_A}/credentials",
        headers=auth_header(organizations=[ORG_B]),
    )
    assert r.status_code == 403


def test_credentials_member_is_200(client):
    r = client.post(
        f"/organizations/{ORG_A}/credentials",
        headers=auth_header(organizations=[ORG_A]),
    )
    assert r.status_code == 200


def test_credentials_admin_bypasses_org_check(client):
    r = client.post(
        f"/organizations/{ORG_A}/credentials",
        headers=auth_header(is_admin=True),
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# HIGH-1: migration control restricted to admin/service principal
# ---------------------------------------------------------------------------


def test_migrations_requires_token(client):
    assert client.post("/migrations/apply").status_code == 401


def test_migrations_non_admin_is_403(client):
    r = client.post("/migrations/apply", headers=auth_header())
    assert r.status_code == 403


def test_migrations_admin_is_200(client):
    r = client.post("/migrations/apply", headers=auth_header(roles=["admin"]))
    assert r.status_code == 200


def test_migrations_service_principal_is_200(client):
    r = client.post("/migrations/apply", headers=auth_header(is_service=True))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# CurrentUser unit checks
# ---------------------------------------------------------------------------


def test_current_user_org_claim_parsing_from_string():
    u = CurrentUser({"sub": "u", "organizations": f"{ORG_A} {ORG_B}"})
    assert u.can_access_org(ORG_A)
    assert u.can_access_org(ORG_B)
    assert not u.can_access_org("33333333-3333-3333-3333-333333333333")


def test_current_user_admin_role_detected():
    assert CurrentUser({"sub": "u", "roles": ["Admin"]}).is_admin
    assert CurrentUser({"sub": "u", "is_admin": True}).is_admin
    assert not CurrentUser({"sub": "u", "roles": ["viewer"]}).is_admin
