"""Unit tests for the A2A runtime tenant registration API
(izzywdev/FuzeAgent#203 slice 2 — ``a2a_tenant_registration.py``).

These mirror ``test_auth_authz.py`` / ``test_database_update_allowlist.py``'s approach:
a real JWT secret is configured before ``auth`` is imported (so verification runs
fail-closed), and the DB layer (``database.get_db_connection``, as imported into
``a2a_tenant_registration``) is replaced with an in-memory fake connection so these
run without a live Postgres. The router under test is the REAL router
(``a2a_tenant_registration.router``), not a hand-rolled mirror — only auth + DB are
faked.

Covers (tenant-registration.md §2-4):
  * tenant/repo mismatch vs. the authenticated caller -> 403, nothing written
  * missing repo claim on an otherwise-valid credential -> 403, nothing written
  * an invalid card (fails the Fuze profile) -> 422, nothing written
  * a non-in-cluster interface url on a non-external tenant -> 422
  * malformed / additional-property envelopes -> 422 (schema failure)
  * first registration -> 201 created:true, defaults applied
  * re-registration -> 200 created:false, updatedAt advances, createdAt preserved
  * GET /a2a/tenants with/without ?enabled=, and that it requires a service/admin
    credential (not an arbitrary product agent token)
  * the vendored schema copies have not drifted from the frozen contract
"""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure verification material BEFORE importing auth, so get_current_user runs in
# its prod-like (fail-closed) mode -- same pattern as test_auth_authz.py. Deliberately
# the SAME literal secret test_auth_authz.py / test_residual_authz.py use: each of
# these files captures `SECRET = os.environ["JWT_SECRET"]` once at import time, but
# pytest imports every test module (running this top-level code) during collection
# BEFORE any test function runs -- so whichever file's `importlib.reload(auth_module)`
# happens last during collection decides the value auth.py actually verifies against
# for the whole session. Sharing the literal (rather than inventing a new one, the
# way test_hierarchy_ws_authz.py's distinct secret does) sidesteps that collection-
# order hazard entirely instead of adding a new value that could collide with it.
os.environ["JWT_SECRET"] = (  # nosec B105 -- test-only fixture, not a real credential
    "test-secret-for-issue-6-authz"
)
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ.pop("AUTH_DISABLED", None)
os.environ.pop("JWT_AUDIENCE", None)
os.environ.pop("JWT_ISSUER", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth as auth_module  # noqa: E402

importlib.reload(auth_module)

import a2a_tenant_registration as reg_module  # noqa: E402

importlib.reload(reg_module)

SECRET = os.environ["JWT_SECRET"]
REPO = "izzywdev/FuzePlan"
TENANT = "FuzePlan"
IN_CLUSTER_URL = "http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc"
EXTERNAL_URL = "https://a2a.fuzeplan.prod.fuzefront.com/rpc"


def make_token(**claims) -> str:
    payload = {"sub": "ci-principal"}
    payload.update(claims)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def auth_header(**claims) -> dict:
    return {"Authorization": f"Bearer {make_token(**claims)}"}


def make_card(
    tenant: str = TENANT, url: str = IN_CLUSTER_URL, signed: bool = True
) -> dict:
    card = {
        "name": f"{tenant} agent",
        "description": f"Planning agent for {tenant}.",
        "provider": {"organization": "FuzeOne", "url": "https://github.com/izzywdev"},
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": url,
                "protocolBinding": "JSONRPC",
                "protocolVersion": "1.0",
                "tenant": tenant,
            }
        ],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "extendedAgentCard": True,
        },
        "securitySchemes": {
            "fuze-oidc": {
                "openIdConnectSecurityScheme": {
                    "openIdConnectUrl": "https://auth.prod.fuzefront.com/.well-known/openid-configuration"
                }
            }
        },
        "securityRequirements": [{"fuze-oidc": []}],
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "product-manager",
                "name": f"{tenant} product-manager",
                "description": "Turns requirements into tickets.",
                "tags": ["product-manager"],
            }
        ],
    }
    if signed:
        card["signatures"] = [
            {"protected": "eyJhbGciOiJFUzI1NiJ9", "signature": "PLACEHOLDER"}
        ]
    return card


def make_register_body(
    tenant: str = TENANT, repo: str = REPO, card: dict | None = None, **overrides
) -> dict:
    body = {
        "tenant": tenant,
        "repo": repo,
        "entryRole": "product-manager",
        "servingRoles": ["product-manager"],
        "card": card if card is not None else make_card(tenant=tenant),
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------


class FakeConnection:
    """In-memory stand-in for the asyncpg connection ``a2a_tenant_registration`` uses.

    Emulates the real ``INSERT ... ON CONFLICT (tenant) DO UPDATE`` semantics closely
    enough to exercise the idempotent-upsert contract (created flag, createdAt
    preserved, updatedAt advanced) without a live Postgres. Timestamps are a
    monotonic counter rather than wall-clock so "did updatedAt advance" assertions
    are never flaky.
    """

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._tick = 0

    def _now(self) -> datetime:
        self._tick += 1
        return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self._tick)

    def seed(self, **row) -> None:
        row.setdefault("created_at", self._now())
        row.setdefault("updated_at", row["created_at"])
        self.rows[row["tenant"]] = row

    async def fetchrow(self, query: str, *params):
        assert "a2a_tenants" in query
        (
            tenant,
            repo,
            ref,
            entry_role,
            serving_roles,
            external,
            provider,
            card,
            enabled,
        ) = params
        existing = self.rows.get(tenant)
        created = existing is None
        # A single NOW() per statement, exactly like Postgres: on INSERT both
        # created_at/updated_at DEFAULT to the same transaction-time NOW(), so a
        # freshly inserted row has createdAt == updatedAt; on UPDATE the BEFORE
        # UPDATE trigger advances updated_at while created_at is left untouched.
        now = self._now()
        created_at = existing["created_at"] if existing else now
        row = {
            "tenant": tenant,
            "repo": repo,
            "ref": ref,
            "entry_role": entry_role,
            "serving_roles": serving_roles,
            "external": external,
            "provider": provider,
            "card": card,
            "enabled": enabled,
            "created_at": created_at,
            "updated_at": now,
            "created": created,
        }
        self.rows[tenant] = row
        return dict(row)

    async def fetch(self, query: str, *params):
        rows = list(self.rows.values())
        if "WHERE enabled" in query:
            (enabled,) = params
            rows = [r for r in rows if r["enabled"] == enabled]
        rows.sort(key=lambda r: r["tenant"])
        return [dict(r) for r in rows]


def _fake_db_connection(conn: FakeConnection):
    @asynccontextmanager
    async def _cm():
        yield conn

    return _cm


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(reg_module.router)
    return app


@pytest.fixture
def fake_conn():
    return FakeConnection()


@pytest.fixture
def client(monkeypatch, fake_conn):
    monkeypatch.setattr(reg_module, "get_db_connection", _fake_db_connection(fake_conn))
    return TestClient(build_app())


# ---------------------------------------------------------------------------
# §3 fail-closed self-registration identity binding
# ---------------------------------------------------------------------------


def test_register_repo_mismatch_is_403_and_not_written(client, fake_conn):
    body = make_register_body(tenant=TENANT, repo=REPO)
    r = client.post(
        "/a2a/tenants/register",
        json=body,
        headers=auth_header(repo="izzywdev/SomeoneElse"),
    )
    assert r.status_code == 403
    assert fake_conn.rows == {}


def test_register_tenant_not_derivable_from_repo_is_403_and_not_written(
    client, fake_conn
):
    # repo matches the caller, but the tenant slug does not match the repo segment.
    body = make_register_body(
        tenant="NotFuzePlan", repo=REPO, card=make_card(tenant="NotFuzePlan")
    )
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 403
    assert fake_conn.rows == {}


def test_register_no_repo_claim_on_credential_is_403_and_not_written(client, fake_conn):
    body = make_register_body()
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header())
    assert r.status_code == 403
    assert fake_conn.rows == {}


def test_register_without_token_is_401(client, fake_conn):
    body = make_register_body()
    r = client.post("/a2a/tenants/register", json=body)
    assert r.status_code == 401
    assert fake_conn.rows == {}


# ---------------------------------------------------------------------------
# §4 card validation
# ---------------------------------------------------------------------------


def test_register_unsigned_card_is_422_and_not_written(client, fake_conn):
    body = make_register_body(card=make_card(signed=False))
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 422
    assert fake_conn.rows == {}


def test_register_card_tenant_mismatch_is_422_and_not_written(client, fake_conn):
    # The card's own interface.tenant disagrees with the record tenant.
    card = make_card(tenant=TENANT)
    card["supportedInterfaces"][0]["tenant"] = "SomeOtherTenant"
    body = make_register_body(card=card)
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 422
    assert fake_conn.rows == {}


def test_register_non_in_cluster_url_when_not_external_is_422(client, fake_conn):
    body = make_register_body(card=make_card(url=EXTERNAL_URL), external=False)
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 422
    assert fake_conn.rows == {}


def test_register_external_tenant_accepts_https_url(client, fake_conn):
    body = make_register_body(card=make_card(url=EXTERNAL_URL), external=True)
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 201
    assert r.json()["record"]["external"] is True


# ---------------------------------------------------------------------------
# Envelope / schema validation (RegisterTenantRequest)
# ---------------------------------------------------------------------------


def test_register_missing_required_field_is_422_and_not_written(client, fake_conn):
    body = make_register_body()
    del body["servingRoles"]
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 422
    assert fake_conn.rows == {}


def test_register_rejects_client_supplied_timestamps(client, fake_conn):
    body = make_register_body()
    body["createdAt"] = "2020-01-01T00:00:00Z"
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 422
    assert fake_conn.rows == {}


# ---------------------------------------------------------------------------
# §2 idempotent-upsert semantics
# ---------------------------------------------------------------------------


def test_first_register_is_201_created_true_with_defaults(client, fake_conn):
    body = make_register_body()
    r = client.post("/a2a/tenants/register", json=body, headers=auth_header(repo=REPO))
    assert r.status_code == 201
    data = r.json()
    assert data["created"] is True
    record = data["record"]
    assert record["tenant"] == TENANT
    assert record["ref"] == "main"
    assert record["external"] is False
    assert record["enabled"] is True
    assert record["createdAt"] == record["updatedAt"]


def test_reregister_is_200_created_false_updated_at_advances_created_at_preserved(
    client, fake_conn
):
    headers = auth_header(repo=REPO)
    first = client.post(
        "/a2a/tenants/register", json=make_register_body(), headers=headers
    ).json()["record"]

    changed_body = make_register_body(entryRole="product-manager", enabled=False)
    r2 = client.post("/a2a/tenants/register", json=changed_body, headers=headers)
    assert r2.status_code == 200
    second = r2.json()
    assert second["created"] is False
    record = second["record"]
    assert record["createdAt"] == first["createdAt"]
    assert record["updatedAt"] != first["updatedAt"]
    assert record["enabled"] is False


def test_concurrent_reregistration_converges_to_single_row(client, fake_conn):
    """Registering the same tenant twice must never create two rows."""
    headers = auth_header(repo=REPO)
    for _ in range(3):
        client.post("/a2a/tenants/register", json=make_register_body(), headers=headers)
    assert list(fake_conn.rows.keys()) == [TENANT]


# ---------------------------------------------------------------------------
# GET /a2a/tenants
# ---------------------------------------------------------------------------


def _seed_two_tenants(fake_conn):
    fake_conn.seed(
        tenant="FuzePlan",
        repo="izzywdev/FuzePlan",
        ref="main",
        entry_role="product-manager",
        serving_roles=["product-manager"],
        external=False,
        provider=None,
        card=make_card(tenant="FuzePlan"),
        enabled=True,
    )
    fake_conn.seed(
        tenant="FuzeKeys",
        repo="izzywdev/FuzeKeys",
        ref="main",
        entry_role="keys-admin",
        serving_roles=["keys-admin"],
        external=False,
        provider=None,
        card=make_card(tenant="FuzeKeys"),
        enabled=False,
    )


def test_list_tenants_requires_service_or_admin_credential(client, fake_conn):
    _seed_two_tenants(fake_conn)
    r = client.get("/a2a/tenants", headers=auth_header(repo=REPO))
    assert r.status_code == 403


def test_list_tenants_without_filter_returns_all_as_operator(client, fake_conn):
    _seed_two_tenants(fake_conn)
    r = client.get("/a2a/tenants", headers=auth_header(is_admin=True))
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert {t["tenant"] for t in body["tenants"]} == {"FuzePlan", "FuzeKeys"}


def test_list_tenants_enabled_filter_as_service_principal(client, fake_conn):
    _seed_two_tenants(fake_conn)
    r = client.get("/a2a/tenants?enabled=true", headers=auth_header(is_service=True))
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["tenants"][0]["tenant"] == "FuzePlan"
    assert all(t["enabled"] for t in body["tenants"])


def test_list_tenants_empty_registry(client, fake_conn):
    r = client.get("/a2a/tenants", headers=auth_header(is_admin=True))
    assert r.status_code == 200
    assert r.json() == {"tenants": [], "count": 0}


# ---------------------------------------------------------------------------
# Vendored schema copies must not drift from the frozen contract
# ---------------------------------------------------------------------------


def test_vendored_schemas_match_frozen_contract():
    repo_root = Path(__file__).resolve().parents[3]
    frozen_dir = repo_root / "agent-templates" / "contracts" / "a2a" / "v1" / "schema"
    for name in (
        "tenant-registration.schema.json",
        "agent-card.schema.json",
        "fuze-profile.schema.json",
    ):
        vendored = (reg_module.SCHEMA_DIR / name).read_bytes()
        frozen = (frozen_dir / name).read_bytes()
        assert (
            vendored == frozen
        ), f"{name}: vendored copy has drifted from the frozen contract"
