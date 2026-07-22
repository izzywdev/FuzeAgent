"""Test harness helpers: a mock transport for the frozen client and a
JSON-Schema validator bound to a specific ``$def`` of the wire schema.

None of this reads the server implementation. The MockTransport replays the
frozen ``mock/responses.mock.json`` fixtures so the caller-side client and the
contract shapes can be exercised before a live server exists (mock/README.md).
"""
from __future__ import annotations

from typing import Any, Callable

from jsonschema import Draft202012Validator


# --- schema validation ------------------------------------------------------
def validator_for(root_schema: dict, def_name: str) -> Draft202012Validator:
    """Return a validator anchored at ``#/$defs/<def_name>`` of ``root_schema``,
    with the whole schema available for ``$ref`` resolution."""
    sub = {"$ref": f"#/$defs/{def_name}", "$defs": root_schema["$defs"]}
    # carry $schema/$id so the resolver keeps the same base URI
    if "$id" in root_schema:
        sub["$id"] = root_schema["$id"]
    return Draft202012Validator(sub)


def errors_for(root_schema: dict, def_name: str, instance: Any) -> list[str]:
    v = validator_for(root_schema, def_name)
    return [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(instance)]


# --- mock transport ---------------------------------------------------------
class _MockResponse:
    def __init__(self, payload: Any):
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _MockStream:
    def __init__(self, lines: list[str]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_lines(self):
        yield from self._lines


class MockTransport:
    """Implements the client's ``Transport`` protocol against frozen fixtures.

    ``responses`` maps a JSON-RPC method name to either a full JSON-RPC envelope
    (dict) or a callable ``(envelope) -> envelope`` so a test can branch on the
    request. ``card`` is served for the well-known GET. ``stream_lines`` are the
    raw SSE lines yielded for streaming calls.

    Every request is captured in ``self.sent`` for assertion.
    """

    def __init__(
        self,
        *,
        responses: dict[str, Any] | None = None,
        card: dict | None = None,
        stream_lines: list[str] | None = None,
    ):
        self.responses = responses or {}
        self.card = card
        self.stream_lines = stream_lines or []
        self.sent: list[dict] = []

    def _record(self, verb: str, url: str, envelope: dict | None, headers: dict) -> None:
        self.sent.append(
            {"verb": verb, "url": url, "envelope": envelope, "headers": headers}
        )

    def _resolve(self, envelope: dict) -> Any:
        method = envelope.get("method")
        if method not in self.responses:
            raise AssertionError(
                f"MockTransport has no fixture for method {method!r}; "
                f"configured: {sorted(self.responses)}"
            )
        payload = self.responses[method]
        if callable(payload):
            payload = payload(envelope)
        return payload

    # -- Transport protocol --
    def post(self, url: str, *, json: dict, headers: dict) -> _MockResponse:  # noqa: A002
        self._record("POST", url, json, headers)
        return _MockResponse(self._resolve(json))

    def get(self, url: str, *, headers: dict) -> _MockResponse:
        self._record("GET", url, None, headers)
        return _MockResponse(self.card)

    def stream(self, method: str, url: str, *, json: dict, headers: dict):  # noqa: A002
        self._record(method, url, json, headers)
        return _MockStream(self.stream_lines)


def sse(frame: dict) -> str:
    """Serialize one JSON-RPC result frame as an SSE ``data:`` line."""
    import json as _json

    return "data: " + _json.dumps(frame)


def single_method_responses(method: str, envelope: dict) -> dict[str, Callable]:
    """Helper: a responses map returning ``envelope`` for exactly one method."""
    return {method: envelope}
