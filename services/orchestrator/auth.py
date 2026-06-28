"""
Authentication and authorization for the FuzeAgent orchestrator API.

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
  JWT_SECRET            HMAC secret for HS* tokens (required in prod).
  JWT_PUBLIC_KEY        PEM public key for RS*/ES* tokens (alternative).
  JWT_ALGORITHM         Default "HS256".
  JWT_AUDIENCE          Optional expected audience.
  JWT_ISSUER            Optional expected issuer.
  AUTH_DISABLED         If "true" AND no secret/key is configured, auth is
                        bypassed *only* for local dev. This NEVER bypasses in
                        production where a secret/key is set. It is logged
                        loudly. Do not set this in any deployed environment.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:  # python-jose is already a declared dependency (requirements.txt)
    from jose import JWTError, jwt
except Exception:  # pragma: no cover - import guard for partial envs
    jwt = None  # type: ignore
    JWTError = Exception  # type: ignore

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
    """A verified principal extracted from the JWT.

    Carries the claims needed for object-level authorization decisions.
    """

    def __init__(self, claims: Dict[str, Any]):
        self.claims = claims
        self.id: str = str(
            claims.get("sub") or claims.get("user_id") or claims.get("uid") or ""
        )
        self.email: Optional[str] = claims.get("email")
        # Roles may arrive as a list or a space/comma separated string.
        self.roles: List[str] = _as_str_list(
            claims.get("roles") or claims.get("role") or []
        )
        # Organizations the principal may act on.
        self.organizations: Set[str] = set(
            _as_str_list(
                claims.get("organizations")
                or claims.get("orgs")
                or claims.get("org_ids")
                or ([claims["organization_id"]] if claims.get("organization_id") else [])
            )
        )
        self.is_admin: bool = bool(claims.get("is_admin")) or any(
            r.lower() in ("admin", "superadmin", "platform-admin") for r in self.roles
        )
        # A service principal (machine token) used by trusted internal callers,
        # e.g. the migration runner. Identified by a dedicated role/scope.
        self.is_service: bool = bool(claims.get("is_service")) or any(
            r.lower() in ("service", "service-account", "system") for r in self.roles
        )

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


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[CurrentUser]:
    """App-wide authentication dependency.

    Returns the verified :class:`CurrentUser`, or raises 401. Public allowlist
    paths short-circuit and return ``None``. Fails closed for everything else.
    """
    # Public allowlist — health/readiness/docs are reachable without a token.
    if is_public_path(request.url.path):
        return None

    # Local-dev escape hatch — only when NO verification material is configured.
    # In any prod-like environment a secret/key is set and this never triggers.
    if _AUTH_DISABLED and not _auth_configured():
        logger.warning(
            "AUTH_DISABLED is set and no JWT secret/key configured — "
            "authentication is BYPASSED. This must never happen in production."
        )
        return CurrentUser({"sub": "dev-bypass", "is_admin": True})

    # Fail closed if auth is not configured in a deployed environment.
    if not _auth_configured():
        logger.error(
            "No JWT_SECRET/JWT_PUBLIC_KEY configured; rejecting request to %s",
            request.url.path,
        )
        raise _UNAUTHENTICATED

    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    claims = _decode_token(credentials.credentials)
    user = CurrentUser(claims)
    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
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
