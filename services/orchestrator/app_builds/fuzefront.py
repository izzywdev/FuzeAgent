"""Client for FuzeFront's public app-registry API (registration + status callbacks).

Auth is the platform service account FuzeAgent already uses for self-registration
(``FUZEFRONT_REGISTRATION_TOKEN``, header ``Authorization: Bearer <token>``). The token is
never logged. Every call logs start/end with elapsed ms (boundary logging).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlsplit

import httpx

from .config import Settings

logger = logging.getLogger(__name__)

CALLBACK_PATH_TEMPLATE = "/api/v1/app-registry/build-sessions/{id}/status"


class RegistryError(Exception):
    pass


class RegistryTransient(RegistryError):
    """Network error / 5xx / 429 — worth retrying."""


class RegistryAuthFailed(RegistryError):
    pass


class RegistryRejected(RegistryError):
    """4xx validation-style rejection of the manifest."""


class SlugConflict(RegistryError):
    pass


class CallbackUrlRejected(ValueError):
    """``callbackUrl`` failed validation. Carries only a short stable ``code``; the HTTP layer
    maps it to a fixed message (router.CALLBACK_REJECTION_MESSAGES) so no exception text, and no
    server configuration detail, is ever echoed to the caller."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def resolve_callback_url(raw: str, build_session_id: str, settings: Settings) -> str:
    """Resolve + validate ``callbackUrl``. The registration token is sent there, so it must
    only ever point at FuzeFront: allowed origins are the configured FuzeFront bases (plus an
    explicit allowlist) and the path must be exactly this session's status endpoint."""
    expected_path = CALLBACK_PATH_TEMPLATE.format(id=quote(build_session_id, safe=""))
    if raw.startswith("/") and not raw.startswith("//"):
        base = settings.callback_base
        if not base:
            raise CallbackUrlRejected("relative_without_base")
        url = base.rstrip("/") + raw
    else:
        url = raw
    try:
        p = urlsplit(url)
    except ValueError as exc:
        raise CallbackUrlRejected("not_a_url") from exc
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise CallbackUrlRejected("bad_scheme_or_credentials")
    port = f":{p.port}" if p.port else ""
    origin = f"{p.scheme}://{p.hostname.lower()}{port}"
    if origin not in settings.allowed_callback_origins():
        raise CallbackUrlRejected("origin_not_allowed")
    if p.path != expected_path or p.query or p.fragment:
        raise CallbackUrlRejected("wrong_path")
    return url


class FuzeFrontClient:
    def __init__(self, settings: Settings, http: Optional[httpx.AsyncClient] = None):
        self._s = settings
        self._http = http
        self._own = http is None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._s.http_timeout_s)
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and self._own:
            await self._http.aclose()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._s.fuzefront_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self, op: str, method: str, url: str, build_id: str, **kw: Any
    ) -> httpx.Response:
        start = time.monotonic()
        logger.debug("fuzefront.%s start build_session_id=%s", op, build_id)
        try:
            res = await self._client().request(
                method, url, headers={**self._headers(), "x-request-id": build_id}, **kw
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "fuzefront.%s failed build_session_id=%s elapsed_ms=%d err=%s",
                op,
                build_id,
                int((time.monotonic() - start) * 1000),
                type(exc).__name__,
            )
            raise RegistryTransient(f"{op}: {type(exc).__name__}") from exc
        logger.info(
            "fuzefront.%s end build_session_id=%s status=%d elapsed_ms=%d",
            op,
            build_id,
            res.status_code,
            int((time.monotonic() - start) * 1000),
        )
        return res

    # ── registry ─────────────────────────────────────────────────────────────
    async def slug_exists(self, slug: str, build_id: str) -> bool:
        base = self._s.registry_base.rstrip("/") + "/api/v1/app-registry"
        res = await self._request(
            "slug_exists", "GET", f"{base}/apps/{quote(slug, safe='')}", build_id
        )
        if res.status_code == 200:
            return True
        if res.status_code == 404:
            return False
        raise self._classify("slug_exists", res)

    async def register(
        self, manifest: Dict[str, Any], organization_id: str, build_id: str
    ) -> None:
        """POST /apps {manifest, organizationId}. 201/200 ok; 409 -> SlugConflict."""
        base = self._s.registry_base.rstrip("/") + "/api/v1/app-registry"
        res = await self._request(
            "register",
            "POST",
            f"{base}/apps",
            build_id,
            json={"manifest": manifest, "organizationId": organization_id},
        )
        if res.status_code in (200, 201):
            return
        if res.status_code == 409:
            raise SlugConflict(manifest.get("slug", ""))
        raise self._classify("register", res)

    @staticmethod
    def _classify(op: str, res: httpx.Response) -> RegistryError:
        code = res.status_code
        if code in (401, 403):
            return RegistryAuthFailed(f"{op}: HTTP {code}")
        if code == 429 or code >= 500:
            return RegistryTransient(f"{op}: HTTP {code}")
        return RegistryRejected(f"{op}: HTTP {code} {_safe_error(res)}")

    # ── status callback ──────────────────────────────────────────────────────
    async def post_callback(
        self, url: str, payload: Dict[str, Any], build_id: str
    ) -> Tuple[int, Dict[str, Any]]:
        """POST one status. Returns (http_status, parsed_json_or_{}); raises RegistryTransient
        only for transport errors (the caller classifies the status)."""
        res = await self._request(
            "status_callback", "POST", url, build_id, json=payload
        )
        try:
            body = res.json()
            body = body if isinstance(body, dict) else {}
        except ValueError:
            body = {}
        return res.status_code, body


def _safe_error(res: httpx.Response) -> str:
    try:
        b = res.json()
        if isinstance(b, dict):
            return str(b.get("message") or b.get("error") or "")[:200]
    except ValueError:
        pass
    return ""
