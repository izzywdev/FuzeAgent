"""Deterministic slug derivation + local manifest validation (mirrors FuzeFront's rules).

FuzeFront's slug rule (manifest.schema.ts): ``^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$``. A slug
is IMMUTABLE once registered, so candidates are chosen BEFORE registering and an existing
app is never edited.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict, Iterator, List

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
_MAX_BASE = 48  # leaves room for a "-<6 hex>-<n>" suffix inside 64 chars


def derive_base_slug(name: str, build_session_id: str) -> str:
    folded = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    s = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")[:_MAX_BASE].strip("-")
    if len(s) < 3:
        s = f"app-{_short_hash(build_session_id)}"
    return s


def _short_hash(build_session_id: str) -> str:
    return hashlib.sha256(build_session_id.encode()).hexdigest()[:6]


def candidate_slugs(name: str, build_session_id: str, limit: int = 6) -> Iterator[str]:
    """base, base-<h6>, base-<h6>-2, … — deterministic for a given (name, session)."""
    base = derive_base_slug(name, build_session_id)
    h = _short_hash(build_session_id)
    yield base
    yield f"{base}-{h}"
    for n in range(2, limit):
        yield f"{base}-{h}-{n}"


_SAME_ORIGIN_PATH_RE = re.compile(r"^/(?![/\\])[^\s?#\\]*$")
_INTEGRATION_TYPES = {"module-federation", "iframe", "web-component", "spa"}


def _asset_url_ok(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    if _SAME_ORIGIN_PATH_RE.match(v):
        return True
    return bool(re.match(r"^https?://[^\s/]+", v))


def validate_integration(integration: Any) -> List[str]:
    """Subset of FuzeFront's integrationSchema; returns a list of problems."""
    if not isinstance(integration, dict):
        return ["integration must be an object"]
    problems: List[str] = []
    allowed = {"type", "remoteEntry", "scope", "module", "url"}
    extra = set(integration) - allowed
    if extra:
        problems.append(f"unknown integration keys: {sorted(extra)}")
    t = integration.get("type")
    if t not in _INTEGRATION_TYPES:
        problems.append("integration.type invalid")
    for k in ("remoteEntry", "url"):
        if k in integration and not _asset_url_ok(integration[k]):
            problems.append(
                f"integration.{k} must be a same-origin absolute path or http(s) URL"
            )
    if t == "module-federation":
        for k in ("remoteEntry", "scope", "module"):
            if not integration.get(k):
                problems.append(f"integration.{k} is required for module-federation")
    return problems


def build_manifest(
    *,
    slug: str,
    name: str,
    brief: str,
    context: str,
    integration: Dict[str, Any],
    description: str | None,
) -> Dict[str, Any]:
    desc = (description or brief)[:1000]
    return {
        "manifestVersion": "1",
        "slug": slug,
        "name": name[:120],
        "menuLabel": name[:40],
        "description": desc,
        "mode": "portal",
        "modes": ["portal"],
        "integration": integration,
        "visibility": "private" if context == "personal" else "organization",
    }
