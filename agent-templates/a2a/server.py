"""HTTP + SSE transport for the shared A2A server (binding.md §1).

    JSON-RPC 2.0 over HTTP(S), with Server-Sent Events for streaming. Only that.

Routes:
    POST /rpc                              single endpoint, all methods (bare PascalCase)
    GET  /.well-known/agent-card.json      public card discovery (unauthenticated)
    GET  /extendedAgentCard                authenticated, per-caller card
    GET  /healthz                          liveness

This module owns transport concerns only — credential extraction, the JSON-RPC
envelope, SSE framing, the ``A2A-Version`` header and error serialization. All agent
behaviour lives in ``adapter`` (and below it, the provider seam).
"""

from __future__ import annotations

import json
from typing import Any, Iterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route

from . import wire_errors as we
from .adapter import A2AAdapter
from .authz import AuthContext
from .identity import Authenticator

A2A_VERSION = "1.0"
_VERSION_HEADER = "a2a-version"

# Methods that stream (SSE); everything else is a unary JSON response.
_STREAMING = {"SendStreamingMessage", "SubscribeToTask"}
# Push-notification config methods are OUT of v1 -> -32003 (binding.md §1).
_PUSH_METHODS = {
    "CreateTaskPushNotificationConfig",
    "GetTaskPushNotificationConfig",
    "ListTaskPushNotificationConfigs",
    "DeleteTaskPushNotificationConfig",
}


class A2AServer:
    def __init__(self, adapter: A2AAdapter, authenticator: Authenticator):
        self.adapter = adapter
        self.auth = authenticator

    # -- envelope helpers ---------------------------------------------------
    @staticmethod
    def _ok(req_id, result) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _err(req_id, exc: we.A2AError) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": we.to_wire_error(exc)}

    def _check_version(self, request: Request) -> None:
        seen = request.headers.get(_VERSION_HEADER)
        # Clients MUST send it; we enforce only a MISMATCH (a wrong version is a
        # silent-failure trap), tolerating omission for robustness.
        if seen is not None and seen != A2A_VERSION:
            raise we.version_not_supported(seen)

    def _authenticate(self, request: Request) -> AuthContext:
        ctx = self.auth.authenticate(request.headers)
        if ctx is None or not ctx.authenticated:
            # A2A authenticates every request; unauthenticated -> 401 (spec §7.4).
            raise _Unauthenticated()
        return ctx

    # -- routes -------------------------------------------------------------
    async def rpc(self, request: Request) -> Response:
        try:
            self._check_version(request)
        except we.A2AError as exc:
            return JSONResponse(self._err(None, exc))

        try:
            body = json.loads(await request.body())
        except Exception:
            return JSONResponse(self._err(None, we.JSONParseError("Parse error")))

        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or "method" not in body:
            return JSONResponse(
                self._err(
                    body.get("id") if isinstance(body, dict) else None,
                    we.InvalidRequestError("Invalid Request"),
                )
            )

        req_id = body.get("id")
        method = body["method"]
        params = body.get("params") or {}

        try:
            ctx = self._authenticate(request)
        except _Unauthenticated:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32600, "message": "Unauthenticated"},
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if method in _PUSH_METHODS:
            return JSONResponse(self._err(req_id, we.push_not_supported()))

        if method in _STREAMING:
            return self._stream_response(req_id, method, params, ctx)

        return self._unary_response(req_id, method, params, ctx)

    def _unary_response(self, req_id, method, params, ctx) -> Response:
        try:
            result = self._dispatch_unary(method, params, ctx)
        except we.A2AError as exc:
            return JSONResponse(self._err(req_id, exc))
        except Exception as exc:  # never leak internals (authz.md §6)
            return JSONResponse(self._err(req_id, we.InternalError("Internal error")))
        return JSONResponse(self._ok(req_id, result))

    def _dispatch_unary(self, method, params, ctx) -> Any:
        if method == "SendMessage":
            return self.adapter.send_message(params, ctx)
        if method == "GetTask":
            return self.adapter.get_task(params, ctx)
        if method == "ListTasks":
            return self.adapter.list_tasks(params, ctx)
        if method == "CancelTask":
            return self.adapter.cancel_task(params, ctx)
        if method == "GetExtendedAgentCard":
            return self.adapter.extended_card(params.get("tenant"), ctx)
        raise we.MethodNotFoundError(f"Method not found: {method}")

    def _stream_response(self, req_id, method, params, ctx) -> Response:
        def frames() -> Iterator[dict]:
            if method == "SendStreamingMessage":
                yield from self.adapter.send_streaming_message(params, ctx)
            elif method == "SubscribeToTask":
                yield from self.adapter.subscribe_to_task(params, ctx)
            else:  # pragma: no cover
                raise we.MethodNotFoundError(f"Method not found: {method}")

        def sse() -> Iterator[bytes]:
            try:
                for frame in frames():
                    payload = self._ok(req_id, frame)
                    yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            except we.A2AError as exc:
                yield f"data: {json.dumps(self._err(req_id, exc))}\n\n".encode("utf-8")
            except Exception:
                yield f"data: {json.dumps(self._err(req_id, we.InternalError('Internal error')))}\n\n".encode(
                    "utf-8"
                )

        return StreamingResponse(sse(), media_type="text/event-stream")

    async def well_known_card(self, request: Request) -> Response:
        tenant = self._card_tenant(request)
        if tenant is None:
            return JSONResponse({"error": "tenant not found"}, status_code=404)
        try:
            card = self.adapter.well_known_card(tenant)
        except we.A2AError:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(card, headers={"Cache-Control": "public, max-age=60"})

    async def extended_card(self, request: Request) -> Response:
        try:
            ctx = self._authenticate(request)
        except _Unauthenticated:
            return JSONResponse(
                {"error": "unauthenticated"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        tenant = self._card_tenant(request)
        if tenant is None:
            return JSONResponse({"error": "tenant not found"}, status_code=404)
        try:
            card = self.adapter.extended_card(tenant, ctx)
        except we.A2AError:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(card)

    def _card_tenant(self, request: Request) -> str | None:
        """Pick the tenant for a card route.

        The shared server fronts many tenants at one URL, disambiguated by ``tenant``
        (card-projection.md §2). Discovery selects it via ``?tenant=``; a single-tenant
        host (e.g. an external per-repo host) needs no query param.
        """
        tenant = request.query_params.get("tenant")
        if tenant:
            return tenant
        enabled = [t.tenant for t in self.adapter.config.tenants if t.enabled]
        return enabled[0] if len(enabled) == 1 else None

    async def healthz(self, request: Request) -> Response:
        return PlainTextResponse("ok")

    # -- app ----------------------------------------------------------------
    def routes(self) -> list[Route]:
        return [
            Route("/rpc", self.rpc, methods=["POST"]),
            Route("/.well-known/agent-card.json", self.well_known_card, methods=["GET"]),
            Route("/extendedAgentCard", self.extended_card, methods=["GET"]),
            Route("/healthz", self.healthz, methods=["GET"]),
        ]

    def app(self) -> Starlette:
        return Starlette(routes=self.routes())


class _Unauthenticated(Exception):
    pass


def build_app(adapter: A2AAdapter, authenticator: Authenticator) -> Starlette:
    return A2AServer(adapter, authenticator).app()
