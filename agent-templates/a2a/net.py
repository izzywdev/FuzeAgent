"""Shared HTTP-URL scheme guard.

Used everywhere runtime code fetches a CONFIG-SUPPLIED URL (OIDC discovery/JWKS in
``runtime.py``, the tenant registry in ``registry.py``) so a ``file://``/``ftp://``
value can never be coerced into reading local files or another scheme (Semgrep
``dynamic-urllib-use-detected``). Extracted to its own module so both call sites share
one guard rather than drifting copies of the same check.
"""

from __future__ import annotations

from urllib.parse import urlparse

#: Only network schemes are ever fetched.
ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


def require_http_url(url: str, what: str) -> str:
    """Return ``url`` if it is an ``http(s)`` URL, else raise a config error."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        raise RuntimeError(
            f"{what} must be an http(s) URL (got scheme {scheme or '(none)'!r}): {url!r}"
        )
    return url
