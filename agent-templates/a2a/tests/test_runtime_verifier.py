"""Unit tests for the OIDC/JWKS verifier construction (runtime._build_verifier).

Covers the ``auth.oidcDiscoveryUrl`` override (values-interface, FuzeFront#364 "Option B"):
signing keys may be fetched from an in-cluster discovery URL, but trust stays anchored to
the PUBLIC ``oidcIssuerUrl``. The three collaborators (discovery fetch, JWKS client, token
decode) are injected so no network or real signing key is needed.
"""

from __future__ import annotations

import pytest

from a2a.config import AuthConfig, ServerConfig
from a2a.runtime import _build_verifier

ISSUER = "https://auth.prod.fuzefront.com"
DISCOVERY = (
    "http://authentik-server.identity.svc.cluster.local:9000"
    "/application/o/fuzeagent-a2a/.well-known/openid-configuration"
)
IN_CLUSTER_JWKS = "http://authentik-server.identity.svc.cluster.local:9000/application/o/fuzeagent-a2a/jwks/"


class _FakeSigningKey:
    key = "PUBLIC-KEY"


class _FakeJwkClient:
    """Records the JWKS URL it was constructed with; returns a fixed signing key."""

    instances: list["_FakeJwkClient"] = []

    def __init__(self, jwks_url: str):
        self.jwks_url = jwks_url
        _FakeJwkClient.instances.append(self)

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey()


def _config(discovery_url: str | None = None, audience: str | None = "a2a") -> ServerConfig:
    return ServerConfig(
        auth=AuthConfig(
            oidc_issuer_url=ISSUER,
            oidc_discovery_url=discovery_url,
            audience=audience,
        )
    )


@pytest.fixture(autouse=True)
def _reset_clients():
    _FakeJwkClient.instances.clear()
    yield
    _FakeJwkClient.instances.clear()


def _claims_decoder(claims: dict):
    """A decoder that ignores the (unusable-in-a-test) signing key and returns preset
    claims verbatim — so we exercise OUR issuer-anchoring, not PyJWT's signature check."""

    def decode(token, key, *, audience, issuer):
        assert key == "PUBLIC-KEY"  # the key really came from the JWKS client
        return dict(claims)

    return decode


def test_discovery_override_is_used_for_key_fetch_when_set():
    fetched: list[str] = []

    def discovery_fetcher(url: str) -> dict:
        fetched.append(url)
        return {"issuer": "http://authentik-internal", "jwks_uri": IN_CLUSTER_JWKS}

    verify = _build_verifier(
        _config(discovery_url=DISCOVERY),
        jwk_client_factory=_FakeJwkClient,
        discovery_fetcher=discovery_fetcher,
        decoder=_claims_decoder({"iss": ISSUER, "sub": "FuzeSales"}),
    )

    # discovery was fetched from the override URL, and the JWKS client points in-cluster.
    assert fetched == [DISCOVERY]
    assert _FakeJwkClient.instances[-1].jwks_url == IN_CLUSTER_JWKS
    # a token whose iss matches the public issuer is accepted.
    assert verify("token")["sub"] == "FuzeSales"


def test_falls_back_to_issuer_derived_discovery_when_unset():
    fetched: list[str] = []

    def discovery_fetcher(url: str) -> dict:  # must NOT be called in the default path
        fetched.append(url)
        return {"jwks_uri": "http://should-not-be-used"}

    verify = _build_verifier(
        _config(discovery_url=None),
        jwk_client_factory=_FakeJwkClient,
        discovery_fetcher=discovery_fetcher,
        decoder=_claims_decoder({"iss": ISSUER, "sub": "FuzeSales"}),
    )

    assert fetched == []  # no discovery fetch on the unchanged default path
    assert _FakeJwkClient.instances[-1].jwks_url == ISSUER + "/protocol/openid-connect/certs"
    assert verify("token")["sub"] == "FuzeSales"


def test_iss_still_validated_against_issuer_even_with_discovery_override():
    # Keys fetched in-cluster, but the token's iss is the in-cluster host, NOT the public
    # issuer -> must be REJECTED (verifier raises; the authenticator treats that as None).
    verify = _build_verifier(
        _config(discovery_url=DISCOVERY),
        jwk_client_factory=_FakeJwkClient,
        discovery_fetcher=lambda url: {"jwks_uri": IN_CLUSTER_JWKS},
        decoder=_claims_decoder(
            {"iss": "http://authentik-server.identity.svc.cluster.local:9000", "sub": "FuzeSales"}
        ),
    )
    with pytest.raises(Exception):
        verify("token-with-internal-iss")


def test_matching_iss_accepted_with_discovery_override():
    verify = _build_verifier(
        _config(discovery_url=DISCOVERY),
        jwk_client_factory=_FakeJwkClient,
        discovery_fetcher=lambda url: {"jwks_uri": IN_CLUSTER_JWKS},
        decoder=_claims_decoder({"iss": ISSUER, "sub": "FuzeSales", "aud": "a2a"}),
    )
    claims = verify("good-token")
    assert claims["iss"] == ISSUER
    assert claims["sub"] == "FuzeSales"


def test_discovery_without_jwks_uri_is_a_config_error():
    with pytest.raises(RuntimeError):
        _build_verifier(
            _config(discovery_url=DISCOVERY),
            jwk_client_factory=_FakeJwkClient,
            discovery_fetcher=lambda url: {"issuer": "x"},  # no jwks_uri
            decoder=_claims_decoder({"iss": ISSUER}),
        )


def test_no_auth_returns_none_fail_closed():
    assert _build_verifier(ServerConfig(auth=None)) is None
