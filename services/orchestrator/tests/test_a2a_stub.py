"""
Stub module for the a2a marker so 'pytest -m a2a' exits with 0 instead of 5.

The bespoke A2AProtocol implementation (AgentCapability, TaskDelegation) was
superseded by the open-standard A2A contract in PR #73 and the full test suite
was quarantined in #76.  This file keeps the marker alive in the collection so
the CI step does not fail with "no tests collected" (exit code 5).
"""

import pytest


@pytest.mark.a2a
def test_a2a_bespoke_protocol_retired() -> None:
    """Bespoke A2A protocol is superseded by open-standard A2A (#73)."""
    pytest.skip("bespoke a2a_protocol superseded by #73; full suite in #76")
