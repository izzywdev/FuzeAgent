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


def _build_verifier(config: ServerConfig):
    """Construct a JWKS-backed token verifier for the configured issuer.

    Uses ``PyJWT`` + ``PyJWKClient`` if available; returns ``None`` (fail-closed: every
    request unauthenticated) when neither a verifier lib nor issuer is configured, so a
    misconfiguration denies rather than silently trusting tokens.
    """
    auth = config.auth
    if auth is None:
        return None
    try:  # pragma: no cover - exercised only in a real deployment
        import jwt
        from jwt import PyJWKClient
    except Exception:
        return None

    jwks_url = auth.oidc_issuer_url.rstrip("/") + "/protocol/openid-connect/certs"
    jwk_client = PyJWKClient(jwks_url)

    def verify(token: str) -> dict:  # pragma: no cover
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=auth.audience,
            options={"require": ["exp"]},
        )

    return verify


def main() -> None:  # pragma: no cover
    import uvicorn

    config, app = build_from_env()
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=config.port)


if __name__ == "__main__":  # pragma: no cover
    main()
