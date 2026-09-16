"""HTTP client for the orchestrator's runtime tenant registry.

Contract v1.3.0 (``agent-templates/contracts/a2a/v1/tenant-registration.md``, decided in
`izzywdev/FuzeAgent#203 <https://github.com/izzywdev/FuzeAgent/issues/203>`_): the shared
A2A server stays **stateless and DB-free** — it never owns a DB client (no asyncpg here).
Instead it fetches its runtime tenant set from the orchestrator over plain HTTP
(``httpx``) and unions it with the existing static ``A2A_VALUES_FILE`` source
(``config.merge_tenant_sources``) so there is never a window where an enabled tenant
resolves from **neither** (#203). A registry that is unreachable, times out, or returns
a malformed body is logged and treated as an EMPTY tenant set here — the caller's union
with the static source is what keeps the server serving.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .config import TenantConfig, tenant_from_registered
from .net import require_http_url

log = logging.getLogger(__name__)

#: ``(url, timeout_seconds) -> parsed JSON body``. Injectable so tests never hit a real
#: network (mirrors ``runtime._build_verifier``'s injectable ``discovery_fetcher``).
HttpGetJson = Callable[[str, float], dict[str, Any]]


def _httpx_get_json(url: str, timeout: float) -> dict[str, Any]:  # pragma: no cover - network
    import httpx  # imported lazily: importing this module never requires httpx installed

    resp = httpx.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_registry_tenants(
    base_url: str,
    *,
    http_get: HttpGetJson | None = None,
    timeout: float = 10.0,
) -> tuple[TenantConfig, ...]:
    """Fetch the enabled tenant set from ``GET {base_url}/a2a/tenants?enabled=true``.

    Returns a ``TenantList`` (tenant-registration.schema.json) mapped into
    ``TenantConfig`` tuples, each carrying its already-projected ``card`` as data — no
    repo clone, no re-projection (decision #2). ``GET /a2a/tenants`` is
    ``x-pagination: exempt`` (tenant-registration.md §5): it is a bounded whole-set
    config read, so no cursor/paging is applied here.

    On ANY failure — unreachable host, timeout, non-2xx, malformed JSON, a body missing
    ``tenants`` — this logs a WARNING **and returns an empty tuple** rather than raising.
    The caller (``runtime._resolve_config_with_registry``) unions this with the static
    source, so an unreachable registry degrades to static-only tenants rather than
    crashing the stateless server (#203: "never a window where an enabled tenant
    resolves from neither").
    """
    fetch = http_get or _httpx_get_json
    url = base_url.rstrip("/") + "/a2a/tenants?enabled=true"
    try:
        require_http_url(url, "A2A_REGISTRY_URL")
        body = fetch(url, timeout)
        records = body["tenants"]
        return tuple(tenant_from_registered(r) for r in records)
    except Exception:
        log.warning(
            "a2a tenant registry unreachable or invalid at %s; falling back to the "
            "static A2A_VALUES_FILE tenant source",
            url,
            exc_info=True,
        )
        return ()
