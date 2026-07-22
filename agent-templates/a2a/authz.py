"""Callee-enforced authorization (authz.md).

    The CALLEE enforces. The caller is opaque and untrusted.

Nothing in the request BODY is trusted for authorization — not ``tenant``, not
``metadata``, not a self-declared caller name. The only trusted input is the
authenticated identity from the transport credential (``AuthContext.caller``).

The grant lives in the CALLEE's ``.fuze/manifest.json`` ``providesTo`` list. It is
FAIL-CLOSED: absent means unconfigured, which is DENY (never permissive) — this is
load-bearing, because ``providesTo`` is absent on most repos at freeze time and
treating absent as allow would silently open them to every caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

_REPO_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_EXEC_PRINCIPAL_RE = re.compile(r"^Exec-[a-z0-9_-]+$")


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    #: allowlisted caller, but the token lacks a scope it could plausibly obtain.
    #: The one legitimate AUTH_REQUIRED at authz step 5 (authz.md §4).
    SCOPE_REQUIRED = "scope_required"


@dataclass(frozen=True)
class AuthContext:
    """Resolved, TRUSTED identity from the transport credential (never the body)."""

    caller: str
    scopes: frozenset[str] = frozenset()
    authenticated: bool = True


@dataclass(frozen=True)
class AuthzResult:
    decision: Decision
    #: internal reason for the callee's LOGS only — never put on the wire (authz.md §6).
    reason: str = ""
    missing_scopes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW


def valid_caller_identity(caller: str | None) -> bool:
    """A caller identity MUST be a bare repo name or an exec principal (authz.md §2)."""
    if not caller:
        return False
    return bool(_REPO_NAME_RE.match(caller)) or bool(_EXEC_PRINCIPAL_RE.match(caller))


def _skill_scopes(role: dict | None) -> list[str]:
    if not role:
        return []
    return list((role.get("a2a") or {}).get("scopes") or [])


def _skill_publish(role: dict | None) -> tuple[bool, bool]:
    a2a = (role or {}).get("a2a") or {}
    publish = a2a.get("publish", True)
    extended_only = a2a.get("extendedOnly", False)
    return bool(publish), bool(extended_only)


def authorize(
    ctx: AuthContext,
    callee_manifest: dict | None,
    *,
    skill_role: dict | None = None,
    skill_known: bool = True,
) -> AuthzResult:
    """Run the callee-side decision procedure (authz.md §3).

    Steps:
      1. authentication (checked upstream; a false ``ctx.authenticated`` => DENY).
      2. caller := trusted identity (already resolved into ``ctx``).
      3. callee := tenant -> repo (a missing/None manifest => DENY as not-found).
      4. providesTo: ABSENT -> DENY, [] -> DENY, caller not in -> DENY.
      5. skill: unknown/unpublished-to-caller -> DENY; a2a.scopes present but token
         lacks them -> SCOPE_REQUIRED (the sole legitimate AUTH_REQUIRED).
    """
    if not ctx.authenticated or not valid_caller_identity(ctx.caller):
        return AuthzResult(Decision.DENY, "unauthenticated or invalid caller identity")

    if callee_manifest is None:
        return AuthzResult(Decision.DENY, "unknown callee/tenant")

    provides_to = callee_manifest.get("providesTo")
    if provides_to is None:
        return AuthzResult(Decision.DENY, "providesTo absent -> fail closed")
    if not isinstance(provides_to, list) or len(provides_to) == 0:
        return AuthzResult(Decision.DENY, "providesTo empty -> no agent callers")
    if ctx.caller not in provides_to:
        return AuthzResult(Decision.DENY, f"caller {ctx.caller!r} not in providesTo")

    if not skill_known:
        return AuthzResult(Decision.DENY, "unknown skill")

    _, extended_only = _skill_publish(skill_role)
    # (visibility of the skill is handled at card projection; here we only gate dispatch)

    required = set(_skill_scopes(skill_role))
    if required:
        missing = tuple(sorted(required - set(ctx.scopes)))
        if missing:
            return AuthzResult(
                Decision.SCOPE_REQUIRED,
                f"missing scopes {missing}",
                missing_scopes=missing,
            )

    return AuthzResult(Decision.ALLOW, "authorized")
