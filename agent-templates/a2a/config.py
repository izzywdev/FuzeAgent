"""Server configuration, parsed from the ``values-interface.schema.json`` shape.

This is the DATA that lets ONE shared server front many product/exec agents: a repo
onboards by adding an entry to ``a2a.tenants`` — never a new pod (values-interface
§description). We parse only; the Helm chart that supplies these values is
devops-engineer's slice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthConfig:
    oidc_issuer_url: str
    #: OPTIONAL override for where the server fetches OIDC discovery + JWKS
    #: (values-interface auth.oidcDiscoveryUrl). Typically an in-cluster URL. When set,
    #: keys are fetched from HERE while the token ``iss`` is STILL validated against
    #: ``oidc_issuer_url`` (the public issuer). When None, discovery is derived from
    #: ``oidc_issuer_url`` — the unchanged default path.
    oidc_discovery_url: str | None = None
    audience: str | None = None
    #: the token claim carrying the caller repo identity — its value is the ONLY
    #: trusted caller identity (authz.md §2 / values-interface auth.callerClaim).
    caller_claim: str = "sub"
    mtls_enabled: bool = False


@dataclass(frozen=True)
class ProviderBinding:
    name: str = "anthropic"
    environment_id: str | None = None
    vault_ids: tuple[str, ...] = ()
    memory_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class TenantConfig:
    tenant: str
    repo: str
    enabled: bool = False
    ref: str = "main"
    entry_role: str | None = None
    serving_roles: tuple[str, ...] = ()
    external: bool = False
    provider: ProviderBinding = field(default_factory=ProviderBinding)


@dataclass(frozen=True)
class ServerConfig:
    enabled: bool = False
    port: int = 8080
    protocol_version: str = "1.0"
    image_tag: str | None = None
    auth: AuthConfig | None = None
    card_key_id: str | None = None
    tenants: tuple[TenantConfig, ...] = ()

    def tenant(self, name: str) -> TenantConfig | None:
        for t in self.tenants:
            if t.tenant == name and t.enabled:
                return t
        return None


def _provider(d: dict | None) -> ProviderBinding:
    d = d or {}
    return ProviderBinding(
        name=d.get("name", "anthropic"),
        environment_id=d.get("environmentId"),
        vault_ids=tuple(d.get("vaultIds") or ()),
        memory_resources=tuple(d.get("memoryResources") or ()),
    )


def _tenant(d: dict) -> TenantConfig:
    return TenantConfig(
        tenant=d["tenant"],
        repo=d["repo"],
        enabled=bool(d.get("enabled", False)),
        ref=d.get("ref", "main"),
        entry_role=d.get("entryRole"),
        serving_roles=tuple(d.get("servingRoles") or ()),
        external=bool(d.get("external", False)),
        provider=_provider(d.get("provider")),
    )


def load_config(values: dict[str, Any]) -> ServerConfig:
    """Parse the ``{"a2a": {...}}`` values document into a ``ServerConfig``."""
    a2a = values.get("a2a", values)  # tolerate being handed the inner block directly
    auth_raw = a2a.get("auth")
    auth = None
    if auth_raw:
        mtls = auth_raw.get("mtls") or {}
        auth = AuthConfig(
            oidc_issuer_url=auth_raw["oidcIssuerUrl"],
            oidc_discovery_url=auth_raw.get("oidcDiscoveryUrl"),
            audience=auth_raw.get("audience"),
            caller_claim=auth_raw.get("callerClaim", "sub"),
            mtls_enabled=bool(mtls.get("enabled", False)),
        )
    signing = a2a.get("cardSigning") or {}
    image = a2a.get("image") or {}
    return ServerConfig(
        enabled=bool(a2a.get("enabled", False)),
        port=int((a2a.get("service") or {}).get("port", 8080)),
        protocol_version=a2a.get("protocolVersion", "1.0"),
        image_tag=image.get("tag"),
        auth=auth,
        card_key_id=signing.get("keyId"),
        tenants=tuple(_tenant(t) for t in (a2a.get("tenants") or [])),
    )
