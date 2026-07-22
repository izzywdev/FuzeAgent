"""Bridge to the FROZEN A2A contract client package.

The generated wire/card models and the typed error taxonomy live in
``agent-templates/contracts/a2a/v1/client/fuze_a2a_client`` and are the single
source of truth for the wire shapes. This module makes them importable whether or
not the client package has been ``pip install``ed, by putting its directory on
``sys.path`` on first import. Everything in this server imports the wire/card models
and errors THROUGH here so there is exactly one definition of the contract types.

We NEVER redefine the wire or card models — redefining a generated model is how a
server silently forks from its spec (see the client package docstring).
"""

from __future__ import annotations

import sys
from pathlib import Path

# .../agent-templates/a2a/_contract.py -> .../agent-templates
_AGENT_TEMPLATES = Path(__file__).resolve().parents[1]
_CONTRACT_ROOT = _AGENT_TEMPLATES / "contracts" / "a2a" / "v1"
_CLIENT_DIR = _CONTRACT_ROOT / "client"

if _CLIENT_DIR.exists() and str(_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CLIENT_DIR))

#: Absolute path to the frozen contract tree (schemas, examples, VERSION).
CONTRACT_ROOT = _CONTRACT_ROOT
SCHEMA_DIR = _CONTRACT_ROOT / "schema"
EXAMPLES_DIR = _CONTRACT_ROOT / "examples"

# Re-export the generated / frozen types. Imported lazily-safe: the client package
# only needs pydantic (always present here), never httpx, because we supply no
# transport (this is the server, not the client).
from fuze_a2a_client import errors as errors  # noqa: E402
from fuze_a2a_client.card_models import (  # noqa: E402
    AgentCapabilities,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    FuzeA2AAgentCard,
    SecurityRequirement,
)
from fuze_a2a_client.wire_models import (  # noqa: E402
    Artifact,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Method,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

__all__ = [
    "CONTRACT_ROOT",
    "SCHEMA_DIR",
    "EXAMPLES_DIR",
    "errors",
    "FuzeA2AAgentCard",
    "AgentInterface",
    "AgentProvider",
    "AgentSkill",
    "AgentCapabilities",
    "SecurityRequirement",
    "Artifact",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "Message",
    "Method",
    "Part",
    "Role",
    "Task",
    "TaskArtifactUpdateEvent",
    "TaskState",
    "TaskStatus",
    "TaskStatusUpdateEvent",
]
