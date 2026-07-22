"""The error codes and their client-side mapping match binding.md §3 exactly, and
the frozen error fixtures raise the right typed exception through the client.
"""
from __future__ import annotations

import pytest
from fuze_a2a_client import (
    A2AClient,
    AgentCard,
    PushNotificationNotSupportedError,
    TaskNotFoundError,
    VersionNotSupportedError,
)
from fuze_a2a_client.errors import from_json_rpc_error

from _harness import MockTransport

pytestmark = [pytest.mark.a2a, pytest.mark.conformance]

# binding.md §3 table — the frozen code assignments.
EXPECTED_CODES = {
    "JSONParseError": -32700,
    "InvalidRequestError": -32600,
    "MethodNotFoundError": -32601,
    "InvalidParamsError": -32602,
    "InternalError": -32603,
    "TaskNotFoundError": -32001,
    "TaskNotCancelableError": -32002,
    "PushNotificationNotSupportedError": -32003,
    "UnsupportedOperationError": -32004,
    "ContentTypeNotSupportedError": -32005,
    "InvalidAgentResponseError": -32006,
    "ExtendedAgentCardNotConfiguredError": -32007,
    "ExtensionSupportRequiredError": -32008,
    "VersionNotSupportedError": -32009,
}


@pytest.mark.parametrize("clsname,code", EXPECTED_CODES.items())
def test_error_codes_frozen(clsname, code):
    import fuze_a2a_client.errors as errmod

    cls = getattr(errmod, clsname)
    assert cls.code == code, f"{clsname} code drifted from binding.md §3"


def test_from_json_rpc_error_maps_by_code():
    exc = from_json_rpc_error({"code": -32003, "message": "no push", "data": []})
    assert isinstance(exc, PushNotificationNotSupportedError)
    assert exc.code == -32003


def _raise_client(mock_card, error_fixture):
    c = A2AClient(
        AgentCard.model_validate(mock_card),
        token="t",
        transport=MockTransport(responses={"SendMessage": error_fixture}, card=mock_card),
    )
    return c


def test_push_not_supported_fixture_raises(mock_card, mock_responses):
    c = _raise_client(mock_card, mock_responses["error.pushNotSupported"])
    with pytest.raises(PushNotificationNotSupportedError) as ei:
        c.send_message("x", skill_id="product-manager")
    assert ei.value.code == -32003


def test_version_not_supported_fixture_raises(mock_card, mock_responses):
    c = _raise_client(mock_card, mock_responses["error.versionNotSupported"])
    with pytest.raises(VersionNotSupportedError) as ei:
        c.send_message("x", skill_id="product-manager")
    assert ei.value.code == -32009


def test_task_not_found_is_the_ambiguous_denial(mock_card, mock_responses):
    # authz.md §6: -32001 is returned identically for unknown / forbidden /
    # other-caller tasks so the error channel is not an enumeration oracle.
    c = _raise_client(mock_card, mock_responses["error.taskNotFound"])
    with pytest.raises(TaskNotFoundError) as ei:
        c.send_message("x", skill_id="product-manager")
    assert ei.value.code == -32001
    # Message must not disclose WHICH of the ambiguous causes applied.
    msg = str(ei.value).lower()
    for leak in ("forbidden", "not authorized", "other caller", "permission", "exists"):
        assert leak not in msg, f"taskNotFound message leaks cause: {leak!r}"


def test_push_notification_reason_domain(mock_responses):
    data = mock_responses["error.pushNotSupported"]["error"]["data"][0]
    assert data["reason"] == "PUSH_NOTIFICATION_NOT_SUPPORTED"
    assert data["domain"] == "a2a-protocol.org"
