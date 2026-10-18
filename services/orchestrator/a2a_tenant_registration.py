"""A2A runtime tenant registration API (orchestrator).

Implements the orchestrator side of izzywdev/FuzeAgent#203 slice 2:

  * ``POST /a2a/tenants/register`` — idempotent self-registration upsert.
  * ``GET  /a2a/tenants``          — the resolved tenant set the A2A server fetches.

Normative source: ``agent-templates/contracts/a2a/v1/tenant-registration.md`` (read
alongside ``schema/tenant-registration.schema.json``). This module does not redefine
the contract; it validates against a vendored, byte-identical copy of the frozen JSON
Schema (see ``contracts/a2a/v1/schema/README.md`` for why it is vendored rather than
referenced) and writes the ``a2a_tenants`` table the Slice-1 migration creates.

SECURITY (contract §3, fail-closed identity binding)
-----------------------------------------------------
Registration is authenticated by the SAME OIDC bearer credential ``auth.py`` already
verifies for every orchestrator request (``require_user``) — no new auth scheme is
introduced. The caller's repo identity is read from the JWT claim named by
``A2A_TENANT_CALLER_CLAIM`` (default ``"repo"``), mirroring the ``auth.callerClaim``
concept the A2A server itself validates for this same credential family
(``values-interface.schema.json`` / ``agent-templates/a2a/config.py``). The request
body is UNTRUSTED for identity: a ``tenant``/``repo`` that does not match the
authenticated caller is rejected with 403 and never written, regardless of what the
caller claims about itself in the payload.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

from auth import CurrentUser, require_admin, require_user
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a2a", tags=["A2A Tenant Registration"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: JWT claim carrying the authenticated caller's repo identity — the ONLY trusted
#: identity for the self-registration binding rule (tenant-registration.md §3). Mirrors
#: values-interface.schema.json's `auth.callerClaim` (default there is "sub"; real
#: deployments set it to "repo" — see deploy/helm/a2a-shared/GO-LIVE.md). Configurable
#: here so the orchestrator can be pointed at whatever claim name the OIDC issuer uses
#: without a code change.
A2A_TENANT_CALLER_CLAIM = os.getenv("A2A_TENANT_CALLER_CLAIM", "repo")

_REQUEST_DEFAULTS: Dict[str, Any] = {"ref": "main", "external": False, "enabled": True}

# ---------------------------------------------------------------------------
# Frozen-contract schema validation (vendored copy — see contracts/a2a/v1/schema/README.md)
# ---------------------------------------------------------------------------

SCHEMA_DIR = Path(__file__).resolve().parent / "contracts" / "a2a" / "v1" / "schema"


@lru_cache(maxsize=None)
def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _schema_store() -> Dict[str, dict]:
    return {
        s["$id"]: s
        for s in (_schema(p.name) for p in SCHEMA_DIR.glob("*.json"))
        if "$id" in s
    }


@lru_cache(maxsize=None)
def _root_validator(schema_name: str) -> Draft202012Validator:
    """Validator for a whole schema file (agent-card.schema.json / fuze-profile.schema.json)."""
    schema = _schema(schema_name)
    resolver = RefResolver(
        base_uri=schema["$id"], referrer=schema, store=_schema_store()
    )
    return Draft202012Validator(schema, resolver=resolver)


@lru_cache(maxsize=None)
def _def_validator(schema_name: str, def_name: str) -> Draft202012Validator:
    """Validator for a single ``$defs`` entry of ``schema_name`` (e.g. RegisterTenantRequest).

    Wraps the target ``$def`` in a tiny schema that keeps the root's ``$id`` (so relative
    ``$ref``s like ``card -> agent-card.schema.json`` resolve against the same base) and
    its ``$defs`` (so internal ``#/$defs/...`` refs, e.g. ``tenantSlug``, still resolve).
    """
    root = _schema(schema_name)
    wrapper = {
        "$id": root["$id"],
        "$schema": root.get("$schema"),
        "$defs": root["$defs"],
        "$ref": f"#/$defs/{def_name}",
    }
    resolver = RefResolver(
        base_uri=wrapper["$id"], referrer=wrapper, store=_schema_store()
    )
    return Draft202012Validator(wrapper, resolver=resolver)


def _format_errors(
    validator: Draft202012Validator, instance: Any, prefix: str = ""
) -> List[str]:
    errors = []
    for e in validator.iter_errors(instance):
        path = "/".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{prefix}{path}: {e.message}")
    return errors


def validate_register_request(body: Any) -> List[str]:
    """Validate ``body`` against the frozen ``RegisterTenantRequest`` $def.

    This structurally validates the whole envelope INCLUDING ``card`` against
    ``agent-card.schema.json`` (the request schema `$ref`s it directly). It does NOT
    perform the additional Fuze-profile check (signatures/interface/capabilities) —
    that is ``validate_card`` below, run separately per contract §4.
    """
    validator = _def_validator(
        "tenant-registration.schema.json", "RegisterTenantRequest"
    )
    return _format_errors(validator, body)


def validate_card(card: Any) -> List[str]:
    """The two-schema card check required by contract §4: structural AND profile."""
    errors: List[str] = []
    for schema_name in ("agent-card.schema.json", "fuze-profile.schema.json"):
        errors.extend(
            _format_errors(
                _root_validator(schema_name), card, prefix=f"[{schema_name}] "
            )
        )
    return errors


def _is_in_cluster_url(url: Any) -> bool:
    """Whether ``url`` looks like an in-cluster service DNS address (card-projection.md §2)."""
    return isinstance(url, str) and ".svc.cluster.local" in url


def _card_cross_checks(card: Dict[str, Any], tenant: str, external: bool) -> List[str]:
    """The two §4 checks that span the record and the card, not expressible in either schema alone."""
    errors: List[str] = []
    interfaces = card.get("supportedInterfaces") or []
    if not interfaces:
        return ["card.supportedInterfaces: missing or empty"]
    iface = interfaces[0]
    iface_tenant = iface.get("tenant")
    if iface_tenant != tenant:
        errors.append(
            f"card.supportedInterfaces[0].tenant ({iface_tenant!r}) must equal the record tenant ({tenant!r})"
        )
    if not external and not _is_in_cluster_url(iface.get("url")):
        errors.append(
            f"card.supportedInterfaces[0].url ({iface.get('url')!r}) must be an in-cluster address "
            "unless external=true"
        )
    return errors


# ---------------------------------------------------------------------------
# Self-registration identity binding (contract §3 — fail-closed)
# ---------------------------------------------------------------------------


def _tenant_from_repo(repo: str) -> str:
    """The repo-name segment card-projection.md calls ``<RepoName>`` — the derived tenant slug."""
    return repo.rsplit("/", 1)[-1]


def _authorize_self_registration(user: CurrentUser, body: Dict[str, Any]) -> None:
    """Enforce tenant-registration.md §3 steps 2-4. Raises 403 on any mismatch; never writes."""
    caller_repo = user.claims.get(A2A_TENANT_CALLER_CLAIM)
    body_repo = body.get("repo")
    body_tenant = body.get("tenant")

    if not caller_repo or not isinstance(caller_repo, str):
        logger.warning(
            "a2a.tenants.register denied: credential carries no %r claim (principal=%s)",
            A2A_TENANT_CALLER_CLAIM,
            user.id,
        )
        raise HTTPException(
            status_code=403, detail="Caller credential carries no repo identity claim"
        )

    if body_repo != caller_repo:
        logger.warning(
            "a2a.tenants.register denied: repo mismatch (body.repo=%s, caller repo=%s)",
            body_repo,
            caller_repo,
        )
        raise HTTPException(
            status_code=403,
            detail="repo does not match the authenticated caller identity",
        )

    expected_tenant = _tenant_from_repo(caller_repo)
    if body_tenant != expected_tenant:
        logger.warning(
            "a2a.tenants.register denied: tenant not derivable from caller repo "
            "(body.tenant=%s, expected=%s, repo=%s)",
            body_tenant,
            expected_tenant,
            caller_repo,
        )
        raise HTTPException(
            status_code=403,
            detail="tenant is not derivable from the authenticated caller repo",
        )


# ---------------------------------------------------------------------------
# DB access — a2a_tenants (Slice-1 migration; snake_case columns)
# ---------------------------------------------------------------------------

_UPSERT_SQL = """
    INSERT INTO a2a_tenants (
        tenant, repo, ref, entry_role, serving_roles, external, provider, card, enabled
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (tenant) DO UPDATE SET
        repo = EXCLUDED.repo,
        ref = EXCLUDED.ref,
        entry_role = EXCLUDED.entry_role,
        serving_roles = EXCLUDED.serving_roles,
        external = EXCLUDED.external,
        provider = EXCLUDED.provider,
        card = EXCLUDED.card,
        enabled = EXCLUDED.enabled
    RETURNING
        tenant, repo, ref, entry_role, serving_roles, external, provider,
        card, enabled, created_at, updated_at, (xmax = 0) AS created
"""
# NOTE on `(xmax = 0) AS created`: the standard atomic single-round-trip idiom for
# distinguishing INSERT from UPDATE inside one `INSERT ... ON CONFLICT DO UPDATE`
# statement — a freshly inserted tuple's xmax is 0; ON CONFLICT DO UPDATE always
# writes a new tuple version with a non-zero xmax. This keeps the whole upsert (and
# therefore the 201-vs-200 decision) atomic, which the contract requires for
# concurrent registrations across replicas (tenant-registration.md §2) — a
# read-then-write pre-check would race under exactly that concurrency.
# `updated_at` is intentionally NOT set in the SET clause: the Slice-1 migration's
# `update_a2a_tenants_updated_at` BEFORE UPDATE trigger advances it unconditionally,
# and `created_at` is untouched by the UPDATE branch, so it is preserved automatically.

_SELECT_ALL_SQL = "SELECT * FROM a2a_tenants ORDER BY tenant"
_SELECT_ENABLED_SQL = "SELECT * FROM a2a_tenants WHERE enabled = $1 ORDER BY tenant"


def _iso_z(dt) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_registered_tenant(row) -> Dict[str, Any]:
    """Map the ``a2a_tenants`` row (snake_case) to the wire ``RegisteredTenant`` (camelCase)."""
    record: Dict[str, Any] = {
        "tenant": row["tenant"],
        "repo": row["repo"],
        "ref": row["ref"],
        "entryRole": row["entry_role"],
        "servingRoles": row["serving_roles"],
        "external": row["external"],
        "enabled": row["enabled"],
        "card": row["card"],
        "createdAt": _iso_z(row["created_at"]),
        "updatedAt": _iso_z(row["updated_at"]),
    }
    provider = row["provider"]
    if provider is not None:
        record["provider"] = provider
    return record


async def _upsert_tenant(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    ref = payload.get("ref", _REQUEST_DEFAULTS["ref"])
    external = payload.get("external", _REQUEST_DEFAULTS["external"])
    enabled = payload.get("enabled", _REQUEST_DEFAULTS["enabled"])

    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            _UPSERT_SQL,
            payload["tenant"],
            payload["repo"],
            ref,
            payload["entryRole"],
            payload["servingRoles"],
            external,
            payload.get("provider"),
            payload["card"],
            enabled,
        )
    return _row_to_registered_tenant(row), bool(row["created"])


async def _list_tenants(enabled: Optional[bool]) -> List[Dict[str, Any]]:
    async with get_db_connection() as conn:
        if enabled is None:
            rows = await conn.fetch(_SELECT_ALL_SQL)
        else:
            rows = await conn.fetch(_SELECT_ENABLED_SQL, enabled)
    return [_row_to_registered_tenant(row) for row in rows]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/tenants/register",
    summary="Self-register (idempotent upsert) an A2A runtime tenant",
    responses={
        201: {"description": "First registration of this tenant"},
        200: {"description": "Existing tenant updated"},
        403: {
            "description": "tenant/repo does not match the authenticated caller identity"
        },
        422: {"description": "Request or card failed schema validation"},
    },
)
async def register_tenant(
    body: Dict[str, Any] = Body(...),
    user: CurrentUser = Depends(require_user),
) -> JSONResponse:
    # 1. Structural validation against the frozen RegisterTenantRequest $def (this
    #    ALSO structurally validates `card` against agent-card.schema.json, since the
    #    request schema $refs it directly).
    envelope_errors = validate_register_request(body)
    if envelope_errors:
        logger.info(
            "a2a.tenants.register rejected: schema validation failed (%d errors)",
            len(envelope_errors),
        )
        raise HTTPException(status_code=422, detail={"errors": envelope_errors})

    # 2-4. Fail-closed self-registration identity binding (contract §3). Never writes
    #      on a mismatch, and runs BEFORE the deeper card-profile check below so an
    #      unauthorized caller learns nothing about why its card would or would not
    #      have validated.
    _authorize_self_registration(user, body)

    # 5. Card validation (contract §4): the Fuze-profile check PLUS the cross-field
    #    checks (interface tenant equality, in-cluster url unless external).
    tenant = body["tenant"]
    external = bool(body.get("external", _REQUEST_DEFAULTS["external"]))
    card = body["card"]
    card_errors = validate_card(card)
    card_errors.extend(_card_cross_checks(card, tenant, external))
    if card_errors:
        logger.info(
            "a2a.tenants.register rejected: card validation failed for tenant=%s (%d errors)",
            tenant,
            len(card_errors),
        )
        raise HTTPException(status_code=422, detail={"errors": card_errors})

    # 6. Idempotent upsert.
    record, created = await _upsert_tenant(body)
    logger.info(
        "a2a.tenants.register %s tenant=%s repo=%s",
        "created" if created else "updated",
        tenant,
        body["repo"],
    )
    return JSONResponse(
        status_code=201 if created else 200,
        content={"created": created, "record": record},
    )


@router.get(
    "/tenants",
    summary="List registered A2A tenants (the A2A server's resolved routing table)",
)
async def list_tenants(
    enabled: Optional[bool] = Query(
        None,
        description="Filter to served tenants only (what the A2A server asks for).",
    ),
    user: CurrentUser = Depends(require_admin),
) -> Dict[str, Any]:
    # x-pagination: exempt (tenant-registration.md §5) — bounded whole-set config read.
    tenants = await _list_tenants(enabled)
    logger.info(
        "a2a.tenants.list principal=%s enabled=%s count=%d",
        user.id,
        enabled,
        len(tenants),
    )
    return {"tenants": tenants, "count": len(tenants)}
