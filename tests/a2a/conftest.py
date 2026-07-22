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
# Integration tests require a real A2A server. This is a live DEPENDENCY, so the
# tier is env-gated, not hard-failing:
#   * A2A_SERVER_BASE_URL UNSET  -> the whole live module SKIPs (Phase 3 gate not
#     yet wired). Each live_*.py declares `pytestmark = requires_live_server` so
#     the skip happens at collection with a clear reason. Skipping keeps main and
#     every PR green and avoids tripping claude-ci-autofix into weakening the
#     acceptance tests.
#   * A2A_SERVER_BASE_URL SET    -> the tests RUN FOR REAL and FAIL LOUDLY on any
#     deviation (no soft-pass, no swallowed errors). That is the Phase 3
#     rollout/CI-with-server context where the honest grade must bite.
# The conformance tier needs no server and always runs.
LIVE_ENV = "A2A_SERVER_BASE_URL"

_SKIP_REASON = (
    "A2A server not deployed in this environment (${var} unset) — this is the "
    "Phase 3 acceptance gate; set A2A_SERVER_BASE_URL (server deployed in CI/staging) "
    "to run and ENFORCE these live contract/acceptance/authZ tests."
)


def live_server_configured() -> bool:
    return bool(os.environ.get(LIVE_ENV))


# Reusable module-level marker for every live_*.py test file.
requires_live_server = pytest.mark.skipif(
    not live_server_configured(),
    reason=_SKIP_REASON.replace("${var}", LIVE_ENV),
)


@pytest.fixture
def live_base_url() -> str:
    base = os.environ.get(LIVE_ENV)
    if not base:
        # Defensive: reached only if a test forgot the module marker.
        pytest.skip(_SKIP_REASON.replace("${var}", LIVE_ENV))
    return base.rstrip("/")


@pytest.fixture
def live_transport(live_base_url):  # noqa: ARG001 - forces the gate to evaluate
    """A real httpx transport for hitting a live server, with a bounded timeout so
    CI never hangs. Exec-escalation dwell is a server concern; the test harness
    still bounds its own socket wait."""
    import httpx

    return httpx.Client(timeout=float(os.environ.get("A2A_TEST_TIMEOUT", "30")))


def _oidc_token(var: str, role: str) -> str:
    tok = os.environ.get(var)
    if not tok:
        pytest.fail(
            f"No OIDC token for the {role} caller (${var} unset). "
            "Cannot exercise the live authorization model without a real credential. "
            "RED until the server + test credentials are wired.",
            pytrace=False,
        )
    return tok


@pytest.fixture
def allowlisted_token() -> str:
    """OIDC token whose subject IS in the callee's providesTo (an allowed caller)."""
    return _oidc_token("A2A_TEST_OIDC_TOKEN", "allowlisted")


@pytest.fixture
def unauthorized_token() -> str:
    """OIDC token whose subject is NOT in the callee's providesTo. authz.md §3:
    absent-from-allowlist MUST be denied BY THE CALLEE, not merely un-routed."""
    return _oidc_token("A2A_TEST_UNAUTH_TOKEN", "unauthorized")


@pytest.fixture
def live_card(live_base_url, live_transport):
    """Fetch the public Agent Card from the live server, or FAIL red with a clear
    'server slice not delivered' message on any connection error."""
    import httpx
    from fuze_a2a_client import A2AClient

    try:
        return A2AClient.fetch_card(live_base_url, transport=live_transport)
    except (httpx.HTTPError, OSError) as exc:
        pytest.fail(
            f"Could not reach the A2A server at {live_base_url} "
            f"(GET /.well-known/agent-card.json): {exc!r}. "
            "RED because the server slice is not yet delivered/reachable.",
            pytrace=False,
        )


@pytest.fixture
def live_client(live_card, live_transport, allowlisted_token):
    from fuze_a2a_client import A2AClient

    return A2AClient(live_card, token=allowlisted_token, transport=live_transport)


@pytest.fixture
def live_raw(live_base_url, live_card, live_transport, allowlisted_token):
    """POST a raw JSON-RPC envelope to the live /rpc endpoint and return
    ``(http_status, parsed_body)``. Lets tests probe methods the typed client does
    not expose (e.g. push-notification methods) and malformed headers."""
    import uuid

    rpc_url = str(live_card.supportedInterfaces[0].url)

    def _post(method: str, params: dict, *, version: str = "1.0", token: str | None = ...):
        headers = {"Content-Type": "application/json", "A2A-Version": version}
        auth = allowlisted_token if token is ... else token
        if auth:
            headers["Authorization"] = f"Bearer {auth}"
        envelope = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        resp = live_transport.post(rpc_url, json=envelope, headers=headers)
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {}
        return resp.status_code, body

    return _post
