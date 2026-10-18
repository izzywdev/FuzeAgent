"""Feature-flag read for the app-build API.

Flag: ``fuzeagent.app-builds.enabled`` — type **release**, default **OFF**, owner
``backend-engineer`` (flag admin: ``feature-flags-engineer``), removal criterion: delete
once the build-with-agent flow has been 100% enabled in prod for 2 weeks without incident.

The Python orchestrator has no OpenFeature/Unleash client yet (``@fuzefront/feature-flags``
is Node-only), so the default provider is a static env provider:
``FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED=true``. ``set_provider`` is the seam for an
Unleash-backed provider later. Any provider error evaluates to the in-code default (OFF).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Callable, Mapping, Optional

logger = logging.getLogger(__name__)

APP_BUILDS_FLAG = "fuzeagent.app-builds.enabled"

#: provider(flag_key, default, context) -> bool
Provider = Callable[[str, bool, Mapping[str, str]], bool]


def env_var_for(flag_key: str) -> str:
    return "FEATURE_FLAG_" + re.sub(r"[^A-Za-z0-9]+", "_", flag_key).upper()


def _env_provider(flag_key: str, default: bool, context: Mapping[str, str]) -> bool:
    raw = os.environ.get(env_var_for(flag_key))
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


_provider: Provider = _env_provider


def set_provider(provider: Optional[Provider]) -> None:
    """Swap the provider (tests / future Unleash). ``None`` restores the env provider."""
    global _provider
    _provider = provider or _env_provider


def is_enabled(
    flag_key: str, default: bool = False, context: Optional[Mapping[str, str]] = None
) -> bool:
    try:
        return bool(_provider(flag_key, default, context or {}))
    except Exception as exc:  # fail to the in-code default (OFF for a release flag)
        logger.warning(
            "flag evaluation failed flag=%s err=%s; using default=%s",
            flag_key,
            type(exc).__name__,
            default,
        )
        return default


def app_builds_enabled() -> bool:
    # Release flag: default OFF. Context: app + environment (no user/org on a machine call).
    return is_enabled(
        APP_BUILDS_FLAG,
        False,
        {
            "app": "fuzeagent-orchestrator",
            "environment": os.environ.get("ENVIRONMENT", "local"),
        },
    )
