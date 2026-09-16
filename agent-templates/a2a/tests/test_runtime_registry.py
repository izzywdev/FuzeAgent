"""Unit tests for ``runtime._resolve_config_with_registry`` — composing the static
``A2A_VALUES_FILE`` tenant set with the orchestrator's HTTP registry (tenant-
registration.md, contract v1.3.0, ``#203`` decision #1).

Kept separate from ``build_from_env`` (which additionally imports ``providers``) so
these never need the Managed-Agents SDK; the registry HTTP call is injected exactly
like ``runtime._build_verifier``'s ``discovery_fetcher`` — no real network.
"""

from __future__ import annotations

import logging

from a2a.config import ServerConfig, TenantConfig
from a2a.runtime import _resolve_config_with_registry

REGISTERED_FUZEPLAN = {
    "tenant": "FuzePlan",
    "repo": "izzywdev/FuzePlan",
    "ref": "main",
    "entryRole": "product-manager",
    "servingRoles": ["product-manager"],
    "external": False,
    "enabled": True,
    "card": {"name": "FuzePlan agent"},
    "createdAt": "2026-09-01T00:00:00Z",
    "updatedAt": "2026-09-01T00:00:00Z",
}


def _static_config() -> ServerConfig:
    return ServerConfig(
        enabled=True,
        tenants=(TenantConfig(tenant="FuzeFront", repo="izzywdev/FuzeFront", enabled=True),),
    )


def test_no_registry_url_is_a_pure_passthrough():
    static = _static_config()

    resolved = _resolve_config_with_registry(static, None)

    assert resolved is static  # unchanged object, not just equal -- true no-op


def test_registry_tenants_are_unioned_with_static_tenants():
    static = _static_config()

    def http_get(url: str, timeout: float) -> dict:
        assert url == "https://orchestrator.fuzefront.com/a2a/tenants?enabled=true"
        return {"tenants": [REGISTERED_FUZEPLAN], "count": 1}

    resolved = _resolve_config_with_registry(
        static, "https://orchestrator.fuzefront.com", http_get=http_get
    )

    names = {t.tenant for t in resolved.tenants}
    assert names == {"FuzeFront", "FuzePlan"}
    # a tenant sourced purely from the registry resolves through the same ServerConfig
    # lookup adapter._tenant_or_none uses.
    fuzeplan = resolved.tenant("FuzePlan")
    assert fuzeplan is not None
    assert fuzeplan.card == {"name": "FuzePlan agent"}
    # the static tenant is untouched
    assert resolved.tenant("FuzeFront") is not None


def test_unreachable_registry_falls_back_to_static_without_crashing(caplog):
    static = _static_config()

    def http_get(url: str, timeout: float) -> dict:
        raise ConnectionError("connection refused")

    with caplog.at_level(logging.WARNING, logger="a2a.registry"):
        resolved = _resolve_config_with_registry(
            static, "https://orchestrator.fuzefront.com", http_get=http_get
        )

    # no exception propagated, and the static tenant set is exactly what is served
    assert resolved.tenants == static.tenants
    assert resolved.tenant("FuzeFront") is not None
    assert any("unreachable or invalid" in rec.message for rec in caplog.records)


def test_empty_registry_url_string_is_also_a_passthrough():
    static = _static_config()

    resolved = _resolve_config_with_registry(static, "")

    assert resolved is static
