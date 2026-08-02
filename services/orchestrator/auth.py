"""
Authentication and authorization for the FuzeAgent orchestrator API.

Identity and authorization are the **FuzeFront platform's** to answer, not FuzeAgent's.
When ``FUZEFRONT_SECURITY_BASE_URL`` is configured this module resolves the caller by
asking the FuzeFront Security API (``GET /v1/security/session``) and asks that same API
for authorization decisions (``POST /v1/security/authz/check``) using the bare
resource/action keys FuzeAgent declares in ``registration/policy.json``. No identity
provider and no policy engine is named, imported, or configured anywhere in FuzeAgent —
see ``fuze_security.py``.

Legacy mode (platform not configured): when ``FUZEFRONT_SECURITY_BASE_URL`` is unset the
module keeps its previous behaviour — local HS*/RS* token verification against
``JWT_SECRET``/``JWT_PUBLIC_KEY`` plus claims-based org scoping. That path is retained
deliberately so standalone/offline deployments do not lose capability. It is logged, and
it is the fallback, never the preference.

This module closes the CRITICAL authorization gaps reported in
izzywdev/FuzeAgent#6 (appsec BOLA/authz audit). It provides:

  * ``get_current_user`` — a verified-token FastAPI dependency (JWT bearer)
    intended to be applied app-wide via ``FastAPI(dependencies=[...])`` /
    router-level so every route is authenticated by default.
  * A small, explicit PUBLIC allowlist (health/readiness/docs) — everything
    else fails closed (401) when no valid token is presented.
  * Object-level authorization helpers (``require_org_access``,
    ``require_admin``, ``CurrentUser.can_access_org``) so resource-by-id
    handlers authorize the *specific object*, not just "is logged in".

Design notes
------------
The orchestrator schema has no per-row ``owner_id`` column on
organizations/teams/agents yet (ownership is expressed through the
org -> team -> agent hierarchy). Until a dedicated ownership column /
membership table exists, object-level authorization is enforced against the
**verified token claims**: a token carries the set of organization ids the
principal may act on (``organizations`` / ``orgs`` claim) and/or an admin
role. This is fail-closed: a principal with no claim for ``{org_id}`` is
denied (403). When the membership table lands, swap the in-claim check in
``CurrentUser.can_access_org`` for a DB membership lookup without changing any
call sites. See issue #6 acceptance criteria.

Configuration (env)
-------------------
  FUZEFRONT_SECURITY_BASE_URL
                        Absolute FuzeFront API base including ``/api``. When set,
                        identity + authorization come from the platform and NONE of the
                        JWT_* settings below are consulted or required.
  JWT_SECRET            Legacy mode only. HMAC secret for HS* tokens.
  JWT_PUBLIC_KEY        Legacy mode only. PEM public key for RS*/ES* tokens.
  JWT_ALGORITHM         Legacy mode only. Default "HS256".
  JWT_AUDIENCE          Legacy mode only. Optional expected audience.
  JWT_ISSUER            Legacy mode only. Optional expected issuer.
  AUTH_DISABLED         If "true" AND neither the platform nor a secret/key is
                        configured, auth is bypassed *only* for local dev. This NEVER
                        bypasses in production where the platform or a secret/key is
                        set. It is logged loudly. Do not set this in any deployed
                        environment.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPBearer

try:  # python-jose is already a declared dependency (requirements.txt)
    from jose import JWTError, jwt
except Exception:  # pragma: no cover - import guard for partial envs
    jwt = None  # type: ignore
    JWTError = Exception  # type: ignore

try:  # the FuzeFront Security client — the only auth dependency we want to have
    from . import fuze_security  # type: ignore[attr-defined]
except (ImportError, ValueError):  # pragma: no cover - flat sys.path import (tests/app)
    try:
        import fuze_security  # type: ignore[no-redef]
    except Exception:  # pragma: no cover
        fuze_security = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE") or None
JWT_ISSUER = os.getenv("JWT_ISSUER") or None
_AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"


def platform_security_enabled() -> bool:
    """Whether identity/authorization is delegated to the FuzeFront Security API.

    Read live (not cached at import) so a deployment can turn the platform path on
    without a code change and so tests can toggle it.
    """
    return bool(fuze_security is not None and fuze_security.is_configured())


# ---------------------------------------------------------------------------
# Policy vocabulary — the BARE keys FuzeAgent registers in registration/policy.json.
# These are the strings sent as `resource.type` / `action` to the platform's
# /v1/security/authz/check. They are FuzeAgent's own vocabulary, not any engine's.
# ---------------------------------------------------------------------------

RESOURCE_ORGANIZATION = "Organization"
RESOURCE_TEAM = "Team"
RESOURCE_AGENT = "Agent"
RESOURCE_TASK = "Task"
RESOURCE_GOAL = "Goal"

ACTION_READ = "read"
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_DEPLOY = "deploy"
ACTION_ASSIGN = "assign"

# Explicit public allowlist — these paths are reachable WITHOUT a token.
# Keep this list as small as possible; everything else is authenticated.
PUBLIC_PATHS: Set[str] = {
    "/health",
    "/healthz",
    "/ready",
    "/readiness",
    "/live",
    "/liveness",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
    "/favicon.ico",
}

# python-jose verifies signatures; we additionally require the standard
# registered claims to be present/valid.
_VERIFY_OPTIONS = {
    "verify_signature": True,
    "verify_exp": True,
    "verify_aud": JWT_AUDIENCE is not None,
}

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _auth_configured() -> bool:
    """True when a verification secret/key is configured (i.e. prod-like)."""
    return bool(JWT_SECRET or JWT_PUBLIC_KEY)


def is_public_path(path: str) -> bool:
    """Whether ``path`` is on the explicit public allowlist."""
    if path in PUBLIC_PATHS:
        return True
    # Allow Swagger UI / static asset subpaths under /docs and /redoc.
    return path.startswith("/docs/") or path.startswith("/redoc/")


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------


class CurrentUser:
    """A verified principal.

    Produced either from the FuzeFront Security API's normalized ``Identity``
    (platform mode) or from locally verified JWT claims (legacy mode). Both paths
    populate the SAME fields, so handlers cannot tell — and must not care — which
    verifier ran.

    Carries the claims needed for object-level authorization decisions, plus the
    caller's raw bearer token so platform authorization checks can be made *as the
    real subject* rather than as FuzeAgent.
    """

    def __init__(self, claims: Dict[str, Any], token: Optional[str] = None):
        self.claims = claims
        #: The raw bearer token this principal presented, when available. Forwarded to
        #: the platform's /v1/security/authz/check so the decision is made for the
        #: caller. Never logged, never persisted.
        self.token: Optional[str] = token
        # ------------------------------------------------------------------
        # @fuzefront/auth Identity-aligned fields (userId, tenantId, roles,
        # email, authMode, issuedAt, expiresAt, issuer).
        # See packages/auth/src/types.ts in FuzeFront for the contract.
        # ------------------------------------------------------------------
        self.id: str = str(
            claims.get("sub")
            or claims.get("userId")
            or claims.get("user_id")
            or claims.get("uid")
            or ""
        )
        # user_id alias kept for backward compat
        self.user_id: str = self.id
        self.email: Optional[str] = claims.get("email")
        # Roles may arrive as a list or a space/comma separated string.
        self.roles: List[str] = _as_str_list(
            claims.get("roles") or claims.get("role") or []
        )
        # tenantId — primary org scope per @fuzefront/auth Identity contract.
        # May be null in legacy-hs256 mode when not resolved out-of-band.
        self.tenant_id: Optional[str] = (
            claims.get("tenantId") or claims.get("tenant_id") or None
        )
        # Organizations the principal may act on (superset of tenantId).
        self.organizations: Set[str] = set(
            _as_str_list(
                claims.get("organizations")
                or claims.get("orgs")
                or claims.get("org_ids")
                or (
                    [claims["organization_id"]] if claims.get("organization_id") else []
                )
            )
        )
        # Promote tenantId into organizations if not already there.
        if self.tenant_id:
            self.organizations.add(self.tenant_id)
        self.is_admin: bool = bool(claims.get("is_admin")) or any(
            r.lower() in ("admin", "superadmin", "platform-admin") for r in self.roles
        )
        # A service principal (machine token) used by trusted internal callers.
        self.is_service: bool = bool(claims.get("is_service")) or any(
            r.lower() in ("service", "service-account", "system") for r in self.roles
        )
        # Standard JWT claims aligned with @fuzefront/auth Identity
        self.auth_mode: str = claims.get("authMode", "legacy-hs256")  # gitleaks:allow
        self.issued_at: Optional[int] = claims.get("iat")
        self.expires_at: Optional[int] = claims.get("exp")
        self.issuer: Optional[str] = claims.get("iss")

    @classmethod
    def from_identity(cls, identity: Any, token: Optional[str] = None) -> "CurrentUser":
        """Build a principal from the platform's normalized ``Identity``.

        ``identity`` is a ``fuze_security.Identity``. Its ``as_claims()`` projection uses
        exactly the claim names this class already reads, so platform-mode and legacy-mode
        principals are indistinguishable downstream.
        """
        return cls(identity.as_claims(), token=token)

    def can_access_org(self, organization_id: str) -> bool:
        """Object-level check: may this principal act on ``organization_id``?

        Admins/service principals pass. Otherwise the org id must be present in
        the principal's verified ``organizations`` claim (fail closed).
        Replace the membership check here with a DB lookup once a membership
        table exists — call sites do not change.
        """
        if self.is_admin or self.is_service:
            return True
        return organization_id in self.organizations

    def require_org_access(self, organization_id: str) -> None:
        if not self.can_access_org(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this organization",
            )

    def require_admin(self) -> None:
        if not (self.is_admin or self.is_service):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator privileges required",
            )


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(",", " ").split() if v.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


def _decode_token(token: str) -> Dict[str, Any]:
    if jwt is None:  # pragma: no cover
        logger.error("python-jose not installed; cannot verify JWT")
        raise _UNAUTHENTICATED
    key = JWT_SECRET or JWT_PUBLIC_KEY
    if not key:
        # No verification material configured.
        raise _UNAUTHENTICATED
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options=_VERIFY_OPTIONS,
        )
    except JWTError as exc:  # invalid signature / expired / bad claims
        logger.info("Rejected token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _bearer_from_request(request: Request) -> Optional[str]:
    """Extract a bearer token from the ``Authorization`` header (manually).

    We read the header directly rather than via ``Depends(HTTPBearer())`` so the
    app-wide dependency does NOT pull in an HTTP-only security sub-dependency:
    FastAPI attaches app-level ``dependencies`` to WebSocket routes too, and
    ``HTTPBearer.__call__`` raises ``TypeError`` on a WebSocket connection
    (it requires an HTTP ``Request``). Reading the header keeps this dependency
    safe to evaluate in either scope. The standalone ``_bearer_scheme`` is still
    exported for OpenAPI's Authorize button on individual routes.
    """
    header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if not header:
        return None
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1] or None
    return None


async def _principal_from_token(token: str) -> Optional[CurrentUser]:
    """Resolve a bearer token to a principal, preferring the FuzeFront platform.

    Platform mode (``FUZEFRONT_SECURITY_BASE_URL`` set): the token is handed to
    ``GET /v1/security/session`` and the platform answers with the normalized
    ``Identity``. FuzeAgent holds no signing key and knows nothing about how the token
    was minted or by whom.

    Legacy mode: the token is verified locally against ``JWT_SECRET``/``JWT_PUBLIC_KEY``,
    exactly as before.

    Returns ``None`` when the token cannot be resolved (fail-closed). Raises the same
    401 ``HTTPException`` as before on a locally-rejected token so legacy call sites see
    unchanged behaviour.
    """
    if platform_security_enabled():
        identity = await fuze_security.get_session(token)  # type: ignore[union-attr]
        if identity is None:
            return None
        return CurrentUser.from_identity(identity, token=token)

    claims = _decode_token(token)
    return CurrentUser(claims, token=token)


async def get_current_user(
    request: Request = None,  # type: ignore[assignment]
    websocket: WebSocket = None,  # type: ignore[assignment]
) -> Optional[CurrentUser]:
    """App-wide authentication dependency.

    Returns the verified :class:`CurrentUser`, or raises 401. Public allowlist
    paths short-circuit and return ``None``. Fails closed for everything else.

    NOTE: FastAPI attaches app-level ``dependencies`` to WebSocket routes too,
    but injects a ``WebSocket`` (not a ``Request``) there. Both params are
    therefore optional; on a WebSocket connection this dependency is a no-op
    (returns ``None``) because a WS handshake cannot carry an HTTP 401 response
    — WS handlers authenticate explicitly via :func:`authenticate_websocket`.
    """
    # WebSocket scope: app-level deps cannot 401 a handshake. No-op here; the
    # handler enforces auth via authenticate_websocket() before accept().
    if websocket is not None or request is None:
        return None

    # Public allowlist — health/readiness/docs are reachable without a token.
    if is_public_path(request.url.path):
        return None

    platform = platform_security_enabled()

    # Local-dev escape hatch — only when NEITHER the platform NOR verification
    # material is configured. In any prod-like environment one of them is set and
    # this never triggers.
    if _AUTH_DISABLED and not platform and not _auth_configured():
        logger.warning(
            "AUTH_DISABLED is set with no platform security base URL and no JWT "
            "secret/key configured — authentication is BYPASSED. This must never "
            "happen in production."
        )
        return CurrentUser({"sub": "dev-bypass", "is_admin": True})

    # Fail closed if auth is not configured in a deployed environment.
    if not platform and not _auth_configured():
        logger.error(
            "Neither FUZEFRONT_SECURITY_BASE_URL nor JWT_SECRET/JWT_PUBLIC_KEY is "
            "configured; rejecting request to %s",
            request.url.path,
        )
        raise _UNAUTHENTICATED

    token = _bearer_from_request(request)
    if not token:
        raise _UNAUTHENTICATED

    user = await _principal_from_token(token)
    if user is None or not user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Stash for downstream handlers / logging.
    request.state.current_user = user
    return user


def require_user(
    user: Optional[CurrentUser] = Depends(get_current_user),
) -> CurrentUser:
    """Like :func:`get_current_user` but never returns ``None``.

    Use on protected handlers that must have a concrete principal (i.e. not a
    public-allowlist path). Guarantees a 401 if unauthenticated.
    """
    if user is None:
        raise _UNAUTHENTICATED
    return user


def require_admin(
    user: CurrentUser = Depends(require_user),
) -> CurrentUser:
    """Dependency: principal must be an admin or service account (else 403)."""
    user.require_admin()
    return user


def require_org_access(organization_id: str, user: CurrentUser) -> CurrentUser:
    """Object-level authorization helper for org-scoped resources.

    Call from a handler that has the org id from the path::

        @app.post("/organizations/{organization_id}/...")
        async def handler(organization_id: str,
                          user: CurrentUser = Depends(require_user)):
            require_org_access(organization_id, user)
            ...
    """
    user.require_org_access(organization_id)
    return user


# ---------------------------------------------------------------------------
# Platform authorization — decisions come from FuzeFront, never from a local policy
# ---------------------------------------------------------------------------
#
# `authorize` / `require_permission` are the preferred authorization API. They send
# FuzeAgent's OWN bare resource/action keys (registration/policy.json) to the platform's
# /v1/security/authz/check as the CALLER's subject, so the policy that decides lives
# with the platform and FuzeAgent ships none.
#
# Legacy fallback: when the platform is not configured they degrade to the pre-existing
# claims/role checks so a standalone deployment keeps working. This is a documented
# downgrade, not a silent one — it is logged once per process.

_LEGACY_AUTHZ_WARNED = False


def _warn_legacy_authz_once() -> None:
    global _LEGACY_AUTHZ_WARNED
    if not _LEGACY_AUTHZ_WARNED:
        _LEGACY_AUTHZ_WARNED = True
        logger.warning(
            "FUZEFRONT_SECURITY_BASE_URL is not configured — authorization is falling "
            "back to local token-claim checks. Platform policy (registration/policy.json) "
            "is NOT being consulted."
        )


async def authorize(
    user: CurrentUser,
    resource: str,
    action: str,
    *,
    tenant: Optional[str] = None,
    resource_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Ask FuzeFront whether ``user`` may perform ``action`` on ``resource``.

    ``resource``/``action`` are FuzeAgent's bare policy keys (``RESOURCE_*``/``ACTION_*``
    above), matching ``registration/policy.json``. ``tenant`` defaults to the principal's
    own tenant; a tenant-scoped decision with no resolvable tenant is DENIED (the
    platform contract's documented fail-closed behaviour for a null tenant).

    Returns ``True``/``False``. Never raises for a denial.
    """
    scope = tenant or user.tenant_id
    if platform_security_enabled():
        if not scope:
            logger.info(
                "Denying %s:%s for %s — no tenant scope resolvable (fail-closed)",
                resource,
                action,
                user.id,
            )
            return False
        return await fuze_security.authz_check(  # type: ignore[union-attr]
            subject=user.id,
            tenant=scope,
            resource=resource,
            action=action,
            resource_key=resource_key,
            context=context,
            token=user.token,
        )

    _warn_legacy_authz_once()
    # Legacy: admins/service principals pass; otherwise the caller must be scoped to the
    # tenant. This is strictly the pre-migration behaviour — no new capability.
    if user.is_admin or user.is_service:
        return True
    return bool(scope) and user.can_access_org(scope)


async def require_permission(
    user: CurrentUser,
    resource: str,
    action: str,
    *,
    tenant: Optional[str] = None,
    resource_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> CurrentUser:
    """:func:`authorize`, but raises 403 on denial. Use this in handlers."""
    allowed = await authorize(
        user,
        resource,
        action,
        tenant=tenant,
        resource_key=resource_key,
        context=context,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} {resource}",
        )
    return user


async def require_org_permission(
    organization_id: str,
    user: CurrentUser,
    action: str = ACTION_READ,
    *,
    resource: str = RESOURCE_ORGANIZATION,
    resource_key: Optional[str] = None,
) -> CurrentUser:
    """Org-scoped object-level authorization, decided by the platform.

    The async replacement for :func:`require_org_access`. The org id from the path is the
    tenant scope, so a principal is authorized *for that specific organization* rather
    than merely "logged in". In legacy mode this reduces exactly to the previous
    ``require_org_access`` claim check, so no capability is lost when the platform is
    absent.
    """
    if not platform_security_enabled():
        _warn_legacy_authz_once()
        user.require_org_access(organization_id)
        return user
    return await require_permission(
        user,
        resource,
        action,
        tenant=organization_id,
        resource_key=resource_key or organization_id,
    )


async def effective_permissions(
    user: CurrentUser, tenant: Optional[str] = None
) -> List[str]:
    """The caller's effective ``Resource:action`` grants, for UI capability gating.

    Empty list when the platform is not configured or the call fails — read that as
    "no permissions known", never as "unrestricted".
    """
    scope = tenant or user.tenant_id
    if not platform_security_enabled() or not scope:
        return []
    return await fuze_security.get_permissions(  # type: ignore[union-attr]
        subject=user.id, tenant=scope, token=user.token
    )


# ---------------------------------------------------------------------------
# WebSocket authentication
# ---------------------------------------------------------------------------
#
# IMPORTANT: the app-wide ``dependencies=[Depends(get_current_user)]`` applied
# to the FastAPI app does NOT run for WebSocket routes — Starlette only applies
# router/app dependencies to HTTP requests. WebSocket handlers must therefore
# authenticate explicitly, BEFORE ``websocket.accept()``. Browsers cannot set
# an ``Authorization`` header on a WS handshake, so the token is accepted from
# (in order): the ``Authorization: Bearer`` header (non-browser clients), the
# ``Sec-WebSocket-Protocol`` subprotocol (``bearer,<token>``), or a ``token`` /
# ``access_token`` query parameter. Fails closed: no/invalid token -> the
# socket is closed with policy-violation (1008) and ``None`` is returned.


def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """Pull a bearer token from header, subprotocol, or query param."""
    # 1) Authorization header (programmatic clients).
    auth_header = websocket.headers.get("authorization") or websocket.headers.get(
        "Authorization"
    )
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
            return parts[1]
        if len(parts) == 1 and parts[0]:
            return parts[0]

    # 2) Sec-WebSocket-Protocol: "bearer, <token>" (browser-friendly).
    proto = websocket.headers.get("sec-websocket-protocol")
    if proto:
        items = [p.strip() for p in proto.split(",") if p.strip()]
        if len(items) == 2 and items[0].lower() in ("bearer", "authorization"):
            return items[1]
        if len(items) == 1 and items[0].lower() not in ("bearer", "authorization"):
            return items[0]

    # 3) Query parameter (last resort; avoid logging full URLs with tokens).
    return websocket.query_params.get("token") or websocket.query_params.get(
        "access_token"
    )


async def authenticate_websocket(websocket: WebSocket) -> Optional[CurrentUser]:
    """Connect-time auth for a WebSocket. Returns the principal or closes 1008.

    Call this FIRST inside every ``@app.websocket`` handler, before
    ``accept()``. On failure it closes the socket (code 1008) and returns
    ``None`` — the handler must ``return`` immediately when it gets ``None``.

    Identity resolution is the same as HTTP: the FuzeFront Security API when the
    platform is configured, local verification otherwise.

    The local-dev escape hatch mirrors :func:`get_current_user`: it only ever
    bypasses when ``AUTH_DISABLED`` is set AND neither the platform nor verification
    material is configured (never in a deployed environment).
    """
    platform = platform_security_enabled()

    # Local-dev bypass — only when NEITHER the platform NOR a secret/key is configured.
    if _AUTH_DISABLED and not platform and not _auth_configured():
        logger.warning(
            "AUTH_DISABLED set with no platform security base URL and no JWT material "
            "— WS authentication BYPASSED."
        )
        return CurrentUser({"sub": "dev-bypass", "is_admin": True})

    if not platform and not _auth_configured():
        logger.error(
            "Neither FUZEFRONT_SECURITY_BASE_URL nor JWT material configured; "
            "rejecting WS %s",
            websocket.url.path,
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        user = await _principal_from_token(token)
    except HTTPException:
        # Invalid/expired token — close instead of raising (no HTTP response on WS).
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    if user is None or not user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return user
