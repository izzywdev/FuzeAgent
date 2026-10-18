"""Client-credentials OIDC token minting for the A2A CALLER side.

The typed :class:`~fuze_a2a_client.A2AClient` takes a ``token`` and presents it as a
bearer on every call (see ``client.py`` ``_headers``). It does NOT decide *how* that
token is obtained — that is a deployment concern, deliberately kept out of the frozen
wire contract. This module fills the one gap the runtime otherwise leaves open: a pod
that must call a peer over A2A has to hold a valid ``aud=a2a`` access token, and
nothing was minting one.

It implements the OAuth 2.0 **client-credentials** grant (RFC 6749 §4.4) against the
family OIDC provider (FuzeFront's Authentik):

  1. discover the ``token_endpoint`` from the provider's OIDC discovery document
     (``oidcDiscoveryUrl`` in ``values-prod.yaml`` — fetched in-cluster to avoid a
     Cloudflare-tunnel hairpin; see ``deploy/helm/a2a-shared/GO-LIVE.md`` §1b),
  2. POST ``grant_type=client_credentials`` with the pod's ``client_id`` /
     ``client_secret`` (provisioned FuzeFront-side and delivered here as a sealed
     secret — read from the mounted secret file or env, **never** hardcoded),
  3. cache the returned access token and reuse it until it is about to expire,
     re-minting transparently on expiry.

The provider's scope mapping stamps ``{"repo": "<RepoName>", "aud": "a2a"}`` onto the
token (FuzeFront#364 — Option 2, repo-name JWTs), which is exactly what the callee
validates (``authz.md`` §2). The audience/scope this module requests is therefore
configuration, not a wire concern.

Transport is injected (``transport=``) exactly as in ``client.py`` so this is unit
testable without a network and without ``httpx``; the default transport needs
``httpx``. A ``ClientCredentialsTokenProvider`` is callable, so it drops straight into
``A2AClient(card, token=provider)`` — the client resolves the callable per request and
so always sends a fresh token.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Protocol

DEFAULT_AUDIENCE = "a2a"
#: Re-mint this many seconds BEFORE the token actually expires, so a token never
#: expires mid-flight between the provider handing it out and the callee validating it.
DEFAULT_EXPIRY_SKEW_SECONDS = 60.0
#: Fallback lifetime if the token endpoint omits ``expires_in`` (spec allows it).
DEFAULT_ASSUMED_TTL_SECONDS = 300.0
DISCOVERY_SUFFIX = "/.well-known/openid-configuration"


class TokenTransport(Protocol):
    """Minimal HTTP seam — the subset of ``httpx.Client`` this module uses.

    Both methods return an object exposing ``.json()`` and either ``.status_code`` or
    ``.raise_for_status()``; the default httpx transport satisfies this.
    """

    def get(self, url: str, *, headers: dict) -> Any: ...
    def post(self, url: str, *, data: dict, headers: dict) -> Any: ...


class TokenFetchError(RuntimeError):
    """Raised when a token could not be minted (discovery or grant failed)."""


class ClientCredentialsTokenProvider:
    """Mints and caches an ``aud=a2a`` OIDC token via the client-credentials grant.

    Thread-safe: the caller side (``a2a_transport``) drives A2A calls from multiple
    threads, so minting/caching is guarded by a lock and only one refresh happens at a
    time.

    Parameters mirror the deployment config (``values-prod.yaml`` ``a2a.auth`` +
    the sealed client secret):

    ``client_id`` / ``client_secret``
        The M2M credentials provisioned FuzeFront-side. ``client_secret`` is read from
        a mounted secret or env by :func:`token_provider_from_env`; never hardcode it.
    ``token_endpoint`` OR ``discovery_url``
        Supply the token endpoint directly, or a discovery URL to resolve it from. If
        only ``issuer`` is given, discovery is ``issuer + /.well-known/openid-configuration``.
    ``audience``
        Requested ``aud`` (default ``"a2a"``). Sent as the ``audience`` form field.
    ``scope``
        Optional space-separated scopes to request.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_endpoint: str | None = None,
        discovery_url: str | None = None,
        issuer: str | None = None,
        audience: str | None = DEFAULT_AUDIENCE,
        scope: str | None = None,
        transport: TokenTransport | None = None,
        expiry_skew_seconds: float = DEFAULT_EXPIRY_SKEW_SECONDS,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are both required")
        if not (token_endpoint or discovery_url or issuer):
            raise ValueError(
                "one of token_endpoint, discovery_url or issuer is required to locate "
                "the OIDC token endpoint"
            )
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_endpoint = token_endpoint
        # Locate discovery: an explicit URL wins; otherwise derive it from the issuer
        # (built by string join, not urljoin, so a trailing slash on the issuer can
        # never swallow the path). Unused when token_endpoint is given directly.
        if discovery_url:
            self._discovery_url = discovery_url
        elif issuer:
            self._discovery_url = issuer.rstrip("/") + DISCOVERY_SUFFIX
        else:
            self._discovery_url = None
        self._audience = audience
        self._scope = scope
        self._transport = transport
        self._skew = max(0.0, float(expiry_skew_seconds))
        self._now = time_fn

        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    # -- public API ---------------------------------------------------------
    def get_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid access token, minting or refreshing only when needed."""
        with self._lock:
            if not force_refresh and self._access_token and self._now() < self._expires_at:
                return self._access_token
            token, ttl = self._mint()
            self._access_token = token
            # Refresh a little early (skew) but never schedule expiry in the past.
            self._expires_at = self._now() + max(0.0, ttl - self._skew)
            return token

    def __call__(self) -> str:
        """Callable form, so the provider can be passed as ``A2AClient(token=...)``."""
        return self.get_token()

    def invalidate(self) -> None:
        """Drop the cached token so the next call re-mints (e.g. after a 401)."""
        with self._lock:
            self._access_token = None
            self._expires_at = 0.0

    # -- internals ----------------------------------------------------------
    def _resolve_token_endpoint(self) -> str:
        if self._token_endpoint:
            return self._token_endpoint
        assert self._discovery_url  # guaranteed by __init__
        resp = self._http().get(self._discovery_url, headers={"Accept": "application/json"})
        doc = _json_or_raise(resp, f"OIDC discovery ({self._discovery_url})")
        endpoint = doc.get("token_endpoint")
        if not endpoint:
            raise TokenFetchError(
                f"OIDC discovery document at {self._discovery_url} has no token_endpoint"
            )
        # Cache it: the token endpoint does not move between refreshes.
        self._token_endpoint = endpoint
        return endpoint

    def _mint(self) -> tuple[str, float]:
        endpoint = self._resolve_token_endpoint()
        form = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._audience:
            form["audience"] = self._audience
        if self._scope:
            form["scope"] = self._scope
        resp = self._http().post(
            endpoint,
            data=form,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        doc = _json_or_raise(resp, f"client-credentials grant ({endpoint})")
        token = doc.get("access_token")
        if not token:
            raise TokenFetchError(
                f"token endpoint {endpoint} returned no access_token "
                f"(error={doc.get('error')!r})"
            )
        ttl = doc.get("expires_in")
        try:
            ttl = float(ttl) if ttl is not None else DEFAULT_ASSUMED_TTL_SECONDS
        except (TypeError, ValueError):
            ttl = DEFAULT_ASSUMED_TTL_SECONDS
        return token, ttl

    def _http(self) -> TokenTransport:
        if self._transport is None:
            self._transport = _default_transport()
        return self._transport


def _json_or_raise(resp: Any, what: str) -> dict:
    """Turn a transport response into a JSON dict or a TokenFetchError.

    Tolerates both the httpx shape (``.status_code`` + ``.raise_for_status``) and a
    minimal test double that only implements ``.json()``.
    """
    status = getattr(resp, "status_code", None)
    if status is not None and status >= 400:
        body = ""
        try:
            body = resp.text  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - best-effort diagnostics only
            body = ""
        raise TokenFetchError(f"{what} failed: HTTP {status} {body}".strip())
    try:
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        raise TokenFetchError(f"{what} returned a non-JSON response: {exc}") from exc


def _default_transport() -> TokenTransport:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - exercised only without httpx
        raise ImportError(
            "ClientCredentialsTokenProvider's default transport needs httpx; install "
            "it (fuze-a2a-client[http]) or pass transport="
        ) from exc
    # Bounded timeout: minting a token must never hang a caller indefinitely (unlike the
    # A2A call itself, which legitimately blocks on exec escalations).
    return httpx.Client(timeout=float(os.environ.get("A2A_TOKEN_HTTP_TIMEOUT", "30")))


def _read_secret(env: dict, *, value_key: str, file_key: str) -> str | None:
    """Read a secret from an env var, or from a file named by ``<var>_FILE``.

    The file form is preferred for Kubernetes secret mounts (the value never lands in
    the process environment / ``/proc/<pid>/environ`` of a child agent sandbox).
    """
    path = env.get(file_key)
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                secret = fh.read().strip()
            if secret:
                return secret
        except OSError as exc:
            raise TokenFetchError(f"could not read {file_key}={path!r}: {exc}") from exc
    val = env.get(value_key)
    return val.strip() if val else None


def token_provider_from_env(
    env: dict | None = None,
    *,
    transport: TokenTransport | None = None,
) -> ClientCredentialsTokenProvider | None:
    """Build a provider from the caller-side A2A environment, or ``None`` if unconfigured.

    Returning ``None`` (rather than raising) when no ``client_id`` is present lets the
    caller fall back to a statically supplied ``A2A_TOKEN`` — the deployment chooses
    exactly one. Env contract (all ``A2A_*``, consistent with ``a2a_transport``):

    ======================= ===================================================
    ``A2A_CLIENT_ID``       OIDC client id of this pod's M2M provider. Presence
                            of this var is what turns the provider on.
    ``A2A_CLIENT_SECRET``   OIDC client secret, or ...
    ``A2A_CLIENT_SECRET_FILE`` ... a path to a mounted secret file (preferred).
    ``A2A_OIDC_DISCOVERY_URL`` OIDC discovery URL (== values ``oidcDiscoveryUrl``).
    ``A2A_OIDC_ISSUER_URL`` Issuer (== values ``oidcIssuerUrl``); discovery is
                            derived from it when no discovery URL is given.
    ``A2A_TOKEN_ENDPOINT``  Explicit token endpoint (skips discovery).
    ``A2A_TOKEN_AUDIENCE``  Requested audience (default ``a2a``).
    ``A2A_TOKEN_SCOPE``     Optional space-separated scopes.
    ======================= ===================================================
    """
    env = os.environ if env is None else env
    client_id = env.get("A2A_CLIENT_ID")
    if not client_id:
        return None
    client_secret = _read_secret(
        env, value_key="A2A_CLIENT_SECRET", file_key="A2A_CLIENT_SECRET_FILE"
    )
    if not client_secret:
        raise TokenFetchError(
            "A2A_CLIENT_ID is set but no client secret was found "
            "(set A2A_CLIENT_SECRET or A2A_CLIENT_SECRET_FILE)"
        )
    return ClientCredentialsTokenProvider(
        client_id=client_id,
        client_secret=client_secret,
        token_endpoint=env.get("A2A_TOKEN_ENDPOINT"),
        discovery_url=env.get("A2A_OIDC_DISCOVERY_URL"),
        issuer=env.get("A2A_OIDC_ISSUER_URL"),
        audience=env.get("A2A_TOKEN_AUDIENCE", DEFAULT_AUDIENCE),
        scope=env.get("A2A_TOKEN_SCOPE"),
        transport=transport,
    )


__all__ = [
    "ClientCredentialsTokenProvider",
    "TokenFetchError",
    "TokenTransport",
    "token_provider_from_env",
    "DEFAULT_AUDIENCE",
]
