"""Environment -> RagConfig, with no default that can be silently wrong.

The rule this file exists to enforce: a value whose wrong default still lets the
process start is worse than no default at all. `CHROMA_HOST` defaulting to
"localhost" is exactly that — the pod starts, connects to nothing, and reports
an empty corpus forever.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import RagConfigError

# Chroma resolves this string with an import path, not a keyword. The orchestrator
# passed the literal "basic", which resolves to no class at all — so the client
# was constructed without the auth it appeared to be configuring. Naming the two
# real providers here keeps that mistake from being re-typed.
TOKEN_AUTH_PROVIDER = "chromadb.auth.token_authn.TokenAuthClientProvider"
BASIC_AUTH_PROVIDER = "chromadb.auth.basic_authn.BasicAuthClientProvider"

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUE


@dataclass(frozen=True)
class RagConfig:
    """Everything the retriever needs, validated.

    `database` is the Chroma *database* the family allocates to A2A on the shared
    FuzeInfra instance — one instance, its own database, per-tenant collections
    inside it. Sharing the instance without a dedicated database would put
    every product's collections in one flat namespace where a name collision is
    a cross-tenant data leak, not a mistake.
    """

    host: str
    port: int
    ssl: bool
    tenant: str
    database: str
    collection_prefix: str
    embedding_model: str
    auth_provider: str | None
    auth_credentials: str | None
    auth_header: str

    @property
    def enabled(self) -> bool:
        return True

    def collection_for(self, tenant: str) -> str:
        """Per-tenant collection name. Isolation is by collection, not by filter.

        A `where` filter on a shared collection is one forgotten argument away
        from returning another tenant's chunks. A separate collection cannot be
        read by omission.
        """
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in tenant.lower())
        if not slug:
            raise RagConfigError("tenant name is empty after slugification")
        return f"{self.collection_prefix}{slug}"

    def chroma_settings(self):
        """`chromadb.config.Settings` for this config, or None when unauthenticated.

        Kept here rather than in the client so the self-tests can assert the exact
        provider string without importing chromadb.
        """
        from chromadb.config import Settings  # imported lazily; see client.py

        if not self.auth_provider:
            return Settings()
        kwargs = {
            "chroma_client_auth_provider": self.auth_provider,
            "chroma_client_auth_credentials": self.auth_credentials,
        }
        if self.auth_provider == TOKEN_AUTH_PROVIDER:
            kwargs["chroma_auth_token_transport_header"] = self.auth_header
        return Settings(**kwargs)


def from_env(env: dict | None = None) -> RagConfig | None:
    """Build a config, or return None when RAG is deliberately off.

    None means "not enabled" and is the ONLY silent outcome. Enabled-but-broken
    raises: that is a deploy defect and must not present as a working pod.
    """
    env = os.environ if env is None else env

    def get(name, default=None):
        v = env.get(name, default)
        return v.strip() if isinstance(v, str) else v

    enabled = (get("A2A_RAG_ENABLED", "0") or "0").lower() in _TRUE
    if not enabled:
        return None

    host = get("CHROMA_HOST")
    if not host:
        raise RagConfigError(
            "A2A_RAG_ENABLED is set but CHROMA_HOST is not. Refusing to fall back to "
            "localhost: that is how RAG runs 'successfully' against nothing. Set "
            "CHROMA_HOST to the shared instance, or unset A2A_RAG_ENABLED."
        )

    try:
        port = int(get("CHROMA_PORT", "8000"))
    except (TypeError, ValueError) as exc:
        raise RagConfigError(f"CHROMA_PORT is not an integer: {get('CHROMA_PORT')!r}") from exc

    database = get("CHROMA_DATABASE")
    if not database:
        raise RagConfigError(
            "A2A_RAG_ENABLED is set but CHROMA_DATABASE is not. The shared instance is "
            "shared: without its own database, A2A's collections land in whatever "
            "namespace the default happens to be, alongside every other product's."
        )

    token = get("CHROMA_AUTH_TOKEN")
    basic = get("CHROMA_AUTH_BASIC")
    if token and basic:
        raise RagConfigError(
            "Both CHROMA_AUTH_TOKEN and CHROMA_AUTH_BASIC are set; pick one."
        )
    if token:
        provider, credentials = TOKEN_AUTH_PROVIDER, token
    elif basic:
        if ":" not in basic:
            raise RagConfigError("CHROMA_AUTH_BASIC must be 'user:password'.")
        provider, credentials = BASIC_AUTH_PROVIDER, basic
    elif (get("CHROMA_ALLOW_UNAUTHENTICATED", "0") or "0").lower() in _TRUE:
        # Local dev / CI against an ephemeral Chroma. Explicit, because an empty
        # credential silently meaning "no auth" is what shipped last time.
        provider, credentials = None, None
    else:
        raise RagConfigError(
            "A2A_RAG_ENABLED is set but no Chroma credential is configured. Set "
            "CHROMA_AUTH_TOKEN (preferred) or CHROMA_AUTH_BASIC, or set "
            "CHROMA_ALLOW_UNAUTHENTICATED=1 to say out loud that this instance has "
            "no auth. An empty credential is never treated as 'no auth wanted'."
        )

    return RagConfig(
        host=host,
        port=port,
        ssl=(get("CHROMA_SSL", "0") or "0").lower() in _TRUE,
        tenant=get("CHROMA_TENANT", "default_tenant"),
        database=database,
        collection_prefix=get("CHROMA_COLLECTION_PREFIX", "a2a-"),
        embedding_model=get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        auth_provider=provider,
        auth_credentials=credentials,
        auth_header=get("CHROMA_AUTH_HEADER", "Authorization"),
    )
