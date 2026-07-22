"""Transport-credential -> trusted caller identity (authz.md §2).

The ONLY trusted caller identity is the validated claim from the transport credential
(the OIDC bearer token's ``callerClaim``, optionally corroborated by the mTLS client
cert subject). Network position is never identity; an unauthenticated in-cluster
request is rejected exactly as an external one is.

Token *signature* validation (JWKS fetch, ``aud``/``iss``/``exp`` checks) is injected
as a ``token_verifier`` so this module stays testable and free of a network dependency.
Crucially the default is FAIL-CLOSED: with no verifier configured, every request is
unauthenticated — we never trust an unverified token's claims.
"""

from __future__ import annotations

from typing import Callable, Protocol

from .authz import AuthContext
from .config import AuthConfig

#: (raw_token) -> claims dict. MUST validate signature/iss/aud/exp and raise on failure.
TokenVerifier = Callable[[str], dict]


class Authenticator(Protocol):
    def authenticate(self, headers: "HeaderLike") -> AuthContext | None:
        """Return a trusted AuthContext, or None if the request is unauthenticated."""
        ...


class HeaderLike(Protocol):
    def get(self, key: str, default=None): ...


def _bearer(headers: HeaderLike) -> str | None:
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


class OidcAuthenticator:
    """Validate the bearer token via an injected verifier, read the caller claim.

    ``scopes`` are read from a ``scope`` (space-delimited) or ``scp`` (list) claim, as
    commonly issued. The mTLS subject header (set by Traefik after cert validation) is
    accepted only as a SECOND factor: it must agree with the token's caller.
    """

    def __init__(
        self,
        auth: AuthConfig,
        token_verifier: TokenVerifier | None = None,
        *,
        mtls_subject_header: str = "x-forwarded-tls-client-cert-subject",
    ):
        self._auth = auth
        self._verify = token_verifier
        self._mtls_header = mtls_subject_header

    def authenticate(self, headers: HeaderLike) -> AuthContext | None:
        token = _bearer(headers)
        if not token or self._verify is None:
            return None  # fail closed: no verifier => nothing is trusted
        try:
            claims = self._verify(token)
        except Exception:
            return None
        caller = claims.get(self._auth.caller_claim)
        if not caller:
            return None
        scopes = _scopes(claims)
        return AuthContext(caller=str(caller), scopes=frozenset(scopes), authenticated=True)


def _scopes(claims: dict) -> set[str]:
    raw = claims.get("scope") or claims.get("scp") or []
    if isinstance(raw, str):
        return set(raw.split())
    if isinstance(raw, (list, tuple)):
        return {str(s) for s in raw}
    return set()


class StaticAuthenticator:
    """Test/dev authenticator: maps a bearer token verbatim to a caller identity.

    NOT for production — it performs no signature validation. Used to drive the server
    in unit tests and local runs without an OIDC issuer.
    """

    def __init__(self, token_to_caller: dict[str, str], scopes: dict[str, set[str]] | None = None):
        self._map = token_to_caller
        self._scopes = scopes or {}

    def authenticate(self, headers: HeaderLike) -> AuthContext | None:
        token = _bearer(headers)
        caller = self._map.get(token) if token else None
        if not caller:
            return None
        return AuthContext(caller=caller, scopes=frozenset(self._scopes.get(caller, set())))
