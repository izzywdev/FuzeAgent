"""Shared fixtures for the INDEPENDENT A2A contract/acceptance suite.

This suite is authored by the test-engineer against the FROZEN contract at
``agent-templates/contracts/a2a/v1``. It never reads the server implementation
(``agent-templates/a2a/``) to shape assertions — it grades the server against the
spec, blind to how the spec was built.

Two tiers of test live here:

* ``conformance`` — static checks against the frozen artifacts (schemas, example
  cards, mock fixtures, generated client). These should be GREEN now, because the
  contract is frozen and merged.
* ``integration`` — behavioural checks against a LIVE A2A server, gated on the
  ``A2A_SERVER_BASE_URL`` env var. These are EXPECTED TO BE RED until the
  backend-engineer's server slice lands. A red integration test against a genuine
  gap is a valid deliverable, not a failure of this suite.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# --- locate the frozen contract tree ---------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "agent-templates" / "contracts" / "a2a" / "v1"
SCHEMA_DIR = CONTRACT_ROOT / "schema"
MOCK_DIR = CONTRACT_ROOT / "mock"
EXAMPLES_DIR = CONTRACT_ROOT / "examples"
CLIENT_DIR = CONTRACT_ROOT / "client"

# Make the FROZEN generated client importable as the caller-side harness.
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))


def _load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# --- path fixtures ----------------------------------------------------------
@pytest.fixture(scope="session")
def contract_root() -> Path:
    return CONTRACT_ROOT


@pytest.fixture(scope="session")
def wire_schema() -> dict:
    return _load_json(SCHEMA_DIR / "a2a-wire.schema.json")


@pytest.fixture(scope="session")
def card_schema() -> dict:
    return _load_json(SCHEMA_DIR / "agent-card.schema.json")


@pytest.fixture(scope="session")
def mock_responses() -> dict:
    return _load_json(MOCK_DIR / "responses.mock.json")


@pytest.fixture(scope="session")
def mock_card() -> dict:
    return _load_json(MOCK_DIR / "agent-card.mock.json")


@pytest.fixture(scope="session")
def fuzeplan_card() -> dict:
    return _load_json(EXAMPLES_DIR / "fuzeplan.agent-card.json")


@pytest.fixture(scope="session")
def exec_cto_card() -> dict:
    return _load_json(EXAMPLES_DIR / "exec-cto.agent-card.json")


@pytest.fixture(scope="session")
def all_example_cards() -> dict[str, dict]:
    return {p.name: _load_json(p) for p in sorted(EXAMPLES_DIR.glob("*.json"))}


# --- live-server gate -------------------------------------------------------
# Integration tests require a real A2A server. Absent one, we FAIL rather than
# SKIP: a silent skip would let CI go green while the server slice is unbuilt,
# which is exactly the dishonesty this role exists to prevent.
LIVE_ENV = "A2A_SERVER_BASE_URL"


@pytest.fixture
def live_base_url() -> str:
    base = os.environ.get(LIVE_ENV)
    if not base:
        pytest.fail(
            f"No live A2A server configured (${LIVE_ENV} unset). "
            "This integration test is RED because the server slice "
            "(backend-engineer, agent-templates/a2a/) is not yet delivered/reachable. "
            "This is the expected honest-grader signal, not a bug in the test.",
            pytrace=False,
        )
    return base.rstrip("/")


@pytest.fixture
def live_transport(live_base_url):  # noqa: ARG001 - forces the gate to evaluate
    """A real httpx transport for hitting a live server, with a bounded timeout so
    CI never hangs. Exec-escalation dwell is a server concern; the test harness
    still bounds its own socket wait."""
    import httpx

    return httpx.Client(timeout=float(os.environ.get("A2A_TEST_TIMEOUT", "30")))
