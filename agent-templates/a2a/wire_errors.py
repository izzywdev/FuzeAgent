"""Building JSON-RPC error objects from the frozen A2A error taxonomy.

The typed exception hierarchy lives in the frozen client package
(``fuze_a2a_client.errors``) and is imported through ``._contract`` — never
redefined here. This module only adds the *server-side* helpers: turning an
``A2AError`` into the on-the-wire ``{"code","message","data"}`` object, where
``data`` is an ARRAY whose elements carry a ProtoJSON ``@type`` (binding.md §3).
"""

from __future__ import annotations

from typing import Any

from ._contract import errors

# Re-export for callers that dispatch on the typed classes.
A2AError = errors.A2AError
JSONParseError = errors.JSONParseError
InvalidRequestError = errors.InvalidRequestError
MethodNotFoundError = errors.MethodNotFoundError
InvalidParamsError = errors.InvalidParamsError
InternalError = errors.InternalError
TaskNotFoundError = errors.TaskNotFoundError
TaskNotCancelableError = errors.TaskNotCancelableError
PushNotificationNotSupportedError = errors.PushNotificationNotSupportedError
UnsupportedOperationError = errors.UnsupportedOperationError
ContentTypeNotSupportedError = errors.ContentTypeNotSupportedError
InvalidAgentResponseError = errors.InvalidAgentResponseError
VersionNotSupportedError = errors.VersionNotSupportedError

ERROR_DOMAIN = "a2a-protocol.org"
_ERROR_INFO_TYPE = "type.googleapis.com/google.rpc.ErrorInfo"


def error_info(reason: str, metadata: dict[str, Any] | None = None) -> dict:
    """One ProtoJSON ``google.rpc.ErrorInfo`` element for the ``data`` array."""
    el: dict[str, Any] = {"@type": _ERROR_INFO_TYPE, "reason": reason, "domain": ERROR_DOMAIN}
    if metadata:
        el["metadata"] = metadata
    return el


def to_wire_error(exc: A2AError) -> dict:
    """Serialize an ``A2AError`` to a JSON-RPC ``error`` object."""
    data = list(exc.data) if getattr(exc, "data", None) else []
    err: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if data:
        err["data"] = data
    return err


def with_info(exc_cls, message: str, reason: str, metadata: dict[str, Any] | None = None):
    """Construct an ``A2AError`` subclass carrying a single ``ErrorInfo`` element."""
    return exc_cls(message, data=[error_info(reason, metadata)])


# Convenience factories for the non-disclosure denial path (authz.md §6): all four
# denial cases MUST look identical on the wire.
def task_not_found() -> TaskNotFoundError:
    return with_info(
        TaskNotFoundError,
        "Task not found",
        "TASK_NOT_FOUND",
        {"note": "Returned identically for unknown, forbidden and other-caller tasks."},
    )


def push_not_supported() -> PushNotificationNotSupportedError:
    return with_info(
        PushNotificationNotSupportedError,
        "Push notifications are not supported",
        "PUSH_NOTIFICATION_NOT_SUPPORTED",
        {"contractVersion": "1.0.0"},
    )


def version_not_supported(seen: str | None = None) -> VersionNotSupportedError:
    md = {"supported": "1.0"}
    if seen is not None:
        md["seen"] = seen
    return with_info(
        VersionNotSupportedError, "A2A protocol version not supported", "VERSION_NOT_SUPPORTED", md
    )
