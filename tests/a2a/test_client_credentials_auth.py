"""Conformance tests for the caller-side client-credentials token provider
(``fuze_a2a_client.auth``) and the ``A2AClient`` callable-token seam.

No live server and no network: the token endpoint + OIDC discovery are served by an
in-test fake transport, and the clock is injected, so the cache/refresh timing is
deterministic. This is the unit coverage for the token-fetch/refresh path added in
contract client 1.4.0 (the runtime half of FuzeInfra#981).
"""
from __future__ import annotations

import pytest

from fuze_a2a_client import (
    A2AClient,
    AgentCard,
    ClientCredentialsTokenProvider,
    TokenFetchError,
    token_provider_from_env,
)

from _harness import MockTransport

pytestmark = pytest.mark.conformance

DISCOVERY_URL = (
    "http://authentik-server.fuzefront.svc.cluster.local:9000"
    "/application/o/fuzefront/.well-known/openid-configuration"
)
TOKEN_ENDPOINT = (
    "http://authentik-server.fuzefront.svc.cluster.local:9000"
    "/application/o/token/"
)
ISSUER = "https://app.fuzefront.com/application/o/fuzefront/"


# ---------------------------------------------------------------------------
# Fake token transport (get: discovery, post: the grant)
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = "" if isinstance(payload, dict) else str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeTokenTransport:
    """Serves a discovery doc on GET and a queue of grant responses on POST.

    Every request is recorded so a test can assert *how many times* the endpoint was
    hit — the whole point of caching is that a warm token issues zero POSTs.
    """

    def __init__(self, *, discovery=None, token_responses=None):
        self._discovery = (
            discovery if discovery is not None else {"token_endpoint": TOKEN_ENDPOINT}
        )
        self._token_responses = list(token_responses or [])
        self.get_calls: list[str] = []
        self.post_calls: list[dict] = []

    def get(self, url, *, headers):
        self.get_calls.append(url)
        return _Resp(self._discovery)

    def post(self, url, *, data, headers):
        self.post_calls.append({"url": url, "data": data, "headers": headers})
        if not self._token_responses:
            raise AssertionError("unexpected extra token POST (cache should have served it)")
        nxt = self._token_responses.pop(0)
        if isinstance(nxt, _Resp):
            return nxt
        return _Resp(nxt)


class _Clock:
    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _grant(token, expires_in=300):
    return {"access_token": token, "token_type": "Bearer", "expires_in": expires_in}


# ---------------------------------------------------------------------------
# Minting, caching, refresh
# ---------------------------------------------------------------------------
def test_mints_via_client_credentials_and_resolves_endpoint_from_discovery():
    tx = FakeTokenTransport(token_responses=[_grant("tok-1")])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret",
        discovery_url=DISCOVERY_URL, transport=tx, time_fn=_Clock(),
    )

    assert p.get_token() == "tok-1"

    # discovery was consulted once, then the grant POSTed once
    assert tx.get_calls == [DISCOVERY_URL]
    assert len(tx.post_calls) == 1
    sent = tx.post_calls[0]
    assert sent["url"] == TOKEN_ENDPOINT
    assert sent["data"]["grant_type"] == "client_credentials"
    assert sent["data"]["client_id"] == "cid"
    assert sent["data"]["client_secret"] == "secret"
    assert sent["data"]["audience"] == "a2a"  # default M2M audience


def test_token_is_cached_within_ttl():
    tx = FakeTokenTransport(token_responses=[_grant("tok-1")])  # only ONE grant queued
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret",
        token_endpoint=TOKEN_ENDPOINT, transport=tx, time_fn=_Clock(),
    )

    assert p.get_token() == "tok-1"
    assert p.get_token() == "tok-1"
    assert p.get_token() == "tok-1"
    # served from cache: exactly one grant, and (explicit endpoint) zero discovery GETs
    assert len(tx.post_calls) == 1
    assert tx.get_calls == []


def test_refreshes_after_expiry():
    clock = _Clock()
    tx = FakeTokenTransport(
        token_responses=[_grant("tok-1", expires_in=300), _grant("tok-2", expires_in=300)]
    )
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret",
        token_endpoint=TOKEN_ENDPOINT, transport=tx,
        expiry_skew_seconds=60, time_fn=clock,
    )

    assert p.get_token() == "tok-1"
    # still fresh just before the skew window opens (300 - 60 = 240)
    clock.advance(239)
    assert p.get_token() == "tok-1"
    assert len(tx.post_calls) == 1
    # cross the refresh threshold -> re-mint
    clock.advance(2)  # now 241 > 240
    assert p.get_token() == "tok-2"
    assert len(tx.post_calls) == 2


def test_force_refresh_and_invalidate_remint():
    tx = FakeTokenTransport(token_responses=[_grant("tok-1"), _grant("tok-2"), _grant("tok-3")])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret",
        token_endpoint=TOKEN_ENDPOINT, transport=tx, time_fn=_Clock(),
    )

    assert p.get_token() == "tok-1"
    assert p.get_token(force_refresh=True) == "tok-2"
    p.invalidate()
    assert p.get_token() == "tok-3"
    assert len(tx.post_calls) == 3


def test_missing_expires_in_uses_assumed_ttl_and_still_caches():
    tx = FakeTokenTransport(token_responses=[{"access_token": "tok-1"}])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret",
        token_endpoint=TOKEN_ENDPOINT, transport=tx, time_fn=_Clock(),
    )
    assert p.get_token() == "tok-1"
    assert p.get_token() == "tok-1"  # cached (would raise on a 2nd POST)
    assert len(tx.post_calls) == 1


def test_scope_and_audience_are_forwarded():
    tx = FakeTokenTransport(token_responses=[_grant("tok-1")])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret", token_endpoint=TOKEN_ENDPOINT,
        audience="a2a", scope="a2a repo", transport=tx, time_fn=_Clock(),
    )
    p.get_token()
    data = tx.post_calls[0]["data"]
    assert data["audience"] == "a2a"
    assert data["scope"] == "a2a repo"


def test_issuer_derives_discovery_url():
    tx = FakeTokenTransport(token_responses=[_grant("tok-1")])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret", issuer=ISSUER,
        transport=tx, time_fn=_Clock(),
    )
    p.get_token()
    assert tx.get_calls == [ISSUER.rstrip("/") + "/.well-known/openid-configuration"]


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------
def test_http_error_from_token_endpoint_raises():
    tx = FakeTokenTransport(token_responses=[_Resp({"error": "invalid_client"}, status=401)])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="bad", token_endpoint=TOKEN_ENDPOINT,
        transport=tx, time_fn=_Clock(),
    )
    with pytest.raises(TokenFetchError):
        p.get_token()


def test_no_access_token_in_response_raises():
    tx = FakeTokenTransport(token_responses=[{"error": "unauthorized_client"}])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret", token_endpoint=TOKEN_ENDPOINT,
        transport=tx, time_fn=_Clock(),
    )
    with pytest.raises(TokenFetchError):
        p.get_token()


def test_discovery_without_token_endpoint_raises():
    tx = FakeTokenTransport(discovery={"issuer": ISSUER}, token_responses=[_grant("x")])
    p = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret", discovery_url=DISCOVERY_URL,
        transport=tx, time_fn=_Clock(),
    )
    with pytest.raises(TokenFetchError):
        p.get_token()


def test_requires_credentials_and_a_locator():
    with pytest.raises(ValueError):
        ClientCredentialsTokenProvider(client_id="", client_secret="s", token_endpoint=TOKEN_ENDPOINT)
    with pytest.raises(ValueError):
        ClientCredentialsTokenProvider(client_id="c", client_secret="", token_endpoint=TOKEN_ENDPOINT)
    with pytest.raises(ValueError):
        ClientCredentialsTokenProvider(client_id="c", client_secret="s")  # no endpoint/discovery/issuer


# ---------------------------------------------------------------------------
# Env factory
# ---------------------------------------------------------------------------
def test_from_env_unconfigured_returns_none():
    # No A2A_CLIENT_ID -> None, so the caller falls back to a static A2A_TOKEN.
    assert token_provider_from_env({}) is None
    assert token_provider_from_env({"A2A_TOKEN": "static"}) is None


def test_from_env_builds_provider_and_mints():
    tx = FakeTokenTransport(token_responses=[_grant("env-tok")])
    env = {
        "A2A_CLIENT_ID": "cid",
        "A2A_CLIENT_SECRET": "secret",
        "A2A_OIDC_DISCOVERY_URL": DISCOVERY_URL,
        "A2A_TOKEN_AUDIENCE": "a2a",
    }
    p = token_provider_from_env(env, transport=tx)
    assert isinstance(p, ClientCredentialsTokenProvider)
    assert p.get_token() == "env-tok"


def test_from_env_reads_secret_from_file(tmp_path):
    secret_file = tmp_path / "client-secret"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    tx = FakeTokenTransport(token_responses=[_grant("env-tok")])
    env = {
        "A2A_CLIENT_ID": "cid",
        "A2A_CLIENT_SECRET_FILE": str(secret_file),
        "A2A_TOKEN_ENDPOINT": TOKEN_ENDPOINT,
    }
    p = token_provider_from_env(env, transport=tx)
    p.get_token()
    assert tx.post_calls[0]["data"]["client_secret"] == "file-secret"  # trimmed


def test_from_env_client_id_without_secret_raises():
    with pytest.raises(TokenFetchError):
        token_provider_from_env({"A2A_CLIENT_ID": "cid"})


# ---------------------------------------------------------------------------
# A2AClient callable-token seam (refresh is transparent to the caller)
# ---------------------------------------------------------------------------
def test_a2aclient_accepts_provider_and_sends_fresh_bearer(mock_card):
    card = AgentCard.model_validate(mock_card)
    clock = _Clock()
    tx = FakeTokenTransport(
        token_responses=[_grant("tok-1", expires_in=300), _grant("tok-2", expires_in=300)]
    )
    provider = ClientCredentialsTokenProvider(
        client_id="cid", client_secret="secret", token_endpoint=TOKEN_ENDPOINT,
        expiry_skew_seconds=60, transport=tx, time_fn=clock,
    )

    rpc_url = str(card.supportedInterfaces[0].url)
    a2a_tx = MockTransport(
        responses={"SendMessage": lambda env: {"jsonrpc": "2.0", "id": env["id"], "result": {}}}
    )
    client = A2AClient(card, token=provider, transport=a2a_tx)

    client.send_message("hi", skill_id="product-manager")
    assert a2a_tx.sent[-1]["headers"]["Authorization"] == "Bearer tok-1"

    # token expires between calls; the client re-resolves the provider and sends tok-2
    # with NO change on the caller's side.
    clock.advance(241)
    client.send_message("still there?", skill_id="product-manager")
    assert a2a_tx.sent[-1]["headers"]["Authorization"] == "Bearer tok-2"
    assert a2a_tx.sent[-1]["url"] == rpc_url


def test_a2aclient_static_string_token_unchanged(mock_card):
    card = AgentCard.model_validate(mock_card)
    a2a_tx = MockTransport(
        responses={"SendMessage": lambda env: {"jsonrpc": "2.0", "id": env["id"], "result": {}}}
    )
    client = A2AClient(card, token="static-token", transport=a2a_tx)
    client.send_message("hi", skill_id="product-manager")
    assert a2a_tx.sent[-1]["headers"]["Authorization"] == "Bearer static-token"
