"""A2A error taxonomy for the JSON-RPC binding.

Codes are frozen from A2A spec 1.0.0 §5.4 (Error Code Mappings) and §9.5.
See ../../binding.md §3.
"""
from __future__ import annotations


class A2AError(Exception):
    """Base for every error surfaced over the A2A wire."""

    code: int = -32603

    def __init__(self, message: str, data: list | None = None, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.data = data or []
        if code is not None:
            self.code = code


# --- standard JSON-RPC ------------------------------------------------------
class JSONParseError(A2AError):
    code = -32700


class InvalidRequestError(A2AError):
    code = -32600


class MethodNotFoundError(A2AError):
    code = -32601


class InvalidParamsError(A2AError):
    code = -32602


class InternalError(A2AError):
    code = -32603


# --- A2A-specific -----------------------------------------------------------
class TaskNotFoundError(A2AError):
    """Also returned for tasks/tenants the caller may not see — the ambiguity is
    deliberate and required (authz.md §6)."""

    code = -32001


class TaskNotCancelableError(A2AError):
    code = -32002


class PushNotificationNotSupportedError(A2AError):
    """Always returned by Fuze v1 for push-notification config methods."""

    code = -32003


class UnsupportedOperationError(A2AError):
    code = -32004


class ContentTypeNotSupportedError(A2AError):
    code = -32005


class InvalidAgentResponseError(A2AError):
    code = -32006


class ExtendedAgentCardNotConfiguredError(A2AError):
    code = -32007


class ExtensionSupportRequiredError(A2AError):
    code = -32008


class VersionNotSupportedError(A2AError):
    code = -32009


_BY_CODE: dict[int, type[A2AError]] = {
    c.code: c
    for c in (
        JSONParseError,
        InvalidRequestError,
        MethodNotFoundError,
        InvalidParamsError,
        InternalError,
        TaskNotFoundError,
        TaskNotCancelableError,
        PushNotificationNotSupportedError,
        UnsupportedOperationError,
        ContentTypeNotSupportedError,
        InvalidAgentResponseError,
        ExtendedAgentCardNotConfiguredError,
        ExtensionSupportRequiredError,
        VersionNotSupportedError,
    )
}


def from_json_rpc_error(err: dict) -> A2AError:
    """Map a JSON-RPC `error` object onto the typed exception hierarchy."""
    code = err.get("code", -32603)
    cls = _BY_CODE.get(code, A2AError)
    return cls(err.get("message", "unknown A2A error"), err.get("data"), code=code)
