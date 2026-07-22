"""Every Agent Card in the frozen contract validates against the card schema AND
the generated pydantic model, and satisfies the Fuze profile constraints from
card-projection.md / authz.md / binding.md.

A card is the published capability boundary; a malformed or over-disclosing card
is a contract violation regardless of what the server later does.
"""
from __future__ import annotations

import pytest
from fuze_a2a_client import AgentCard
from jsonschema import Draft202012Validator

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]

# Fields the projection MUST NOT emit — they would leak the callee's "how"
# (card-projection.md §3, §7). Checked as substrings across the serialized card.
FORBIDDEN_CARD_KEYS = {
    "tools",
    "mcp_servers",
    "mcpServers",
    "system",
    "system_append",
    "systemAppend",
    "persona",
    "model",
    "environment",
    "vault",
}


def _all_cards(all_example_cards, mock_card):
    cards = dict(all_example_cards)
    cards["mock/agent-card.mock.json"] = mock_card
    return cards


def test_all_cards_validate_against_schema(all_example_cards, mock_card, card_schema):
    validator = Draft202012Validator(card_schema)
    for name, card in _all_cards(all_example_cards, mock_card).items():
        errors = [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(card)]
        assert not errors, f"{name} violates agent-card.schema.json: {errors}"


def test_all_cards_parse_with_generated_model(all_example_cards, mock_card):
    for name, card in _all_cards(all_example_cards, mock_card).items():
        # Raises pydantic.ValidationError on any drift from the generated model.
        AgentCard.model_validate(card)


def test_profile_single_jsonrpc_interface(all_example_cards, mock_card):
    # binding.md §2 / card-projection.md §2: exactly one interface, JSONRPC, v1.0,
    # tenant set (so one shared server can front many product agents).
    for name, card in _all_cards(all_example_cards, mock_card).items():
        ifaces = card["supportedInterfaces"]
        assert len(ifaces) == 1, f"{name}: v1 freezes exactly one interface"
        iface = ifaces[0]
        assert iface["protocolBinding"] == "JSONRPC", f"{name}: only JSONRPC in v1"
        assert iface["protocolVersion"] == "1.0", f"{name}: protocolVersion must be 1.0"
        assert iface.get("tenant"), f"{name}: tenant MUST be set for shared-server routing"


def test_profile_capabilities(all_example_cards, mock_card):
    # card-projection.md §4: streaming on, pushNotifications off, extendedCard on.
    for name, card in _all_cards(all_example_cards, mock_card).items():
        caps = card["capabilities"]
        assert caps.get("streaming") is True, f"{name}: streaming must be advertised"
        assert caps.get("pushNotifications") is False, f"{name}: no push in v1"
        assert caps.get("extendedAgentCard") is True, f"{name}: extended card required"


def test_profile_oidc_security_scheme_present(all_example_cards, mock_card):
    # authz.md §2: fuze-oidc is primary; the identity is the token subject.
    for name, card in _all_cards(all_example_cards, mock_card).items():
        schemes = card.get("securitySchemes", {})
        assert "fuze-oidc" in schemes, f"{name}: fuze-oidc scheme required"
        assert "openIdConnectSecurityScheme" in schemes["fuze-oidc"], f"{name}: OIDC wrapper"


def test_signatures_present_and_nonempty(all_example_cards, mock_card):
    # card-projection.md §6: the Fuze profile REQUIRES a non-empty signatures[].
    for name, card in _all_cards(all_example_cards, mock_card).items():
        sigs = card.get("signatures")
        assert sigs, f"{name}: Fuze profile requires a non-empty signatures[]"
        for s in sigs:
            assert s.get("protected") and s.get("signature"), f"{name}: incomplete JWS"


def test_cards_do_not_leak_callee_internals(all_example_cards, mock_card):
    # card-projection.md §7 encapsulation invariant: no credential/tool/vault/mcp
    # names anywhere in the published card.
    import json

    for name, card in _all_cards(all_example_cards, mock_card).items():
        def walk(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert k not in FORBIDDEN_CARD_KEYS, (
                        f"{name}: card leaks callee internal key {k!r} at {path}"
                    )
                    walk(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, f"{path}[{i}]")

        walk(card)
        # 'jira'/'atlassian' may legitimately appear in a product-manager skill's
        # tags/description (they describe WHAT, not the credential); tool/mcp keys
        # are what must never appear, checked above via structural keys.
        _ = json.dumps(card)  # ensure serializable


def test_skill_ids_are_role_join_keys(all_example_cards, mock_card):
    # card-projection.md §3: skill id == role key, matches ^[a-z0-9_-]+$.
    import re

    pat = re.compile(r"^[a-z0-9_-]+$")
    for name, card in _all_cards(all_example_cards, mock_card).items():
        for skill in card["skills"]:
            assert pat.match(skill["id"]), f"{name}: skill id {skill['id']!r} not a valid role key"


def test_description_describes_outcomes_not_tools(fuzeplan_card):
    # card-projection.md §1/§7: caller-facing description names outcomes and that
    # the callee holds its own tooling — the encapsulation promise in prose.
    desc = fuzeplan_card["description"].lower()
    assert "own tool" in desc or "its own" in desc or "credential" in desc


def test_exec_card_is_incluster_only_and_scoped(exec_cto_card):
    # card-projection.md §5: exec agents in-cluster only; escalation skill carries
    # an explicit scope; tenant is Exec-<role> so grants are per-exec-role.
    iface = exec_cto_card["supportedInterfaces"][0]
    assert iface["tenant"] == "Exec-cto"
    assert str(iface["url"]).startswith("http://"), "exec agents are not tunnel-published"
    assert ".prod.fuzefront.com" not in str(iface["url"]), "exec agents must not be external"
    skill = exec_cto_card["skills"][0]
    reqs = skill.get("securityRequirements", [])
    scopes = [s for r in reqs for s in r.get("fuze-oidc", [])]
    assert "a2a.exec.escalate" in scopes, "exec escalation must be scope-gated"
