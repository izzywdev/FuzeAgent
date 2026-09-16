"""Compose the running server from configuration.

Wires the pure pieces (``config`` -> ``adapter`` -> ``server``) to the concrete
Managed-Agents provider (``providers.get_provider``), a repo resolver that reads each
tenant's projection inputs from a checked-out tree, an OIDC authenticator, and
(contract v1.3.0, ``#203``) the orchestrator's HTTP tenant registry (``registry.py``).

Deliberately dependency-light so unit tests never import ``providers``/the SDK: the
git-sync of a tenant's ``ref``, the JWKS verifier construction, and the registry fetch
are all runtime concerns exercised here via injectable collaborators. The Helm chart,
image and secret wiring that supply ``VALUES_FILE`` / issuer URL / registry URL are
devops-engineer's slice — this module only consumes them.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

from .adapter import A2AAdapter
from .config import ServerConfig, TenantConfig, load_config, merge_tenant_sources
from .identity import OidcAuthenticator
from .loader import load_repo
from .net import require_http_url
from .registry import HttpGetJson, fetch_registry_tenants


class LocalRepoResolver:
    """Resolve a tenant's (manifest, roles) from ``<base_dir>/<tenant-name>``.

    The checkout/refresh of each repo at ``tenant.ref`` is performed out of band (an
    init/sidecar container the chart provides); this resolver only reads the tree.
    GitOps: the git ref is the source of truth, never live-mutated state.

    The directory is keyed on the TENANT name, matching what the repo-sync init
    container clones to (``/repos/<tenant>``). Keying on the repo slug instead only
    coincides while every tenant name equals its repo name — a second tenant over an
    existing repo (e.g. ``FuzeInfraOps`` over ``izzywdev/FuzeAgent``) would be read
    from the wrong directory.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def __call__(self, tenant: TenantConfig) -> tuple[dict, dict]:
        return load_repo(self.base_dir / tenant.tenant)


def _read_values(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve_config_with_registry(
    static_config: ServerConfig,
    registry_url: str | None,
    *,
    http_get: HttpGetJson | None = None,
) -> ServerConfig:
    """UNION ``static_config.tenants`` with the HTTP registry's, if configured.

    Kept as its own env-free, provider-free helper (mirrors ``_build_verifier``'s
    injectable collaborators) so it is unit-testable with a mocked ``http_get`` and
    without importing ``providers`` — ``build_from_env``'s module docstring: "dependency-
    light so unit tests never import it".

    An unset/empty ``registry_url`` is a no-op: ``static_config`` is returned unchanged,
    matching pre-#203 behaviour exactly (purely additive). When set, an unreachable
    registry (``fetch_registry_tenants`` already logged + returned ``()``) also degrades
    to ``static_config.tenants`` unchanged — never a crash, never an outage window.
    """
    if not registry_url:
        return static_config
    registry_tenants = fetch_registry_tenants(registry_url, http_get=http_get)
    return dataclasses.replace(
        static_config,
        tenants=merge_tenant_sources(static_config.tenants, registry_tenants),
    )


def build_from_env():
    """Build ``(config, app)`` from environment.

    Env:
        A2A_VALUES_FILE   JSON of the values-interface document (a2a.* block).
        A2A_REPOS_DIR     directory holding tenant repo checkouts (default /repos).
        AGENT_PROVIDER    provider id (default anthropic).
        A2A_REGISTRY_URL  OPTIONAL orchestrator base URL (contract v1.3.0). When set,
                          the runtime tenant set is the UNION of this HTTP registry
                          (``GET {url}/a2a/tenants?enabled=true``) and the static
                          ``A2A_VALUES_FILE`` tenants (``config.merge_tenant_sources``);
                          an unreachable registry falls back to the static source alone
                          (``registry.fetch_registry_tenants``) rather than crashing.
                          Unset -> behaviour is byte-identical to pre-#203 (static only).
    """
    from providers import get_provider  # imported here so tests never need the SDK

    config: ServerConfig = _resolve_config_with_registry(
        load_config(_read_values(os.environ.get("A2A_VALUES_FILE"))),
        os.environ.get("A2A_REGISTRY_URL"),
    )
    provider = get_provider(os.environ.get("AGENT_PROVIDER") or "anthropic")
    resolver = LocalRepoResolver(os.environ.get("A2A_REPOS_DIR", "/repos"))
    adapter = A2AAdapter(config, provider, resolver)

    if config.auth is None:
        raise RuntimeError("A2A auth config is required (values.a2a.auth.oidcIssuerUrl)")
    authenticator = OidcAuthenticator(config.auth, token_verifier=_build_verifier(config))

    from .server import build_app

    return config, build_app(adapter, authenticator)


class _TokenIssuerMismatch(Exception):
    """Raised when a token's ``iss`` does not match the configured public issuer.

    Trust is anchored to ``oidcIssuerUrl`` even when the signing keys were fetched from an
    in-cluster ``oidcDiscoveryUrl`` override (FuzeFront#364 "Option B").
    """


#: ``oidcDiscoveryUrl`` is trusted operator config, but rejecting non-http(s) schemes up
#: front (``net.require_http_url``, shared with ``registry.py``'s registry-URL guard) is
#: cheap, correct hardening — ``urllib`` also honours ``file://``/``ftp://``, which on a
#: config-supplied URL would let a discovery URL read local files (Semgrep
#: ``dynamic-urllib-use-detected``).
_require_http_url = require_http_url


def _http_get_json(url: str) -> dict:  # pragma: no cover - network
    import urllib.request

    _require_http_url(url, "fetched URL")
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected -- scheme validated
    # to http/https by _require_http_url above (file://ftp:// rejected); URL is trusted
    # operator config (values-prod oidcDiscoveryUrl / oidcIssuerUrl), never user input.
    with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
        url, timeout=10
    ) as resp:  # noqa: S310 - scheme-guarded by _require_http_url above
        return json.loads(resp.read().decode("utf-8"))


def _resolve_jwks_url(auth, discovery_fetcher) -> str:
    """Decide where signing keys are fetched from.

    * ``oidc_discovery_url`` set  -> fetch that discovery document and use its
      ``jwks_uri`` (typically an in-cluster identity-provider URL — the provider is
      deployment config, never named here). Keys come from in-cluster.
    * ``oidc_discovery_url`` unset -> issuer-derived certs path — the UNCHANGED default.

    Both the discovery URL and the ``jwks_uri`` it yields are scheme-guarded to http(s)
    BEFORE any fetch, so a ``file://`` config value never reaches ``urllib``.
    """
    if auth.oidc_discovery_url:
        _require_http_url(auth.oidc_discovery_url, "auth.oidcDiscoveryUrl")
        discovery = discovery_fetcher(auth.oidc_discovery_url)
        jwks_uri = discovery.get("jwks_uri")
        if not jwks_uri:
            raise RuntimeError(
                f"OIDC discovery at {auth.oidc_discovery_url} has no jwks_uri"
            )
        return _require_http_url(jwks_uri, "OIDC discovery jwks_uri")
    return auth.oidc_issuer_url.rstrip("/") + "/protocol/openid-connect/certs"


def _build_verifier(
    config: ServerConfig,
    *,
    jwk_client_factory=None,
    discovery_fetcher=None,
    decoder=None,
):
    """Construct a JWKS-backed token verifier for the configured issuer.

    Uses ``PyJWT`` + ``PyJWKClient`` if available; returns ``None`` (fail-closed: every
    request unauthenticated) when neither a verifier lib nor issuer is configured, so a
    misconfiguration denies rather than silently trusting tokens.

    Key source honors ``auth.oidcDiscoveryUrl`` (see :func:`_resolve_jwks_url`), but the
    token's ``iss`` is ALWAYS validated against ``oidc_issuer_url`` — trust is anchored to
    the public issuer regardless of where the keys were fetched.

    The three collaborators are injectable so this is unit-testable without a network or a
    real signing key; production wiring falls back to PyJWT + urllib.
    """
    auth = config.auth
    if auth is None:
        return None

    if jwk_client_factory is None or decoder is None:
        try:
            import jwt
            from jwt import PyJWKClient
        except Exception:
            return None
        if jwk_client_factory is None:
            jwk_client_factory = PyJWKClient
        if decoder is None:

            def decoder(token, key, *, audience, issuer):  # pragma: no cover - needs PyJWT
                return jwt.decode(
                    token,
                    key,
                    algorithms=["RS256", "ES256"],
                    audience=audience,
                    issuer=issuer,
                    options={"require": ["exp"]},
                )

    if discovery_fetcher is None:
        discovery_fetcher = _http_get_json

    jwks_url = _resolve_jwks_url(auth, discovery_fetcher)
    jwk_client = jwk_client_factory(jwks_url)

    def verify(token: str) -> dict:
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        claims = decoder(
            token,
            signing_key,
            audience=auth.audience,
            issuer=auth.oidc_issuer_url,
        )
        # Anchor trust to the PUBLIC issuer even when keys came from the in-cluster
        # discovery override. Explicit belt-and-suspenders on top of the decoder's own
        # issuer check (values-interface auth.oidcDiscoveryUrl normative behavior).
        if claims.get("iss") != auth.oidc_issuer_url:
            raise _TokenIssuerMismatch(
                f"token iss {claims.get('iss')!r} != configured oidcIssuerUrl "
                f"{auth.oidc_issuer_url!r}"
            )
        return claims

    return verify


def main() -> None:  # pragma: no cover
    import uvicorn

    config, app = build_from_env()
    # Bind to loopback by default; the Helm chart sets HOST=0.0.0.0 EXPLICITLY so the
    # in-cluster Service can reach the pod. Never hardcode a bind-all default (CWE-605).
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=config.port)


if __name__ == "__main__":  # pragma: no cover
    main()
