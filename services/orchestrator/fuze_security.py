"""FuzeFront Security API client — FuzeAgent's ONLY identity/authorization dependency.

Provider-agnostic by construction. This module speaks the FuzeFront-owned Security
contract (``@fuzefront/security-client`` / ``openapi.yaml``, served same-origin under
``/api/v1/security``) and names **no** identity provider and **no** policy engine.
Whichever federation/MFA engine or ReBAC engine FuzeFront runs behind that contract is
invisible here — swapping it must not require a change in this file.

Endpoints used (all published in the FuzeFront Security contract v0.4.0):

  ``GET  /v1/security/session``              -> normalized ``Identity`` for a token
  ``POST /v1/security/authz/check``          -> ``{ allow: bool }``
  ``POST /v1/security/authz/bulk-check``     -> ``{ decisions: [{ allow }] }``
  ``GET  /v1/security/authz/permissions``    -> ``{ permissions: ["Resource:action"] }``

The ``resource``/``action`` keys sent to ``authz/check`` are the **bare keys FuzeAgent
already declares in** ``registration/policy.json`` (``Organization``, ``Team``,
``Agent``, ``Task``, ``Goal`` x ``read``/``create``/``update``/``delete``/``deploy``/
``assign``). FuzeAgent registers that policy with the platform once, and thereafter asks
the platform for decisions — it never evaluates, stores, or ships policy itself.

Configuration (env, all vendor-neutral)
---------------------------------------
  ``FUZEFRONT_SECURITY_BASE_URL``
      Absolute base URL of the FuzeFront API *including* the ``/api`` prefix, e.g.
      ``http://fuzefront-backend.fuzefront.svc.cluster.local:3001/api``. Server-side
      calls need an absolute host (there is no "same origin" for a backend process);
      browser callers use the same-origin ``/api`` base instead. When this is UNSET the
      security service is considered **not configured** and callers fall back to their
      documented legacy behaviour — see ``auth.py``.
  ``FUZEFRONT_SECURITY_TIMEOUT_SECONDS``
      Per-request timeout. Default ``5.0``.
  ``FUZEFRONT_SECURITY_SERVICE_TOKEN``
      Optional machine token used for calls FuzeAgent makes on its own behalf rather
      than on behalf of a signed-in user (e.g. a background reconciliation deciding
      whether a service principal may deploy an agent). NOT used for user requests —
      those forward the user's own bearer token so the decision is made for the real
      subject.

Fail-closed
-----------
Every helper here denies on any error: transport failure, timeout, non-2xx, malformed
body, missing config. There is no permissive fallback and no "allow on error" path. A
denial is returned as ``False``/``None``; the caller turns that into 401/403.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

try:  # httpx is a declared dependency (requirements.txt)
    import httpx
except Exception:  # pragma: no cover - import guard for partial envs
    httpx = None  # type: ignore


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Contract path prefix. Versioned by the FuzeFront Security contract, not by us.
SECURITY_PREFIX = "/v1/security"

#: Major version of the FuzeFront Security contract this client is written against.
SECURITY_CONTRACT_MAJOR = 0


def base_url() -> Optional[str]:
    """Configured FuzeFront API base (including ``/api``), or ``None``."""
    raw = (os.getenv("FUZEFRONT_SECURITY_BASE_URL") or "").strip()
    return raw.rstrip("/") or None


def is_configured() -> bool:
    """Whether the FuzeFront Security service is wired up for this process."""
    return bool(base_url()) and httpx is not None


def timeout_seconds() -> float:
    try:
        return float(os.getenv("FUZEFRONT_SECURITY_TIMEOUT_SECONDS", "5.0"))
    except ValueError:
        return 5.0


def service_token() -> Optional[str]:
    return (os.getenv("FUZEFRONT_SECURITY_SERVICE_TOKEN") or "").strip() or None


def _url(path: str) -> Optional[str]:
    base = base_url()
    if not base:
        return None
    return f"{base}{SECURITY_PREFIX}{path}"


def _headers(token: Optional[str]) -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    bearer = token or service_token()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    return headers


# ---------------------------------------------------------------------------
# Normalized identity (mirrors the contract's `Identity`)
# ---------------------------------------------------------------------------


class Identity:
    """The stable, provider-neutral identity returned by ``GET /v1/security/session``.

    Field names mirror the contract's ``Identity`` schema exactly so drift is obvious.
    """

    __slots__ = (
        "userId",
        "tenantId",
        "roles",
        "email",
        "authMode",
        "issuedAt",
        "expiresAt",
        "issuer",
        "raw",
    )

    def __init__(self, data: Dict[str, Any]):
        self.raw = data
        self.userId: str = str(data.get("userId") or "")
        tenant = data.get("tenantId")
        self.tenantId: Optional[str] = str(tenant) if tenant else None
        roles = data.get("roles") or []
        self.roles: List[str] = (
            [str(r) for r in roles] if isinstance(roles, (list, tuple)) else []
        )
        self.email: Optional[str] = data.get("email")
        self.authMode: str = str(data.get("authMode") or "federated-jwks")
        self.issuedAt: Optional[int] = data.get("issuedAt")
        self.expiresAt: Optional[int] = data.get("expiresAt")
        self.issuer: Optional[str] = data.get("issuer")

    def as_claims(self) -> Dict[str, Any]:
        """Project onto the claim names ``auth.CurrentUser`` already understands."""
        claims: Dict[str, Any] = {
            "sub": self.userId,
            "userId": self.userId,
            "tenantId": self.tenantId,
            "roles": list(self.roles),
            "authMode": self.authMode,
        }
        if self.email:
            claims["email"] = self.email
        if self.issuedAt is not None:
            claims["iat"] = self.issuedAt
        if self.expiresAt is not None:
            claims["exp"] = self.expiresAt
        if self.issuer:
            claims["iss"] = self.issuer
        return claims


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def _default_client():  # pragma: no cover - trivial factory
    return httpx.AsyncClient(timeout=timeout_seconds())


#: Injectable async-client factory. Production uses :func:`_default_client`; tests swap
#: in an ``httpx.AsyncClient`` backed by a ``MockTransport`` so no network is touched.
client_factory = _default_client


async def _request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, str]] = None,
) -> Optional[Any]:
    """Issue one call. Returns the decoded body, or ``None`` on ANY failure.

    ``None`` is the fail-closed sentinel — callers must treat it as deny/unauthenticated,
    never as "no opinion".
    """
    url = _url(path)
    if url is None or httpx is None:
        logger.debug("Security service not configured; %s %s skipped", method, path)
        return None
    try:
        async with client_factory() as client:
            response = await client.request(
                method, url, headers=_headers(token), json=json_body, params=params
            )
    except Exception as exc:  # transport/timeout/DNS — fail closed
        logger.warning("Security service %s %s failed: %s", method, path, exc)
        return None

    if response.status_code == 401:
        logger.info("Security service rejected the token for %s %s", method, path)
        return None
    if response.status_code >= 400:
        logger.warning(
            "Security service %s %s returned %s", method, path, response.status_code
        )
        return None
    if response.status_code == 204 or not response.content:
        return {}
    try:
        return response.json()
    except Exception as exc:  # malformed body — fail closed
        logger.warning(
            "Security service %s %s returned non-JSON: %s", method, path, exc
        )
        return None


# ---------------------------------------------------------------------------
# AuthN — session
# ---------------------------------------------------------------------------


async def get_session(token: str) -> Optional[Identity]:
    """Resolve the presented bearer token to a normalized ``Identity``.

    ``GET /v1/security/session``. Returns ``None`` when the token is not valid, or when
    the service is unreachable — both are "not authenticated" (fail-closed). FuzeAgent
    performs NO signature verification of its own on this path and therefore needs no
    signing key, no JWKS URL, and no knowledge of the issuing provider.
    """
    if not token:
        return None
    body = await _request("GET", "/session", token=token)
    if not isinstance(body, dict):
        return None
    identity = body.get("identity")
    if not isinstance(identity, dict):
        return None
    resolved = Identity(identity)
    if not resolved.userId:
        return None
    return resolved


async def revoke_session(token: str) -> bool:
    """Log out — ``DELETE /v1/security/session``. Idempotent; ``False`` on failure."""
    if not token:
        return False
    return await _request("DELETE", "/session", token=token) is not None


# ---------------------------------------------------------------------------
# AuthZ — check / bulk-check / permissions
# ---------------------------------------------------------------------------


def _check_body(
    subject: str,
    tenant: str,
    resource: str,
    action: str,
    resource_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one ``AuthzCheckRequest`` using FuzeAgent's bare policy keys."""
    ref: Dict[str, Any] = {"type": resource}
    if resource_key:
        ref["key"] = resource_key
    body: Dict[str, Any] = {
        "subject": subject,
        "tenant": tenant,
        "resource": ref,
        "action": action,
    }
    if context:
        body["context"] = context
    return body


async def authz_check(
    *,
    subject: str,
    tenant: str,
    resource: str,
    action: str,
    resource_key: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
) -> bool:
    """One authorization decision. ``POST /v1/security/authz/check``. Fail-closed."""
    if not subject or not tenant or not resource or not action:
        return False
    body = await _request(
        "POST",
        "/authz/check",
        token=token,
        json_body=_check_body(subject, tenant, resource, action, resource_key, context),
    )
    return bool(isinstance(body, dict) and body.get("allow") is True)


async def authz_bulk_check(
    checks: Sequence[Tuple[str, str, str, str]],
    *,
    token: Optional[str] = None,
) -> List[bool]:
    """Many decisions in one round trip. ``POST /v1/security/authz/bulk-check``.

    ``checks`` is a sequence of ``(subject, tenant, resource, action)`` tuples. The
    returned list is index-aligned with the input, exactly as the contract guarantees.
    Fail-closed: on any failure — including a response whose decision count does not
    match the request — every element is ``False``.
    """
    if not checks:
        return []
    payload = {
        "checks": [
            _check_body(subject, tenant, resource, action)
            for (subject, tenant, resource, action) in checks
        ]
    }
    body = await _request("POST", "/authz/bulk-check", token=token, json_body=payload)
    denied = [False] * len(checks)
    if not isinstance(body, dict):
        return denied
    decisions = body.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(checks):
        logger.warning(
            "authz/bulk-check returned a misaligned decision list; denying all"
        )
        return denied
    return [bool(isinstance(d, dict) and d.get("allow") is True) for d in decisions]


async def get_permissions(
    *, subject: str, tenant: str, token: Optional[str] = None
) -> List[str]:
    """Effective ``Resource:action`` grants for a subject in a tenant.

    ``GET /v1/security/authz/permissions``. Fail-closed: ``[]`` on any failure, which a
    caller must read as "no permissions known", never as "unrestricted".
    """
    if not subject or not tenant:
        return []
    body = await _request(
        "GET",
        "/authz/permissions",
        token=token,
        params={"subject": subject, "tenant": tenant},
    )
    if not isinstance(body, dict):
        return []
    permissions = body.get("permissions")
    if not isinstance(permissions, list):
        return []
    return [str(p) for p in permissions]
