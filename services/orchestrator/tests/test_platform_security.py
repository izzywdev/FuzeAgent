"""FuzeFront Security API migration — identity and authorization come from the platform.

These tests pin the behaviour that makes FuzeAgent provider-agnostic:

  1. ``fuze_security`` speaks ONLY the published FuzeFront Security contract paths
     (``/v1/security/session``, ``/authz/check``, ``/authz/bulk-check``,
     ``/authz/permissions``) and never any identity/policy vendor.
  2. Every decision is FAIL-CLOSED — transport error, timeout, 4xx/5xx, malformed
     body, or a misaligned bulk response all deny.
  3. ``auth.get_current_user`` resolves the caller through the platform when
     ``FUZEFRONT_SECURITY_BASE_URL`` is set, and needs NO local signing key to do it.
  4. Legacy mode (platform unset) keeps the previous local-verification behaviour, so
     standalone deployments lose nothing.

No network is touched: an ``httpx.MockTransport`` is injected via
``fuze_security.client_factory``.
"""

import json
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fuze_security  # noqa: E402

BASE = "http://fuzefront.test/api"
SECURITY = f"{BASE}/v1/security"

USER_ID = "user-42"
TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "22222222-2222-2222-2222-222222222222"
LEGACY_SECRET = "legacy-mode-test-secret"  # nosec B105 - test fixture, not a credential

IDENTITY = {
    "userId": USER_ID,
    "tenantId": TENANT,
    "roles": ["operator"],
    "email": "agent-operator@example.com",
    "authMode": "federated-jwks",
    "issuedAt": 1700000000,
    "expiresAt": 1700003600,
    "issuer": "fuzefront",
}


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def install_transport(monkeypatch, handler):
    """Point ``fuze_security`` at a MockTransport and configure the base URL."""
    monkeypatch.setenv("FUZEFRONT_SECURITY_BASE_URL", BASE)
    monkeypatch.setattr(
        fuze_security,
        "client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def recording_handler(routes, seen):
    """Build a handler that records requests and replies from ``routes``."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        key = f"{request.method} {request.url.path}"
        responder = routes.get(key)
        if responder is None:
            return httpx.Response(404, json={"error": "no route"})
        return responder(request)

    return handler


# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------


def test_not_configured_without_base_url(monkeypatch):
    monkeypatch.delenv("FUZEFRONT_SECURITY_BASE_URL", raising=False)
    assert fuze_security.is_configured() is False
    assert fuze_security.base_url() is None


def test_configured_with_base_url(monkeypatch):
    monkeypatch.setenv("FUZEFRONT_SECURITY_BASE_URL", BASE + "/")
    assert fuze_security.is_configured() is True
    # Trailing slash normalized so paths do not double up.
    assert fuze_security.base_url() == BASE


def test_no_vendor_name_in_the_client_source():
    """The whole point of the migration: no identity/policy vendor is named here."""
    with open(fuze_security.__file__, "r", encoding="utf-8") as handle:
        source = handle.read().lower()
    for vendor in ("authentik", "permit.io", "permitio", "keycloak", "auth0", "okta"):
        assert vendor not in source, f"{vendor} must not appear in fuze_security.py"


# ---------------------------------------------------------------------------
# 2. Session resolution — GET /v1/security/session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_returns_normalized_identity(monkeypatch):
    seen = []
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200, json={"identity": IDENTITY, "user": {"id": USER_ID}}
                )
            },
            seen,
        ),
    )

    identity = await fuze_security.get_session("caller-token")

    assert identity is not None
    assert identity.userId == USER_ID
    assert identity.tenantId == TENANT
    assert identity.roles == ["operator"]
    # The caller's own token is forwarded — the platform decides for the real subject.
    assert seen[0].headers["authorization"] == "Bearer caller-token"


@pytest.mark.asyncio
async def test_get_session_denies_on_401(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {"GET /api/v1/security/session": lambda r: httpx.Response(401)}, []
        ),
    )
    assert await fuze_security.get_session("bad-token") is None


@pytest.mark.asyncio
async def test_get_session_denies_on_transport_error(monkeypatch):
    def boom(request):
        raise httpx.ConnectError("security service unreachable", request=request)

    install_transport(monkeypatch, boom)
    assert await fuze_security.get_session("any-token") is None


@pytest.mark.asyncio
async def test_get_session_denies_on_malformed_body(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200, content=b"not-json"
                )
            },
            [],
        ),
    )
    assert await fuze_security.get_session("any-token") is None


@pytest.mark.asyncio
async def test_get_session_denies_identity_without_subject(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200,
                    json={"identity": {"userId": "", "tenantId": None, "roles": []}},
                )
            },
            [],
        ),
    )
    assert await fuze_security.get_session("any-token") is None


# ---------------------------------------------------------------------------
# 3. Authorization — POST /v1/security/authz/check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authz_check_sends_bare_policy_keys(monkeypatch):
    seen = []
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "POST /api/v1/security/authz/check": lambda r: httpx.Response(
                    200, json={"allow": True}
                )
            },
            seen,
        ),
    )

    allowed = await fuze_security.authz_check(
        subject=USER_ID,
        tenant=TENANT,
        resource="Agent",
        action="deploy",
        resource_key="agent-7",
        token="caller-token",
    )

    assert allowed is True
    body = json.loads(seen[0].content)
    # Exactly the shape of the contract's AuthzCheckRequest, with FuzeAgent's own
    # bare keys from registration/policy.json.
    assert body == {
        "subject": USER_ID,
        "tenant": TENANT,
        "resource": {"type": "Agent", "key": "agent-7"},
        "action": "deploy",
    }


@pytest.mark.asyncio
async def test_authz_check_denies_when_allow_is_false(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "POST /api/v1/security/authz/check": lambda r: httpx.Response(
                    200, json={"allow": False}
                )
            },
            [],
        ),
    )
    assert (
        await fuze_security.authz_check(
            subject=USER_ID, tenant=TENANT, resource="Organization", action="delete"
        )
        is False
    )


@pytest.mark.asyncio
async def test_authz_check_denies_on_server_error(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {"POST /api/v1/security/authz/check": lambda r: httpx.Response(500)}, []
        ),
    )
    assert (
        await fuze_security.authz_check(
            subject=USER_ID, tenant=TENANT, resource="Task", action="assign"
        )
        is False
    )


@pytest.mark.asyncio
async def test_authz_check_denies_on_missing_arguments(monkeypatch):
    install_transport(monkeypatch, recording_handler({}, []))
    assert (
        await fuze_security.authz_check(
            subject=USER_ID, tenant="", resource="Task", action="read"
        )
        is False
    )


@pytest.mark.asyncio
async def test_bulk_check_is_index_aligned(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "POST /api/v1/security/authz/bulk-check": lambda r: httpx.Response(
                    200,
                    json={
                        "decisions": [
                            {"allow": True},
                            {"allow": False},
                            {"allow": True},
                        ]
                    },
                )
            },
            [],
        ),
    )
    decisions = await fuze_security.authz_bulk_check(
        [
            (USER_ID, TENANT, "Agent", "read"),
            (USER_ID, TENANT, "Agent", "delete"),
            (USER_ID, TENANT, "Task", "read"),
        ]
    )
    assert decisions == [True, False, True]


@pytest.mark.asyncio
async def test_bulk_check_denies_everything_on_misaligned_response(monkeypatch):
    """A short decision list must never be read as 'the rest were allowed'."""
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "POST /api/v1/security/authz/bulk-check": lambda r: httpx.Response(
                    200, json={"decisions": [{"allow": True}]}
                )
            },
            [],
        ),
    )
    decisions = await fuze_security.authz_bulk_check(
        [(USER_ID, TENANT, "Agent", "read"), (USER_ID, TENANT, "Agent", "delete")]
    )
    assert decisions == [False, False]


@pytest.mark.asyncio
async def test_permissions_returns_resource_action_pairs(monkeypatch):
    seen = []
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/authz/permissions": lambda r: httpx.Response(
                    200,
                    json={
                        "subject": USER_ID,
                        "tenant": TENANT,
                        "permissions": ["Agent:read", "Task:assign"],
                    },
                )
            },
            seen,
        ),
    )
    permissions = await fuze_security.get_permissions(subject=USER_ID, tenant=TENANT)
    assert permissions == ["Agent:read", "Task:assign"]
    assert seen[0].url.params["subject"] == USER_ID
    assert seen[0].url.params["tenant"] == TENANT


@pytest.mark.asyncio
async def test_permissions_empty_on_failure(monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {"GET /api/v1/security/authz/permissions": lambda r: httpx.Response(503)},
            [],
        ),
    )
    assert await fuze_security.get_permissions(subject=USER_ID, tenant=TENANT) == []


# ---------------------------------------------------------------------------
# 4. auth.py wiring — platform mode needs NO local signing key
# ---------------------------------------------------------------------------


@pytest.fixture
def platform_auth(monkeypatch):
    """``auth`` with the platform configured and NO local JWT material.

    The module's config attributes are patched in place rather than re-imported: other
    test modules in the same session hold direct references into ``auth``, and reloading
    it under them swaps the class objects out from beneath their fixtures.
    """
    import auth as auth_module

    monkeypatch.setenv("FUZEFRONT_SECURITY_BASE_URL", BASE)
    monkeypatch.setattr(auth_module, "JWT_SECRET", None)
    monkeypatch.setattr(auth_module, "JWT_PUBLIC_KEY", None)
    monkeypatch.setattr(auth_module, "_AUTH_DISABLED", False)
    return auth_module


def _app_with(auth_module):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI(dependencies=[Depends(auth_module.get_current_user)])

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/whoami")
    async def whoami(user=Depends(auth_module.require_user)):
        return {"id": user.id, "tenant": user.tenant_id, "roles": user.roles}

    @app.post("/organizations/{organization_id}/agents")
    async def create_agent(
        organization_id: str, user=Depends(auth_module.require_user)
    ):
        await auth_module.require_org_permission(
            organization_id,
            user,
            auth_module.ACTION_CREATE,
            resource=auth_module.RESOURCE_AGENT,
        )
        return {"created": True}

    return TestClient(app)


def test_platform_mode_is_enabled_without_any_jwt_material(platform_auth):
    assert platform_auth.platform_security_enabled() is True
    assert platform_auth._auth_configured() is False


def test_platform_mode_health_is_public(platform_auth, monkeypatch):
    install_transport(monkeypatch, recording_handler({}, []))
    assert _app_with(platform_auth).get("/health").status_code == 200


def test_platform_mode_without_token_is_401(platform_auth, monkeypatch):
    install_transport(monkeypatch, recording_handler({}, []))
    assert _app_with(platform_auth).get("/whoami").status_code == 401


def test_platform_mode_resolves_identity_from_the_security_api(
    platform_auth, monkeypatch
):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200, json={"identity": IDENTITY, "user": {"id": USER_ID}}
                )
            },
            [],
        ),
    )
    response = _app_with(platform_auth).get(
        "/whoami", headers={"Authorization": "Bearer opaque-platform-token"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": USER_ID,
        "tenant": TENANT,
        "roles": ["operator"],
    }


def test_platform_mode_rejects_a_token_the_platform_rejects(platform_auth, monkeypatch):
    install_transport(
        monkeypatch,
        recording_handler(
            {"GET /api/v1/security/session": lambda r: httpx.Response(401)}, []
        ),
    )
    response = _app_with(platform_auth).get(
        "/whoami", headers={"Authorization": "Bearer forged"}
    )
    assert response.status_code == 401


def test_platform_mode_org_permission_allows_when_platform_allows(
    platform_auth, monkeypatch
):
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200, json={"identity": IDENTITY, "user": {"id": USER_ID}}
                ),
                "POST /api/v1/security/authz/check": lambda r: httpx.Response(
                    200, json={"allow": True}
                ),
            },
            [],
        ),
    )
    response = _app_with(platform_auth).post(
        f"/organizations/{TENANT}/agents", headers={"Authorization": "Bearer tok"}
    )
    assert response.status_code == 200


def test_platform_mode_org_permission_is_403_when_platform_denies(
    platform_auth, monkeypatch
):
    """The org id in the path is the tenant scope — a foreign org must be refused."""
    install_transport(
        monkeypatch,
        recording_handler(
            {
                "GET /api/v1/security/session": lambda r: httpx.Response(
                    200, json={"identity": IDENTITY, "user": {"id": USER_ID}}
                ),
                "POST /api/v1/security/authz/check": lambda r: httpx.Response(
                    200, json={"allow": False}
                ),
            },
            [],
        ),
    )
    response = _app_with(platform_auth).post(
        f"/organizations/{OTHER_TENANT}/agents", headers={"Authorization": "Bearer tok"}
    )
    assert response.status_code == 403


def test_platform_mode_org_permission_is_403_when_platform_is_unreachable(
    platform_auth, monkeypatch
):
    """Fail-closed end to end: a broken security service denies, it does not admit."""

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/session"):
            return httpx.Response(
                200, json={"identity": IDENTITY, "user": {"id": USER_ID}}
            )
        calls["n"] += 1
        raise httpx.ConnectError("authz down", request=request)

    install_transport(monkeypatch, handler)
    response = _app_with(platform_auth).post(
        f"/organizations/{TENANT}/agents", headers={"Authorization": "Bearer tok"}
    )
    assert response.status_code == 403
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# 5. Legacy mode is preserved — no capability is dropped when the platform is absent
# ---------------------------------------------------------------------------


@pytest.fixture
def legacy_auth(monkeypatch):
    """``auth`` with NO platform configured — the pre-migration local-verification path."""
    import auth as auth_module

    monkeypatch.delenv("FUZEFRONT_SECURITY_BASE_URL", raising=False)
    monkeypatch.setattr(
        auth_module, "JWT_SECRET", LEGACY_SECRET  # nosec B105 - test fixture
    )
    monkeypatch.setattr(auth_module, "JWT_PUBLIC_KEY", None)
    monkeypatch.setattr(auth_module, "JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(auth_module, "JWT_AUDIENCE", None)
    monkeypatch.setattr(auth_module, "JWT_ISSUER", None)
    monkeypatch.setattr(auth_module, "_AUTH_DISABLED", False)
    monkeypatch.setitem(auth_module._VERIFY_OPTIONS, "verify_aud", False)
    return auth_module


def test_legacy_mode_still_verifies_locally(legacy_auth):
    from jose import jwt

    assert legacy_auth.platform_security_enabled() is False
    token = jwt.encode(
        {"sub": USER_ID, "organizations": [TENANT]},
        LEGACY_SECRET,
        algorithm="HS256",
    )
    response = _app_with(legacy_auth).get(
        "/whoami", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == USER_ID


def test_legacy_mode_org_permission_falls_back_to_claims(legacy_auth):
    from jose import jwt

    client = _app_with(legacy_auth)
    token = jwt.encode(
        {"sub": USER_ID, "organizations": [TENANT]},
        LEGACY_SECRET,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(f"/organizations/{TENANT}/agents", headers=headers).status_code
        == 200
    )
    assert (
        client.post(
            f"/organizations/{OTHER_TENANT}/agents", headers=headers
        ).status_code
        == 403
    )
