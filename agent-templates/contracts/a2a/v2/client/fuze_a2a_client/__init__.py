"""fuze-a2a-client — typed client for the Fuze A2A contract v1.

Frozen against A2A specification 1.0.0 (`lf.a2a.v1`).

`wire_models` and `card_models` are GENERATED from the schemas in ../../schema/ by
`regenerate.sh`; do not hand-edit them. Editing a generated model instead of the
schema is how a contract silently forks from its spec.
"""
from .card_models import FuzeA2AAgentCard as AgentCard
from .client import (
    A2A_VERSION,
    INTERRUPTED_STATES,
    TERMINAL_STATES,
    WELL_KNOWN_CARD_PATH,
    A2AClient,
)
from .errors import (
    A2AError,
    ContentTypeNotSupportedError,
    InvalidAgentResponseError,
    PushNotificationNotSupportedError,
    TaskNotCancelableError,
    TaskNotFoundError,
    UnsupportedOperationError,
    VersionNotSupportedError,
)
from .wire_models import Artifact, Message, Part, Role, Task, TaskState, TaskStatus

__version__ = "1.0.0"

__all__ = [
    "A2AClient",
    "AgentCard",
    "A2A_VERSION",
    "WELL_KNOWN_CARD_PATH",
    "TERMINAL_STATES",
    "INTERRUPTED_STATES",
    "Task",
    "TaskState",
    "TaskStatus",
    "Message",
    "Part",
    "Role",
    "Artifact",
    "A2AError",
    "TaskNotFoundError",
    "TaskNotCancelableError",
    "PushNotificationNotSupportedError",
    "UnsupportedOperationError",
    "ContentTypeNotSupportedError",
    "InvalidAgentResponseError",
    "VersionNotSupportedError",
]
