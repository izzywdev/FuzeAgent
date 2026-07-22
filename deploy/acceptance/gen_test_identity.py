#!/usr/bin/env python3
"""Mint an ephemeral OIDC test identity for the Phase-3 A2A acceptance gate.

Generates a throwaway RSA keypair, writes a JWKS the server will trust (served by
``jwks_server.py`` at ``<issuer>/protocol/openid-connect/certs`` — the Keycloak-style
path ``runtime._build_verifier`` fetches), and prints two signed JWTs as
``NAME=VALUE`` lines for ``$GITHUB_ENV``:

* ``A2A_TEST_OIDC_TOKEN``   — subject IS in the FuzePlan callee's ``providesTo``
                              allowlist (an authorized caller).
* ``A2A_TEST_UNAUTH_TOKEN`` — a VALID caller identity that is NOT in the allowlist,
                              so the callee (not the caller) must refuse it.

No secrets are stored: the keypair lives only for the job. The tokens contain only
``sub``/``aud``/``iss``/``exp``/``scope`` — base64url text (alphanumeric plus ``-_.``),
safe to place in ``$GITHUB_ENV`` and shell env without special-character breakage.

    python gen_test_identity.py --jwks-out /tmp/jwks.json \
        --issuer http://127.0.0.1:9099 --audience fuze-a2a-acceptance \
        --allowlisted-sub FuzeSales --unauth-sub FuzeStranger >> "$GITHUB_ENV"
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KID = "a2a-acceptance-key-1"
ALG = "RS256"


def _build_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return key, private_pem


def _jwks_for(public_key) -> dict:
    # PyJWT emits the RSA public JWK (n/e) as JSON; annotate with kid/use/alg so
    # PyJWKClient can select it by the token header's kid.
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": KID, "use": "sig", "alg": ALG})
    return {"keys": [jwk]}


def _mint(private_pem: str, *, sub: str, issuer: str, audience: str, ttl: int) -> str:
    now = int(time.time())
    claims = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + ttl,
        # A space-delimited scope claim, as commonly issued (identity._scopes reads it).
        "scope": "a2a.call",
    }
    return jwt.encode(claims, private_pem, algorithm=ALG, headers={"kid": KID})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jwks-out", required=True)
    ap.add_argument("--issuer", required=True)
    ap.add_argument("--audience", required=True)
    ap.add_argument("--allowlisted-sub", default="FuzeSales")
    ap.add_argument("--unauth-sub", default="FuzeStranger")
    ap.add_argument("--ttl", type=int, default=3600)
    args = ap.parse_args()

    key, private_pem = _build_keypair()
    with open(args.jwks_out, "w", encoding="utf-8") as fh:
        json.dump(_jwks_for(key.public_key()), fh)

    allowed = _mint(
        private_pem, sub=args.allowlisted_sub, issuer=args.issuer, audience=args.audience, ttl=args.ttl
    )
    unauth = _mint(
        private_pem, sub=args.unauth_sub, issuer=args.issuer, audience=args.audience, ttl=args.ttl
    )
    # Printed for `>> $GITHUB_ENV`. JWTs are single-line, no metacharacters.
    print(f"A2A_TEST_OIDC_TOKEN={allowed}")
    print(f"A2A_TEST_UNAUTH_TOKEN={unauth}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
