"""HTTP surface for FuzeFront "build your application" sessions.

  POST /api/v1/app-builds                       launch (FUZEAGENT_BUILD_API_URL points here)
  GET  /api/v1/app-builds/{buildSessionId}      read session state
  POST /api/v1/app-builds/{buildSessionId}/cancel

Machine-to-machine: ``Authorization: Bearer <APP_BUILD_API_TOKEN>`` (constant-time compare,
fail-closed when the secret is unset). Gated by release flag ``fuzeagent.app-builds.enabled``
(default OFF -> 503 ``feature_disabled``). Contract: docs/app-builds.md,
contracts/app-builds.openapi.yaml. The brief and token are never logged; ids + lengths only.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import flags
from .fuzefront import CallbackUrlRejected
from .models import BUILD_SESSION_ID_PATTERN, BuildRecord, LaunchRequest
from .runtime import BuildRuntime, IdempotencyConflict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/app-builds", tags=["app-builds"])

# Fixed, caller-safe explanations for a rejected callbackUrl, keyed by the short code that
# CallbackUrlRejected carries. Nothing from the exception itself reaches the response.
CALLBACK_REJECTION_DEFAULT = "callbackUrl is not acceptable"
CALLBACK_REJECTION_MESSAGES: Dict[str, str] = {
    "not_a_url": "callbackUrl is not a valid URL",
    "bad_scheme_or_credentials": "callbackUrl must be an http(s) URL without credentials",
    "origin_not_allowed": "callbackUrl origin is not an allowed FuzeFront origin",
    "wrong_path": "callbackUrl path must be this session's status endpoint",
    "relative_without_base": "a relative callbackUrl cannot be resolved by this service",
}

MAX_BODY_BYTES = 32 * 1024
_ID_RE = re.compile(BUILD_SESSION_ID_PATTERN)

_runtime: Optional[BuildRuntime] = None


def set_runtime(runtime: Optional[BuildRuntime]) -> None:
    global _runtime
    _runtime = runtime


def get_runtime() -> Optional[BuildRuntime]:
    return _runtime


def _err(status: int, error: str, message: str, **extra: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": error, "message": message, **extra}
    )


def _token_ok(presented: str, expected: str) -> bool:
    # Hash both sides so the compare is constant-time regardless of length.
    a = hashlib.sha256(presented.encode()).digest()
    b = hashlib.sha256(expected.encode()).digest()
    return hmac.compare_digest(a, b)


async def _guard(
    request: Request, runtime: Optional[BuildRuntime] = Depends(get_runtime)
):
    """Auth -> config -> flag, in that order. Returns a JSONResponse to short-circuit, else None."""
    if runtime is None:
        return _err(
            503,
            "builder_unavailable",
            "The application builder is not configured on this server",
        )
    s = runtime.settings
    if not s.inbound_token:  # fail CLOSED: never accept unauthenticated
        logger.error("app_builds rejected: APP_BUILD_API_TOKEN is not configured")
        return _err(
            503,
            "builder_unavailable",
            "The application builder is not configured on this server",
        )
    header = request.headers.get("authorization", "")
    scheme, _, presented = header.partition(" ")
    if (
        scheme.lower() != "bearer"
        or not presented.strip()
        or not _token_ok(presented.strip(), s.inbound_token)
    ):
        logger.warning("app_builds auth rejected path=%s", request.url.path)
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid bearer token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not flags.app_builds_enabled():
        return _err(
            503,
            "feature_disabled",
            f"The app-build API is not enabled ({flags.APP_BUILDS_FLAG})",
        )
    missing = s.missing_for_launch()
    if missing:
        logger.error("app_builds misconfigured: missing %s", ",".join(missing))
        return _err(
            503,
            "builder_unavailable",
            "The application builder is not configured on this server",
        )
    return None


def _view(rec: BuildRecord, runtime: BuildRuntime) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "agentSessionRef": rec.agent_session_ref,
        "buildSessionId": rec.build_session_id,
        "status": rec.status,
    }
    url = runtime.settings.session_url(rec.agent_session_ref)
    if url:
        body["agentSessionUrl"] = url
    if rec.app_slug:
        body["appSlug"] = rec.app_slug
    if rec.error_code:
        body["errorCode"] = rec.error_code
    return body


@router.post("")
async def launch_build(
    request: Request,
    blocked=Depends(_guard),
    runtime: Optional[BuildRuntime] = Depends(get_runtime),
):
    if blocked is not None:
        return blocked
    assert runtime is not None
    start = time.monotonic()
    req_id = request.headers.get("x-request-id", "")[:100]
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return _err(413, "payload_too_large", "Request body too large")
    try:
        req = LaunchRequest.model_validate_json(raw)
    except ValidationError as exc:
        fields = [
            {"path": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        logger.info(
            "app_builds launch invalid req_id=%s fields=%s",
            req_id,
            [f["path"] for f in fields],
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": "Request body failed validation",
                "fields": fields,
            },
        )
    try:
        rec, created = await runtime.accept(req)
    except CallbackUrlRejected as exc:
        # Fixed messages keyed by a short code: never echo exception text to the caller.
        message = CALLBACK_REJECTION_MESSAGES.get(exc.code, CALLBACK_REJECTION_DEFAULT)
        logger.info(
            "app_builds launch callbackUrl rejected req_id=%s code=%s", req_id, exc.code
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": "Request body failed validation",
                "fields": [{"path": "callbackUrl", "message": message}],
            },
        )
    except IdempotencyConflict:
        return _err(
            409,
            "idempotency_conflict",
            "buildSessionId was already used with a different request",
        )
    logger.info(
        "app_builds launch accepted build_session_id=%s created=%s context=%s name_len=%d brief_len=%d elapsed_ms=%d",
        rec.build_session_id,
        created,
        rec.context,
        len(rec.name),
        len(rec.brief),
        int((time.monotonic() - start) * 1000),
    )
    return JSONResponse(
        status_code=201 if created else 200, content=_view(rec, runtime)
    )


@router.get("/{build_session_id}")
async def get_build(
    build_session_id: str,
    blocked=Depends(_guard),
    runtime: Optional[BuildRuntime] = Depends(get_runtime),
):
    if blocked is not None:
        return blocked
    assert runtime is not None
    rec = (
        await runtime.store.get(build_session_id)
        if _ID_RE.match(build_session_id)
        else None
    )
    if rec is None:
        return _err(404, "not_found", "Build session not found")
    return _view(rec, runtime)


@router.post("/{build_session_id}/cancel")
async def cancel_build(
    build_session_id: str,
    blocked=Depends(_guard),
    runtime: Optional[BuildRuntime] = Depends(get_runtime),
):
    if blocked is not None:
        return blocked
    assert runtime is not None
    result = (
        await runtime.cancel(build_session_id)
        if _ID_RE.match(build_session_id)
        else None
    )
    if result is None:
        return _err(404, "not_found", "Build session not found")
    rec, changed = result
    return {**_view(rec, runtime), "cancelled": changed}
