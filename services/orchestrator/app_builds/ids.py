"""Server-minted identifiers for app-build sessions.

Standard: governance/identifier-standard.md (TypeID: ``<prefix>_<26-char base32 UUIDv7>``).
FuzeAgent owns the *agent session* entity, so FuzeAgent mints its id; the FuzeFront
``buildSessionId`` is a *reference* to FuzeFront's own entity and is never reused as ours.

``fuzefront-identity`` (the sanctioned Python constructor) is not installable from this
repo's dependency set yet, so this module is a minimal, spec-compatible TypeID minter.
TODO(identity-adoption): replace ``mint_agent_session_ref`` with
``fuzefront_identity.mint_id("agentBuildSession")`` once that wheel is a dependency.
"""

from __future__ import annotations

import re
import secrets
import time

#: Product namespace (``.fuze/manifest.json`` ``identity.namespace``) + type.
AGENT_BUILD_SESSION_PREFIX = "agent_abs"

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_SUFFIX_RE = r"[0-7][0-9a-hjkmnp-tv-z]{25}"
AGENT_SESSION_REF_RE = re.compile(rf"^{AGENT_BUILD_SESSION_PREFIX}_{_SUFFIX_RE}$")


def _uuid7_int() -> int:
    """UUIDv7 layout: 48-bit unix-ms | 4-bit version | 12 rand | 2-bit variant | 62 rand."""
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(secrets.token_bytes(10), "big")
    rand_a = (rand >> 68) & 0xFFF
    rand_b = rand & ((1 << 62) - 1)
    return (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b


def _b32(n: int) -> str:
    out = []
    for _ in range(26):
        out.append(_ALPHABET[n & 31])
        n >>= 5
    return "".join(reversed(out))


def mint_agent_session_ref() -> str:
    """Mint a new agent-session reference (opaque past the prefix)."""
    return f"{AGENT_BUILD_SESSION_PREFIX}_{_b32(_uuid7_int())}"
