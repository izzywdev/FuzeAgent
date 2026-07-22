"""Shared test fixtures.

Adds the ``agent-templates`` directory to ``sys.path`` so ``import a2a...`` and the
contract client package resolve without an editable install, mirroring how the server
process is launched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_A2A_PKG = Path(__file__).resolve().parents[1]  # .../agent-templates/a2a
_AGENT_TEMPLATES = _A2A_PKG.parent  # .../agent-templates
for p in (str(_AGENT_TEMPLATES),):
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = _A2A_PKG / "tests" / "fixtures"
CONTRACT = _AGENT_TEMPLATES / "contracts" / "a2a" / "v1"
EXAMPLES = CONTRACT / "examples"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def fuzeplan_repo() -> Path:
    return FIXTURES / "fuzeplan"


@pytest.fixture
def fuzeinfra_repo() -> Path:
    return FIXTURES / "fuzeinfra"


@pytest.fixture
def fuzeplan_example() -> dict:
    return _read_json(EXAMPLES / "fuzeplan.agent-card.json")


@pytest.fixture
def exec_cto_example() -> dict:
    return _read_json(EXAMPLES / "exec-cto.agent-card.json")
