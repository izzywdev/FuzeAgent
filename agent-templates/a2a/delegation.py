"""The `delegated-principal` A2A extension (contracts/a2a/ext/delegated-principal/v1).

WHY THIS EXISTS. v1's `AuthContext.caller` is one string, and a caller identity is
a bare repo name or an `Exec-*` principal (authz.md §2). There is no end-user
subject anywhere in the model, so a CEO and a warehouse worker arriving through
the same calling repo are indistinguishable to the callee: if `FuzeExecutive` is
in `FuzePlan`'s `providesTo`, both pass identically.

THE POD IS A DELEGATE, NEVER A PRINCIPAL. It holds no standing authority over
product data; its workload credential authorizes exactly one thing — presenting
delegated tokens. Every bit of data-plane authority arrives with the call. The
alternative, giving the pod broad rights and having it check the caller first, is
the confused deputy: the guard becomes a matter of remembering to look.

This module is ADDITIVE. `Delegation` absent from an AuthContext means the callee
did not adopt the extension, and `authorize()` behaves exactly as v1. Nothing
here can make a v1 deployment stricter or looser than it was.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

EXTENSION_URI = "https://contracts.fuzefront.com/a2a/ext/delegated-principal/v1"

_SUBJECT_RE = re.compile(r"^(user|service):[^\s:]+$")
_ACTOR_RE = re.compile(r"^(repo|agent|service):[^\s:]+$")


class SkillClass(str, Enum):
    """Closed. There is deliberately no fourth member and no default.

    An unclassified skill is DENIED, not treated as `DELEGABLE`. A default would
    mean a newly written skill acquires the weakest rule in the system by being
    written rather than by being decided — the same closed-set property the route
    and OpenAPI gates enforce.
    """

    DELEGABLE = "delegable"
    PRINCIPAL_REQUIRED = "principal-required"
    NEVER_DELEGABLE = "never-delegable"


class DelegationError(ValueError):
    """A malformed policy. Raised at load, never carried into a decision."""


@dataclass(frozen=True)
class Delegation:
    """Claims read from an ALREADY-VERIFIED credential.

    Constructing this from an unverified token is the one way to misuse the
    module: an unverified `sub` is worth less than no `sub`, because it looks
    like authority. The caller of `parse_claims` verifies signature and `aud`
    first — this module never sees a raw token and cannot check that for you.
    """

    #: RFC 8693 `sub` — the ORIGINATING principal, whom the work is ultimately for.
    subject: str
    #: RFC 8693 `act` chain, outermost first: immediate actor, then its actor.
    actor_chain: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DelegationPolicy:
    """A callee's classification of its own skills, plus who may broker what.

    Loaded from `.fuze/a2a-delegation.json` — see `from_manifest` for why it is a
    separate file rather than a manifest key.
    """

    skills: dict[str, SkillClass]
    brokerable: dict[str, frozenset[str]]
    authz_base_url: str | None = None

    @classmethod
    def from_manifest(cls, block: dict | None) -> "DelegationPolicy | None":
        """Build from `.fuze/a2a-delegation.json`, or None when the file is absent.

        Its OWN file, not a key in the manifest's `a2a` block: v1's
        manifest-a2a-extension.schema.json sets additionalProperties:false there,
        so a `delegation` key would make every adopting repo's manifest fail v1
        validation. An extension you must edit the frozen contract to adopt is a
        version, not an extension.

        None means "this callee did not adopt the extension" and restores exact v1
        behaviour. A block that is PRESENT but malformed raises: half-configured
        delegation is more dangerous than none, because it reads as protection.
        """
        if not block:
            return None
        if block.get("extension") != EXTENSION_URI:
            raise DelegationError(
                f"delegation block does not name {EXTENSION_URI}; refusing to guess "
                f"which extension's rules apply"
            )
        raw_skills = block.get("skills")
        if not isinstance(raw_skills, dict) or not raw_skills:
            raise DelegationError("delegation.skills must be a non-empty object")
        skills = {}
        for key, value in raw_skills.items():
            try:
                skills[key] = SkillClass(value)
            except ValueError as exc:
                raise DelegationError(
                    f"skill {key!r} has unknown class {value!r}; the classes are "
                    f"{[c.value for c in SkillClass]} and there is no default"
                ) from exc
        raw_brokerable = block.get("brokerable")
        if not isinstance(raw_brokerable, dict):
            raise DelegationError("delegation.brokerable must be an object")
        brokerable = {}
        for actor, roles in raw_brokerable.items():
            if not _ACTOR_RE.match(actor):
                raise DelegationError(
                    f"brokerable key {actor!r} is not a typed actor reference "
                    f"(repo:/agent:/service:)"
                )
            if not isinstance(roles, list):
                raise DelegationError(f"brokerable[{actor!r}] must be an array")
            brokerable[actor] = frozenset(roles)
        return cls(skills=skills, brokerable=brokerable,
                   authz_base_url=block.get("authzBaseUrl"))

    def classify(self, skill: str) -> SkillClass | None:
        """The skill's class, or None when unclassified. None is DENY, not a default."""
        return self.skills.get(skill)

    def brokerable_by(self, actor_chain: tuple[str, ...], skill: str) -> bool:
        """May any actor in the chain broker this skill?

        An actor absent from `brokerable` brokers NOTHING — absence is not a
        wildcard. An explicit empty list says the same thing on purpose, which is
        a meaningful statement in a way absence is not.
        """
        return any(skill in self.brokerable.get(actor, frozenset())
                   for actor in actor_chain)


def parse_claims(claims: dict | None) -> Delegation | None:
    """Delegation from VERIFIED credential claims, or None when absent.

    Raises DelegationError on a malformed chain rather than dropping the bad
    entry: an actor reference that cannot be evaluated must not be treated as
    satisfied, and silently ignoring it is exactly that.
    """
    if not claims:
        return None
    subject = claims.get("sub")
    if not subject:
        return None
    if not _SUBJECT_RE.match(subject):
        raise DelegationError(
            f"sub {subject!r} is not a typed principal (user:/service:); an untyped "
            f"id cannot be resolved to a principal kind and so cannot be checked"
        )
    chain: list[str] = []
    node = claims.get("act")
    while isinstance(node, dict):
        actor = node.get("sub")
        if not actor or not _ACTOR_RE.match(actor or ""):
            raise DelegationError(
                f"actor {actor!r} is not a typed reference (repo:/agent:/service:); "
                f"it cannot be matched against the brokerable set"
            )
        chain.append(actor)
        node = node.get("act")
    if not chain:
        raise DelegationError(
            "sub is present but the act chain is empty; a delegated call must name "
            "the actor doing the delegating"
        )
    return Delegation(subject=subject, actor_chain=tuple(chain))
