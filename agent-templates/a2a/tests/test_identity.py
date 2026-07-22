"""Unit tests for credential -> trusted identity (authz.md §2)."""

from __future__ import annotations

from a2a.config import AuthConfig
from a2a.identity import OidcAuthenticator, StaticAuthenticator


class Headers(dict):
    def get(self, key, default=None):
        # case-insensitive like starlette Headers
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


def test_oidc_fail_closed_without_verifier():
    auth = AuthConfig(oidc_issuer_url="https://x")
    a = OidcAuthenticator(auth, token_verifier=None)
    assert a.authenticate(Headers({"Authorization": "Bearer abc"})) is None


def test_oidc_reads_caller_claim_and_scopes():
    auth = AuthConfig(oidc_issuer_url="https://x", caller_claim="azp")
    a = OidcAuthenticator(
        auth, token_verifier=lambda t: {"azp": "FuzeSales", "scope": "a2a.read a2a.write"}
    )
    ctx = a.authenticate(Headers({"Authorization": "Bearer good"}))
    assert ctx.caller == "FuzeSales"
    assert ctx.scopes == frozenset({"a2a.read", "a2a.write"})


def test_oidc_rejects_when_verifier_raises():
    auth = AuthConfig(oidc_issuer_url="https://x")

    def boom(_):
        raise ValueError("bad signature")

    a = OidcAuthenticator(auth, token_verifier=boom)
    assert a.authenticate(Headers({"Authorization": "Bearer bad"})) is None


def test_oidc_no_bearer_is_unauthenticated():
    auth = AuthConfig(oidc_issuer_url="https://x")
    a = OidcAuthenticator(auth, token_verifier=lambda t: {"sub": "x"})
    assert a.authenticate(Headers({})) is None


def test_scp_list_claim():
    auth = AuthConfig(oidc_issuer_url="https://x")
    a = OidcAuthenticator(auth, token_verifier=lambda t: {"sub": "FuzeSales", "scp": ["a", "b"]})
    ctx = a.authenticate(Headers({"Authorization": "Bearer good"}))
    assert ctx.scopes == frozenset({"a", "b"})


def test_static_authenticator():
    a = StaticAuthenticator({"tok": "FuzeSales"}, {"FuzeSales": {"a2a.exec.escalate"}})
    ctx = a.authenticate(Headers({"Authorization": "Bearer tok"}))
    assert ctx.caller == "FuzeSales"
    assert "a2a.exec.escalate" in ctx.scopes
    assert a.authenticate(Headers({"Authorization": "Bearer nope"})) is None
