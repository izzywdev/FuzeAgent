"""Environment-driven settings for the app-build API (all optional, fail-closed)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple
from urllib.parse import urlsplit


def _origin(url: str) -> Optional[str]:
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    port = f":{p.port}" if p.port else ""
    return f"{p.scheme}://{p.hostname.lower()}{port}"


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        v = int(env.get(key, "") or default)
    except ValueError:
        return default
    return v if v > 0 else default


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    try:
        v = float(env.get(key, "") or default)
    except ValueError:
        return default
    return v if v > 0 else default


@dataclass(frozen=True)
class Settings:
    #: Bearer secret FuzeFront presents (its FUZEAGENT_BUILD_API_TOKEN). Unset => 503.
    inbound_token: str = ""
    #: FuzeFront applications-service base (register.sh's FUZEFRONT_API_URL).
    fuzefront_api_url: str = ""
    #: FuzeFront public base; resolves a relative callbackUrl.
    fuzefront_public_base_url: str = ""
    #: Platform service-account token (register.sh's FUZEFRONT_REGISTRATION_TOKEN).
    fuzefront_token: str = ""
    #: Extra origins a callbackUrl may point at (comma separated in env).
    callback_allowed_origins: Tuple[str, ...] = field(default_factory=tuple)
    #: Optional UI deep-link template, e.g. https://app.fuzefront.com/app/fuzeagent/x/{agentSessionRef}
    session_url_template: str = ""
    callback_max_attempts: int = 5
    callback_base_delay_s: float = 5.0
    callback_max_delay_s: float = 300.0
    http_timeout_s: float = 10.0
    registry_attempts: int = 3
    poll_interval_s: float = 2.0

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        e = os.environ if env is None else env
        extra = tuple(
            o
            for o in (
                _origin(x)
                for x in (e.get("APP_BUILD_CALLBACK_ALLOWED_ORIGINS") or "").split(",")
            )
            if o
        )
        return cls(
            inbound_token=(e.get("APP_BUILD_API_TOKEN") or "").strip(),
            fuzefront_api_url=(e.get("FUZEFRONT_API_URL") or "").strip().rstrip("/"),
            fuzefront_public_base_url=(e.get("FUZEFRONT_PUBLIC_BASE_URL") or "")
            .strip()
            .rstrip("/"),
            fuzefront_token=(e.get("FUZEFRONT_REGISTRATION_TOKEN") or "").strip(),
            callback_allowed_origins=extra,
            session_url_template=(
                e.get("APP_BUILD_SESSION_URL_TEMPLATE") or ""
            ).strip(),
            callback_max_attempts=_int(e, "APP_BUILD_CALLBACK_MAX_ATTEMPTS", 5),
            callback_base_delay_s=_float(
                e, "APP_BUILD_CALLBACK_BASE_DELAY_SECONDS", 5.0
            ),
            callback_max_delay_s=_float(
                e, "APP_BUILD_CALLBACK_MAX_DELAY_SECONDS", 300.0
            ),
            http_timeout_s=_float(e, "APP_BUILD_HTTP_TIMEOUT_SECONDS", 10.0),
            registry_attempts=_int(e, "APP_BUILD_REGISTRY_ATTEMPTS", 3),
            poll_interval_s=_float(e, "APP_BUILD_POLL_INTERVAL_SECONDS", 2.0),
        )

    @property
    def registry_base(self) -> str:
        """Where app registration goes: internal API URL first, else public base."""
        return self.fuzefront_api_url or self.fuzefront_public_base_url

    @property
    def callback_base(self) -> str:
        """Where a relative callbackUrl resolves: public base first, else API URL."""
        return self.fuzefront_public_base_url or self.fuzefront_api_url

    def missing_for_launch(self) -> Tuple[str, ...]:
        """Names of required-but-unset settings; non-empty => the API fails closed (503)."""
        missing = []
        if not self.inbound_token:
            missing.append("APP_BUILD_API_TOKEN")
        if not self.registry_base:
            missing.append("FUZEFRONT_API_URL")
        if not self.fuzefront_token:
            missing.append("FUZEFRONT_REGISTRATION_TOKEN")
        return tuple(missing)

    def allowed_callback_origins(self) -> Tuple[str, ...]:
        origins = [
            o
            for o in (
                _origin(self.fuzefront_public_base_url),
                _origin(self.fuzefront_api_url),
            )
            if o
        ]
        return tuple(dict.fromkeys([*origins, *self.callback_allowed_origins]))

    def session_url(self, agent_session_ref: str) -> Optional[str]:
        if not self.session_url_template:
            return None
        return self.session_url_template.replace("{agentSessionRef}", agent_session_ref)
