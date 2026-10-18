"""Unit tests for ``registry.fetch_registry_tenants`` — the HTTP tenant-registry client
(tenant-registration.md, contract v1.3.0, ``#203`` decision #1).

No real network: ``http_get`` is injected exactly like ``runtime._build_verifier``'s
``discovery_fetcher``, so these tests never import/require ``httpx`` to actually connect.
"""

from __future__ import annotations

import logging

import pytest
from a2a.config import TenantConfig
from a2a.registry import fetch_registry_tenants

REGISTERED_TENANT = {
    "tenant": "FuzePlan",
    "repo": "izzywdev/FuzePlan",
    "ref": "main",
    "entryRole": "product-manager",
    "servingRoles": ["product-manager", "ux-designer"],
    "external": False,
    "enabled": True,
    "card": {"name": "FuzePlan agent", "supportedInterfaces": [{"tenant": "FuzePlan"}]},
    "createdAt": "2026-09-01T00:00:00Z",
    "updatedAt": "2026-09-01T00:00:00Z",
}


def _ok_http_get(body: dict):
    calls: list[tuple[str, float]] = []

    def _get(url: str, timeout: float) -> dict:
        calls.append((url, timeout))
        return body

    _get.calls = calls
    return _get


def test_fetch_parses_tenant_list_into_tenant_configs():
    http_get = _ok_http_get({"tenants": [REGISTERED_TENANT], "count": 1})

    tenants = fetch_registry_tenants("https://orchestrator.fuzefront.com", http_get=http_get)

    assert tenants == (
        TenantConfig(
            tenant="FuzePlan",
            repo="izzywdev/FuzePlan",
            enabled=True,
            ref="main",
            entry_role="product-manager",
            serving_roles=("product-manager", "ux-designer"),
            external=False,
            card=REGISTERED_TENANT["card"],
        ),
    )


def test_fetch_requests_enabled_true_and_the_right_path():
    http_get = _ok_http_get({"tenants": [], "count": 0})

    fetch_registry_tenants("https://orchestrator.fuzefront.com", http_get=http_get)

    assert http_get.calls == [
        ("https://orchestrator.fuzefront.com/a2a/tenants?enabled=true", 10.0)
    ]


def test_fetch_strips_trailing_slash_on_base_url():
    http_get = _ok_http_get({"tenants": [], "count": 0})

    fetch_registry_tenants("https://orchestrator.fuzefront.com/", http_get=http_get)

    assert http_get.calls[0][0] == "https://orchestrator.fuzefront.com/a2a/tenants?enabled=true"


def test_unreachable_registry_falls_back_to_empty_and_logs(caplog):
    def _raises(url: str, timeout: float) -> dict:
        raise TimeoutError("connect timed out")

    with caplog.at_level(logging.WARNING, logger="a2a.registry"):
        tenants = fetch_registry_tenants("https://orchestrator.fuzefront.com", http_get=_raises)

    assert tenants == ()
    assert any("unreachable or invalid" in rec.message for rec in caplog.records)


def test_malformed_body_falls_back_to_empty_and_logs(caplog):
    http_get = _ok_http_get({"nope": "not a TenantList"})

    with caplog.at_level(logging.WARNING, logger="a2a.registry"):
        tenants = fetch_registry_tenants("https://orchestrator.fuzefront.com", http_get=http_get)

    assert tenants == ()
    assert any("unreachable or invalid" in rec.message for rec in caplog.records)


@pytest.mark.parametrize("bad_url", ["file:///etc/passwd", "ftp://orchestrator/a2a"])
def test_non_http_base_url_is_rejected_without_a_fetch_attempt(bad_url, caplog):
    calls: list[str] = []

    def _get(url: str, timeout: float) -> dict:
        calls.append(url)
        return {"tenants": []}

    with caplog.at_level(logging.WARNING, logger="a2a.registry"):
        tenants = fetch_registry_tenants(bad_url, http_get=_get)

    assert tenants == ()
    assert calls == []  # the fetch never happened


def test_default_enabled_true_and_default_ref_main_when_omitted():
    minimal = {
        "tenant": "Exec-cto",
        "repo": "izzywdev/FuzeInfra",
        "entryRole": "cto",
        "servingRoles": ["cto"],
        "card": {"name": "exec-cto"},
        "createdAt": "2026-09-01T00:00:00Z",
        "updatedAt": "2026-09-01T00:00:00Z",
    }
    http_get = _ok_http_get({"tenants": [minimal], "count": 1})

    (tenant,) = fetch_registry_tenants("https://orchestrator.fuzefront.com", http_get=http_get)

    assert tenant.ref == "main"
    assert tenant.enabled is True
    assert tenant.card == {"name": "exec-cto"}
