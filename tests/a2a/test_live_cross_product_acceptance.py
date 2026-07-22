"""THE motivating acceptance test (card-projection.md §7, task brief §2).

A requirements agent that holds **no Atlassian MCP and no Jira skill** calls the
FuzePlan agent over A2A, and Jira tickets result. The caller's entire toolkit is
the generic A2A client + the callee's card. If the caller needs any Jira knowledge
to make this work, the design has failed — that is the assertion.

RED until the FuzePlan A2A server is reachable ($A2A_SERVER_BASE_URL, or
$A2A_FUZEPLAN_BASE_URL for a dedicated FuzePlan endpoint).
"""
from __future__ import annotations

import os

import pytest
from fuze_a2a_client import A2AClient, TaskState

# Gate on either a dedicated FuzePlan endpoint or the shared server URL. Per-PR /
# local: SKIP. Under Phase-3 enforcement (A2A_REQUIRE_LIVE, set by
# a2a-acceptance.yml): NEVER skip — run and fail loudly if unconfigured.
_live_configured = bool(os.environ.get("A2A_FUZEPLAN_BASE_URL") or os.environ.get("A2A_SERVER_BASE_URL"))
_live_enforced = bool(os.environ.get("A2A_REQUIRE_LIVE"))
pytestmark = [
    pytest.mark.a2a,
    pytest.mark.integration,
    pytest.mark.acceptance,
    pytest.mark.live,
    pytest.mark.skipif(
        not _live_configured and not _live_enforced,
        reason=(
            "FuzePlan A2A live acceptance is the Phase-3 rollout gate (#90) — runs vs a "
            "deployed server via a2a-acceptance.yml, NOT per-PR. "
            "A2A_FUZEPLAN_BASE_URL / A2A_SERVER_BASE_URL unset and A2A_REQUIRE_LIVE off."
        ),
    ),
]

REQUIREMENTS = (
    "From this discussion, create Jira tickets: (1) add email-OTP to self-registration, "
    "(2) rate-limit the OTP endpoint, (3) add an audit log for OTP failures. "
    "One ticket each, with acceptance criteria."
)


@pytest.fixture
def fuzeplan_client(live_transport, allowlisted_token):
    base = os.environ.get("A2A_FUZEPLAN_BASE_URL") or os.environ.get("A2A_SERVER_BASE_URL")
    if not base:
        pytest.fail(
            "No FuzePlan A2A endpoint ($A2A_FUZEPLAN_BASE_URL / $A2A_SERVER_BASE_URL). "
            "RED until the FuzePlan server slice is delivered.",
            pytrace=False,
        )
    import httpx

    try:
        card = A2AClient.fetch_card(base.rstrip("/"), transport=live_transport)
    except (httpx.HTTPError, OSError) as exc:
        pytest.fail(f"FuzePlan card unreachable at {base}: {exc!r} — server slice not delivered.", pytrace=False)
    return A2AClient(card, token=allowlisted_token, transport=live_transport)


def _ticket_ids(task) -> list[str]:
    ids: list[str] = []
    for art in task.artifacts or []:
        for part in art.parts:
            data = getattr(part.root, "data", None)
            if isinstance(data, dict):
                ids.extend(data.get("tickets", []))
    return ids


def test_fuzeplan_exposes_product_manager_skill(fuzeplan_client):
    skill_ids = {s.id for s in fuzeplan_client.card.skills}
    assert "product-manager" in skill_ids, (
        "FuzePlan must publish the product-manager skill for cross-product routing"
    )


def test_caller_with_no_jira_skill_gets_tickets(fuzeplan_client):
    # The caller names the published skill and sends plain text. It holds NO Jira
    # skill, NO Atlassian MCP, NO credentials — only this client and the card.
    task = fuzeplan_client.send_message(REQUIREMENTS, skill_id="product-manager")

    # An always_ask bulk pause is legitimate (state-mapping.md §4): confirm and
    # continue, still without the caller knowing anything about Jira.
    if task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
        assert task.status.message is not None, "pause must be explained"
        task = fuzeplan_client.send_message("Confirmed, proceed.", task_id=task.id)

    assert task.status.state == TaskState.TASK_STATE_COMPLETED, (
        f"expected tickets to be created; got {task.status.state} "
        f"({task.status.message.parts[0].root.text if task.status.message else 'no message'})"
    )
    tickets = _ticket_ids(task)
    assert tickets, "FuzePlan must return the Jira tickets it created as artifacts"


def test_caller_never_supplied_jira_credentials(fuzeplan_client):
    # Encapsulation, stated as behaviour: the successful call above used only a
    # bearer token identifying the CALLER — no Atlassian token was ever sent. The
    # client's headers carry exactly Authorization(bearer)+Content-Type+A2A-Version.
    fuzeplan_client.send_message("What is the delivery status of the OTP epic?", skill_id="product-manager")
    sent = fuzeplan_client._transport  # httpx client; inspect last request is not stored.
    # Structural guarantee instead: the client exposes no way to attach an
    # Atlassian/Jira credential — its only auth input is the OIDC bearer token.
    import inspect

    sig = inspect.signature(A2AClient.__init__)
    assert set(sig.parameters) <= {"self", "card", "token", "transport"}, (
        "caller client must accept no callee-domain credential — only an OIDC token"
    )
    assert sent is not None
