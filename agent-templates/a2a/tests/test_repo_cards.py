"""Project THIS repo's real roles (not a fixture) and assert the card is valid.

The other card-generator tests use fixture repos. This one guards the actual
`agent-templates/roles/` set that ships in FuzeAgent, so adding/removing a serving
role (or breaking role-manifest.schema.json) fails CI here — the reason a2a-unit's
path filter now also watches `agent-templates/roles/**` and the role schema.
"""
from __future__ import annotations

from pathlib import Path

from a2a import card_generator as cg
from a2a.loader import load_repo
from a2a.validation import card_errors

# tests/ -> a2a/ -> agent-templates/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


def _fuzeagent_card() -> dict:
    manifest, roles = load_repo(REPO_ROOT)
    # default sign=True — the fuze-profile schema requires a `signatures` field
    # (keyless signing in tests still populates it, matching the other card tests).
    cards = dict(cg.generate_cards(manifest, roles))
    assert "FuzeAgent" in cards, f"expected a FuzeAgent product card, got tenants {list(cards)}"
    return cards["FuzeAgent"]


def test_fuzeagent_real_roles_project_a_schema_valid_card():
    card = _fuzeagent_card()
    assert not card_errors(card), card_errors(card)


def test_agent_orchestrator_serving_role_is_projected():
    card = _fuzeagent_card()
    skills = {s["id"]: s for s in card["skills"]}
    # the serving role must appear; _base must never be projected
    assert "agent-orchestrator" in skills, f"skills: {sorted(skills)}"
    assert "_base" not in skills
    orch = skills["agent-orchestrator"]
    assert orch["description"], "an undescribed skill is unroutable"
    assert orch.get("examples"), "serving role should publish a2a.examples for discoverability"
