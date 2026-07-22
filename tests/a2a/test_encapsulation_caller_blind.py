"""The motivating cross-product invariant (card-projection.md §7), verified at the
CONTRACT level: a caller holding NO Atlassian MCP and NO Jira skill can drive the
FuzePlan product-manager skill using only the card + the generic client, and the
caller side carries zero Jira/Atlassian knowledge.

The live end-to-end version (real tickets from a real FuzePlan server) is
test_live_cross_product_acceptance.py; this file proves the design does not
require the caller to know anything about Jira. If it did, the design has failed.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fuze_a2a_client import A2AClient, AgentCard, TaskState

from _harness import MockTransport

pytestmark = [pytest.mark.a2a, pytest.mark.conformance, pytest.mark.acceptance]

# Vocabulary that would betray the callee's "how" leaking onto the caller side.
CALLEE_DOMAIN_TOKENS = ("atlassian", "jira", "mcp", "vault", "confluence")


def _client_source_files() -> list[Path]:
    import fuze_a2a_client

    pkg_dir = Path(fuze_a2a_client.__file__).resolve().parent
    return sorted(pkg_dir.glob("*.py"))


def test_caller_client_imports_no_callee_domain():
    # The generic caller SDK must not import or reference any Jira/Atlassian/MCP
    # machinery — the whole point is that the caller needs none of it.
    import ast

    for path in _client_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                low = m.lower()
                for tok in CALLEE_DOMAIN_TOKENS:
                    assert tok not in low, (
                        f"{path.name} imports callee-domain module {m!r} "
                        f"(token {tok!r}) — caller is no longer blind to the callee's how"
                    )


def test_caller_needs_only_card_and_goal(fuzeplan_card, mock_responses):
    # A requirements agent holds ONLY: the FuzePlan card + its goal text. No Jira
    # skill, no Atlassian credential. It selects the published skill by id and
    # sends a plain-text goal. That is the entire caller surface.
    card = AgentCard.model_validate(fuzeplan_card)
    # The caller can SEE the product-manager skill on the public card...
    skill_ids = {s.id for s in card.skills}
    assert "product-manager" in skill_ids
    # ...but the card gives it no Jira tool, credential or MCP handle to hold.
    transport = MockTransport(
        responses={"SendMessage": mock_responses["SendMessage.completed"]},
        card=fuzeplan_card,
    )
    client = A2AClient(card, token="requirements-agent-oidc", transport=transport)
    task = client.send_message(
        "Create Jira tickets for the requirements in this discussion.",
        skill_id="product-manager",
    )
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    # The Jira tickets come back as artifacts the caller did not have to create.
    ticket_ids = [
        t
        for art in (task.artifacts or [])
        for part in art.parts
        if getattr(part.root, "data", None)
        for t in (part.root.data or {}).get("tickets", [])
    ]
    assert ticket_ids, "callee must return the Jira tickets it created as artifacts"
    assert all(tid.startswith("FP-") for tid in ticket_ids)


def test_public_card_advertises_outcome_not_toolset(fuzeplan_card):
    # card-projection.md §7: a caller learns WHAT (tickets/sprints/status), never
    # the credentials or MCP servers behind it.
    pm = next(s for s in fuzeplan_card["skills"] if s["id"] == "product-manager")
    # 'jira' as a TAG/description describes the outcome domain and is allowed;
    # what must be absent is any tool/mcp/credential handle. The skill object has
    # no such fields by schema (additionalProperties:false) — assert the shape.
    allowed = {"id", "name", "description", "tags", "examples", "inputModes", "outputModes", "securityRequirements"}
    assert set(pm) <= allowed, f"skill leaks non-projected fields: {set(pm) - allowed}"
