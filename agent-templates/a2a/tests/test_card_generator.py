"""Unit tests for the Agent Card projection (card-projection.md).

These assert the NORMATIVE projection rules and schema/profile conformance. Where the
frozen ``examples/*.json`` are hand-authored illustrations that differ from a rule
(notably tag ORDER, and the composed ``description`` prose), we assert the invariant
the contract actually fixes — schema validity and the derived tag SET — not byte
equality with the example.
"""

from __future__ import annotations

import json

import pytest
from a2a import card_generator as cg
from a2a.loader import load_repo
from a2a.validation import card_errors, validate_card
from fuze_a2a_client.card_models import FuzeA2AAgentCard


# --------------------------------------------------------------------------- #
# product projection (FuzePlan)
# --------------------------------------------------------------------------- #
def test_product_card_validates_against_schema_and_profile(fuzeplan_repo):
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles)
    assert card_errors(card) == []
    # Also round-trips through the generated pydantic card model.
    FuzeA2AAgentCard.model_validate(card)


def test_product_card_identity_and_interface(fuzeplan_repo):
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles)

    assert card["name"] == "FuzePlan agent"
    assert card["provider"] == {"organization": "FuzeOne", "url": "https://github.com/izzywdev"}
    assert card["version"] == cg.contract_version()  # tracks contracts/a2a/v1/VERSION (card-projection.md §version); not hard-coded
    assert card["documentationUrl"] == "https://github.com/izzywdev/FuzePlan"

    iface = card["supportedInterfaces"]
    assert len(iface) == 1
    assert iface[0]["url"] == cg.IN_CLUSTER_URL
    assert iface[0]["protocolBinding"] == "JSONRPC"
    assert iface[0]["protocolVersion"] == "1.0"
    assert iface[0]["tenant"] == "FuzePlan"


def test_interface_tenant_overrides_repo_name(fuzeplan_repo):
    """The card's AgentInterface.tenant is the ROUTING key, which is the tenant name,
    not the repo name. When a tenant is served from a differently-named repo (e.g.
    ``FuzeInfraOps`` over ``izzywdev/FuzePlan``) the card must advertise the tenant,
    else the values-interface rule 'tenant key == AgentInterface.tenant' is violated
    and dispatch to that tenant is unroutable."""
    manifest, roles = load_repo(fuzeplan_repo)

    default = cg.project_product_card(manifest, roles)
    assert default["supportedInterfaces"][0]["tenant"] == "FuzePlan"  # defaults to repo

    card = cg.project_product_card(manifest, roles, tenant="FuzeInfraOps")
    assert card["supportedInterfaces"][0]["tenant"] == "FuzeInfraOps"
    # only the routing tenant changes; the card identity still names the repo
    assert card["name"] == "FuzePlan agent"


def test_product_capabilities_and_security(fuzeplan_repo):
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles)
    assert card["capabilities"] == {
        "streaming": True,
        "pushNotifications": False,
        "extendedAgentCard": True,
    }
    # in-cluster card declares both oidc and mtls
    assert set(card["securitySchemes"]) == {"fuze-oidc", "fuze-mtls"}
    assert card["securityRequirements"] == [{"fuze-oidc": []}]
    assert card["signatures"], "profile requires a non-empty signatures[]"


def test_product_skills_match_example_derived_fields(fuzeplan_repo, fuzeplan_example):
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles)

    got = {s["id"]: s for s in card["skills"]}
    want = {s["id"]: s for s in fuzeplan_example["skills"]}
    assert set(got) == set(want) == {"product-manager", "ux-designer"}

    for sid in want:
        assert got[sid]["name"] == want[sid]["name"]
        assert got[sid]["description"] == want[sid]["description"]
        assert got[sid].get("examples") == want[sid].get("examples")
        # tag SET equality (order is deterministic-sorted, not example order)
        assert set(got[sid]["tags"]) == set(want[sid]["tags"])
        # our tags are sorted deterministically
        assert got[sid]["tags"] == sorted(got[sid]["tags"])


def test_serving_roles_order_is_explicit(fuzeplan_repo):
    manifest, roles = load_repo(fuzeplan_repo)
    # servingRoles fixes the order
    card = cg.project_product_card(manifest, roles)
    assert [s["id"] for s in card["skills"]] == ["product-manager", "ux-designer"]

    # without servingRoles, order is lexicographic by role key
    m2 = {k: v for k, v in manifest.items() if k != "a2a"}
    card2 = cg.project_product_card(m2, roles)
    assert [s["id"] for s in card2["skills"]] == ["product-manager", "ux-designer"]


# --------------------------------------------------------------------------- #
# exec projection (FuzeInfra cto)
# --------------------------------------------------------------------------- #
def test_exec_card_validates(fuzeinfra_repo):
    manifest, roles = load_repo(fuzeinfra_repo)
    card = cg.project_exec_card("cto", roles["cto"], manifest)
    assert card_errors(card) == []
    FuzeA2AAgentCard.model_validate(card)


def test_exec_card_identity_tenant_and_external(fuzeinfra_repo):
    manifest, roles = load_repo(fuzeinfra_repo)
    card = cg.project_exec_card("cto", roles["cto"], manifest)

    assert card["name"] == "FuzeOne CTO agent"
    assert card["supportedInterfaces"][0]["tenant"] == "Exec-cto"
    # exec is never external -> in-cluster url
    assert card["supportedInterfaces"][0]["url"] == cg.IN_CLUSTER_URL


def test_exec_skill_tags_and_scopes(fuzeinfra_repo, exec_cto_example):
    manifest, roles = load_repo(fuzeinfra_repo)
    card = cg.project_exec_card("cto", roles["cto"], manifest)
    skill = card["skills"][0]
    want = exec_cto_example["skills"][0]

    assert skill["id"] == "cto"
    assert skill["name"] == want["name"]
    # exec tag set: role key, exec tier, executive, services, a2a.tags
    assert set(skill["tags"]) == set(want["tags"])
    assert "executive" in skill["tags"] and "exec" in skill["tags"] and "cto" in skill["tags"]
    assert skill["securityRequirements"] == [{"fuze-oidc": ["a2a.exec.escalate"]}]


def test_generate_cards_yields_exec_card_for_exec_role(fuzeinfra_repo):
    manifest, roles = load_repo(fuzeinfra_repo)
    cards = cg.generate_cards(manifest, roles)
    tenants = [t for t, _ in cards]
    # FuzeInfra fixture has only the exec cto role -> one exec card, no product card
    assert tenants == ["Exec-cto"]


# --------------------------------------------------------------------------- #
# invariants and failure modes
# --------------------------------------------------------------------------- #
def test_determinism_byte_identical(fuzeplan_repo):
    manifest, roles = load_repo(fuzeplan_repo)
    a = json.dumps(cg.project_product_card(manifest, roles), sort_keys=True)
    b = json.dumps(cg.project_product_card(manifest, roles), sort_keys=True)
    assert a == b


def test_missing_description_fails_loudly():
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product", "a2a": {"servingRoles": ["r"]}}
    roles = {"r": {"role": "r", "name": "FuzeX r"}}  # no description
    with pytest.raises(cg.CardProjectionError):
        cg.project_product_card(manifest, roles)


def test_base_and_coordinator_roles_excluded():
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product"}
    roles = {
        "_base": {"role": "_base", "name": "base", "description": "d"},
        "coord": {"role": "coord", "name": "c", "description": "d", "coordinator": True},
        "worker": {"role": "worker", "name": "FuzeX worker", "description": "does work"},
    }
    serving = cg.select_serving_roles(manifest, roles)
    assert serving == ["worker"]


def test_publish_false_hidden_from_public_shown_on_extended():
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product"}
    roles = {
        "open": {"role": "open", "name": "FuzeX open", "description": "d"},
        "secret": {
            "role": "secret",
            "name": "FuzeX secret",
            "description": "d",
            "a2a": {"publish": False},
        },
    }
    assert cg.select_serving_roles(manifest, roles, visibility="public") == ["open"]
    assert cg.select_serving_roles(manifest, roles, visibility="extended") == ["open", "secret"]


# --------------------------------------------------------------------------- #
# in-cluster endpoint — the per-product-pod blocker
# (card-projection.md §2 / values-interface `a2a.inClusterUrl`, contract v1.2.0)
# --------------------------------------------------------------------------- #
#: What a per-product pod's own Service looks like: one A2A deployment per product, in
#: that product's namespace, instead of a tenant row on the shared server.
PER_PRODUCT_URL = "http://a2a-fuzeplan.fuzeplan.svc.cluster.local:8080/rpc"


def test_in_cluster_url_defaults_to_the_shared_server(fuzeplan_repo):
    """Unset -> the SHARED server's address, exactly as before v1.2.0.

    This is the no-regression guarantee for the live `a2a-shared` deployment (FuzeAgent,
    FuzeFront, FuzePlan): an unchanged values file leaves `inClusterUrl` unset, so nothing
    about its cards moves.
    """
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles)
    assert card["supportedInterfaces"][0]["url"] == cg.DEFAULT_IN_CLUSTER_URL
    assert cg.DEFAULT_IN_CLUSTER_URL == "http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc"
    # the pre-v1.2.0 name still resolves for anything that imported it
    assert cg.IN_CLUSTER_URL == cg.DEFAULT_IN_CLUSTER_URL
    # passing None explicitly is the same "not declared" signal
    assert cg.project_product_card(manifest, roles, in_cluster_url=None) == card


def test_product_card_advertises_the_configured_in_cluster_url(fuzeplan_repo):
    """A per-product pod's card must name ITS OWN endpoint.

    The regression this guards is precisely why every product's A2A pod shipped disabled:
    the URL was a module constant, so a per-product pod would start, pass its probes, and
    publish `a2a-shared`'s address — callers following the card never reach it.
    """
    manifest, roles = load_repo(fuzeplan_repo)
    card = cg.project_product_card(manifest, roles, in_cluster_url=PER_PRODUCT_URL)

    iface = card["supportedInterfaces"][0]
    assert iface["url"] == PER_PRODUCT_URL
    # nothing anywhere in the card still points at the shared server
    assert cg.DEFAULT_IN_CLUSTER_URL not in json.dumps(card)
    # ONLY the endpoint moves — routing key, binding and skills are untouched
    assert iface["tenant"] == "FuzePlan"
    assert iface["protocolBinding"] == "JSONRPC"
    assert [s["id"] for s in card["skills"]] == ["product-manager", "ux-designer"]
    # and the card is still schema + profile valid at its new address
    assert card_errors(card) == []


def test_exec_card_advertises_the_configured_in_cluster_url(fuzeinfra_repo):
    """Exec cards are in-cluster ONLY, so a pod serving one must move its URL too."""
    manifest, roles = load_repo(fuzeinfra_repo)
    url = "http://a2a-fuzeinfra.fuzeinfra.svc.cluster.local:8080/rpc"

    default = cg.project_exec_card("cto", roles["cto"], manifest)
    assert default["supportedInterfaces"][0]["url"] == cg.DEFAULT_IN_CLUSTER_URL

    card = cg.project_exec_card("cto", roles["cto"], manifest, in_cluster_url=url)
    assert card["supportedInterfaces"][0]["url"] == url
    assert card["supportedInterfaces"][0]["tenant"] == "Exec-cto"
    assert card_errors(card) == []


def test_generate_cards_threads_in_cluster_url_to_every_card():
    """One pod serves them all, so every card it emits carries that pod's endpoint."""
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product"}
    roles = {
        "worker": {"role": "worker", "name": "FuzeX worker", "description": "does work"},
        "cto": {
            "role": "cto",
            "name": "FuzeOne CTO",
            "description": "decides",
            "metadata": {"tier": "executive"},
        },
    }
    url = "http://a2a-fuzex.fuzex.svc.cluster.local:8080/rpc"
    cards = dict(cg.generate_cards(manifest, roles, in_cluster_url=url))
    assert set(cards) == {"FuzeX", "Exec-cto"}
    for tenant, card in cards.items():
        assert card["supportedInterfaces"][0]["url"] == url, tenant


def test_external_tenant_ignores_in_cluster_url():
    """`external: true` publishes through the tunnel; the in-cluster value must not leak."""
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product", "a2a": {"external": True}}
    roles = {"worker": {"role": "worker", "name": "FuzeX worker", "description": "d"}}
    card = cg.project_product_card(manifest, roles, in_cluster_url=PER_PRODUCT_URL)
    assert card["supportedInterfaces"][0]["url"] == "https://a2a.fuzex.prod.fuzefront.com/rpc"


def test_in_cluster_url_keeps_the_projection_deterministic(fuzeplan_repo):
    """Same inputs -> byte-identical card. The new input is DECLARED, never sniffed."""
    manifest, roles = load_repo(fuzeplan_repo)
    a = json.dumps(cg.project_product_card(manifest, roles, in_cluster_url=PER_PRODUCT_URL))
    b = json.dumps(cg.project_product_card(manifest, roles, in_cluster_url=PER_PRODUCT_URL))
    assert a == b


def test_external_card_uses_https_url_and_no_mtls():
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product", "a2a": {"external": True}}
    roles = {"worker": {"role": "worker", "name": "FuzeX worker", "description": "d"}}
    card = cg.project_product_card(manifest, roles)
    url = card["supportedInterfaces"][0]["url"]
    assert url.startswith("https://a2a.fuzex.prod.fuzefront.com/rpc")
    assert "fuze-mtls" not in card["securitySchemes"]


def test_signing_placeholder_and_injected_signer():
    manifest = {"repo": "izzywdev/FuzeX", "tier": "product"}
    roles = {"worker": {"role": "worker", "name": "FuzeX worker", "description": "d"}}

    default = cg.project_product_card(manifest, roles)
    assert default["signatures"] == [cg._PLACEHOLDER_SIGNATURE]

    seen = {}

    def signer(payload: bytes) -> dict:
        seen["payload"] = payload
        return {"protected": "hdr", "signature": "sig"}

    signed = cg.project_product_card(manifest, roles, signer=signer)
    assert signed["signatures"] == [{"protected": "hdr", "signature": "sig"}]
    # signer received canonical bytes that EXCLUDE signatures
    assert b"signatures" not in seen["payload"]


def test_canonicalize_excludes_signatures_and_is_stable():
    card = {"b": 1, "a": 2, "signatures": [{"x": 1}]}
    out = cg.canonicalize(card)
    assert out == b'{"a":2,"b":1}'
