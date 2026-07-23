"""Compose the running server from configuration.

Wires the pure pieces (``config`` -> ``adapter`` -> ``server``) to the concrete
Managed-Agents provider (``providers.get_provider``), a repo resolver that reads each
tenant's projection inputs from a checked-out tree, and an OIDC authenticator.

Deliberately dependency-light so unit tests never import it: the git-sync of a
tenant's ``ref`` and the JWKS verifier construction are runtime concerns. The Helm
chart, image and secret wiring that supply ``VALUES_FILE`` / issuer URL are
devops-engineer's slice — this module only consumes them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .adapter import A2AAdapter
from .config import ServerConfig, TenantConfig, load_config
from .identity import OidcAuthenticator
from .loader import load_repo


class LocalRepoResolver:
    """Resolve a tenant's (manifest, roles) from ``<base_dir>/<repo-name>``.

    The checkout/refresh of each repo at ``tenant.ref`` is performed out of band (an
    init/sidecar container the chart provides); this resolver only reads the tree.
    GitOps: the git ref is the source of truth, never live-mutated state.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def __call__(self, tenant: TenantConfig) -> tuple[dict, dict]:
        name = tenant.repo.rsplit("/", 1)[-1]
        return load_repo(self.base_dir / name)


def _read_values(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_from_env():
    """Build ``(config, app)`` from environment.

    Env:
        A2A_VALUES_FILE   JSON of the values-interface document (a2a.* block).
        A2A_REPOS_DIR     directory holding tenant repo checkouts (default /repos).
        AGENT_PROVIDER    provider id (default anthropic).
    """
    from providers import get_provider  # imported here so tests never need the SDK

    config: ServerConfig = load_config(_read_values(os.environ.get("A2A_VALUES_FILE")))
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


#: Only network schemes are ever fetched. ``urllib`` also honours ``file://``/``ftp://``
#: which, on a config-supplied URL, would let a discovery URL read local files (Semgrep
#: ``dynamic-urllib-use-detected``). ``oidcDiscoveryUrl`` is trusted operator config, but
#: rejecting non-http(s) schemes up front is cheap, correct hardening.
_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


def _require_http_url(url: str, what: str) -> str:
    """Return ``url`` if it is an ``http(s)`` URL, else raise a config error.

    Guards every fetch of a config-supplied URL against ``file://``/``ftp://``/etc. so a
    dynamic URL can never be coerced into reading local files or other schemes.
    """
    from urllib.parse import urlparse

    scheme = urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise RuntimeError(
            f"{what} must be an http(s) URL (got scheme {scheme or '(none)'!r}): {url!r}"
        )
    return url


def _http_get_json(url: str) -> dict:  # pragma: no cover - network
    import urllib.request

    _require_http_url(url, "fetched URL")
    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - scheme-guarded above
        return json.loads(resp.read().decode("utf-8"))


def _resolve_jwks_url(auth, discovery_fetcher) -> str:
    """Decide where signing keys are fetched from.

    * ``oidc_discovery_url`` set  -> fetch that discovery document and use its
      ``jwks_uri`` (typically an in-cluster Authentik URL). Keys come from in-cluster.
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
