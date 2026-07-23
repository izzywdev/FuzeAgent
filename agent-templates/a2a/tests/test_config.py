"""Unit tests for parsing the values-interface config document."""

from __future__ import annotations

from a2a.config import load_config

VALUES = {
    "a2a": {
        "enabled": True,
        "image": {"repository": "ghcr.io/izzywdev/fuzeagent-a2a", "tag": "1.2.3"},
        "service": {"type": "ClusterIP", "port": 8080},
        "protocolVersion": "1.0",
        "auth": {
            "oidcIssuerUrl": "https://auth.prod.fuzefront.com",
            "audience": "a2a",
            "callerClaim": "azp",
            "mtls": {"enabled": True, "caSecretRef": {"name": "ca", "key": "tls.crt"}},
        },
        "cardSigning": {"keySecretRef": {"name": "k", "key": "jwk"}, "keyId": "fuze-a2a-2026-07"},
        "tenants": [
            {
                "tenant": "FuzePlan",
                "repo": "izzywdev/FuzePlan",
                "enabled": True,
                "ref": "main",
                "entryRole": "product-manager",
                "servingRoles": ["product-manager", "ux-designer"],
                "provider": {
                    "name": "anthropic",
                    "environmentId": "env-1",
                    "vaultIds": ["v1", "v2"],
                    "memoryResources": ["handoff"],
                },
            },
            {"tenant": "Exec-cto", "repo": "izzywdev/FuzeInfra", "enabled": False},
        ],
    }
}


def test_load_config_top_level():
    cfg = load_config(VALUES)
    assert cfg.enabled is True
    assert cfg.port == 8080
    assert cfg.protocol_version == "1.0"
    assert cfg.image_tag == "1.2.3"
    assert cfg.card_key_id == "fuze-a2a-2026-07"


def test_load_config_auth():
    cfg = load_config(VALUES)
    assert cfg.auth.oidc_issuer_url == "https://auth.prod.fuzefront.com"
    assert cfg.auth.caller_claim == "azp"
    assert cfg.auth.audience == "a2a"
    assert cfg.auth.mtls_enabled is True


def test_load_config_tenants_and_enabled_gate():
    cfg = load_config(VALUES)
    assert len(cfg.tenants) == 2
    fp = cfg.tenant("FuzePlan")
    assert fp is not None
    assert fp.entry_role == "product-manager"
    assert fp.serving_roles == ("product-manager", "ux-designer")
    assert fp.provider.vault_ids == ("v1", "v2")
    assert fp.provider.environment_id == "env-1"
    # disabled tenant is not resolvable via tenant()
    assert cfg.tenant("Exec-cto") is None


def test_load_config_accepts_inner_block():
    cfg = load_config(VALUES["a2a"])
    assert cfg.enabled is True


def test_default_caller_claim_is_sub():
    cfg = load_config({"a2a": {"enabled": True, "auth": {"oidcIssuerUrl": "https://x"}}})
    assert cfg.auth.caller_claim == "sub"


def test_oidc_discovery_url_defaults_to_none():
    # Purely additive: existing configs that omit it behave exactly as before.
    cfg = load_config(VALUES)
    assert cfg.auth.oidc_discovery_url is None


def test_oidc_discovery_url_parsed_when_set():
    cfg = load_config(
        {
            "a2a": {
                "enabled": True,
                "auth": {
                    "oidcIssuerUrl": "https://auth.prod.fuzefront.com",
                    "oidcDiscoveryUrl": (
                        "http://authentik-server.identity.svc.cluster.local:9000"
                        "/application/o/fuzeagent-a2a/.well-known/openid-configuration"
                    ),
                },
            }
        }
    )
    assert cfg.auth.oidc_issuer_url == "https://auth.prod.fuzefront.com"
    assert cfg.auth.oidc_discovery_url == (
        "http://authentik-server.identity.svc.cluster.local:9000"
        "/application/o/fuzeagent-a2a/.well-known/openid-configuration"
    )
