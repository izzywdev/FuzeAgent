"""Unit tests for parsing the values-interface config document."""

from __future__ import annotations

import json

import pytest
from a2a._contract import SCHEMA_DIR
from a2a.config import load_config
from jsonschema import Draft202012Validator

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
                        "http://idp-server.identity.svc.cluster.local:9000"
                        "/application/o/fuzeagent-a2a/.well-known/openid-configuration"
                    ),
                },
            }
        }
    )
    assert cfg.auth.oidc_issuer_url == "https://auth.prod.fuzefront.com"
    assert cfg.auth.oidc_discovery_url == (
        "http://idp-server.identity.svc.cluster.local:9000"
        "/application/o/fuzeagent-a2a/.well-known/openid-configuration"
    )


# --------------------------------------------------------------------------- #
# a2a.inClusterUrl — the per-product-pod endpoint (contract v1.2.0)
# --------------------------------------------------------------------------- #
PER_PRODUCT_VALUES = {
    "a2a": {
        "enabled": True,
        "inClusterUrl": "http://a2a-fuzeplan.fuzeplan.svc.cluster.local:8080/rpc",
        "service": {"type": "ClusterIP", "port": 8080},
        "auth": {"oidcIssuerUrl": "https://auth.prod.fuzefront.com"},
        "tenants": [
            {"tenant": "FuzePlan", "repo": "izzywdev/FuzePlan", "enabled": True},
        ],
    }
}


def test_in_cluster_url_defaults_to_none():
    """Unset -> None -> the generator's shared-server default. The shared deployment,
    whose values file has no `inClusterUrl`, is therefore unchanged."""
    assert load_config(VALUES).in_cluster_url is None


def test_in_cluster_url_parsed_when_set():
    cfg = load_config(PER_PRODUCT_VALUES)
    assert cfg.in_cluster_url == "http://a2a-fuzeplan.fuzeplan.svc.cluster.local:8080/rpc"


def test_empty_in_cluster_url_is_treated_as_unset():
    """An empty string from a half-templated chart value must fall back to the default,
    never be published as an empty `AgentInterface.url`."""
    assert load_config({"a2a": {"enabled": True, "inClusterUrl": ""}}).in_cluster_url is None


# --------------------------------------------------------------------------- #
# the frozen values interface itself (additionalProperties:false at every level,
# so a new key is only usable once the schema is versioned to accept it)
# --------------------------------------------------------------------------- #
def _values_validator() -> Draft202012Validator:
    schema = json.loads(
        (SCHEMA_DIR / "values-interface.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize("doc", [VALUES, PER_PRODUCT_VALUES])
def test_values_documents_validate_against_the_frozen_interface(doc):
    assert list(_values_validator().iter_errors(doc)) == []


def test_interface_still_rejects_undeclared_keys():
    """`additionalProperties: false` is what forces a key like `inClusterUrl` to be a
    deliberate, versioned schema change rather than an ad-hoc value."""
    bad = {"a2a": {"enabled": True, "inClusterUrlTypo": "http://x/rpc"}}
    assert list(_values_validator().iter_errors(bad))
