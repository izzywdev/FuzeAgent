"""Wire schemas, the persisted session record, and the forward-only state machine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

BRIEF_MAX = 4000
NAME_MAX = 120
_TYPEID_SUFFIX = r"[0-9a-hjkmnp-tv-z]{26}"
BUILD_SESSION_ID_PATTERN = rf"^[a-z][a-z_]{{0,60}}_{_TYPEID_SUFFIX}$"
ORG_ID_PATTERN = rf"^org_{_TYPEID_SUFFIX}$"
USER_ID_PATTERN = rf"^usr_{_TYPEID_SUFFIX}$"


class LaunchRequest(BaseModel):
    """POST /api/v1/app-builds body. Strict: unknown keys (incl. an ``id``) are rejected."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    buildSessionId: str = Field(pattern=BUILD_SESSION_ID_PATTERN)
    organizationId: str = Field(pattern=ORG_ID_PATTERN)
    requestedByUserId: str = Field(pattern=USER_ID_PATTERN)
    context: Literal["personal", "organization"]
    name: str = Field(min_length=1, max_length=NAME_MAX)
    brief: str = Field(min_length=1, max_length=BRIEF_MAX)
    callbackUrl: str = Field(min_length=1, max_length=2048)

    @field_validator("name", "brief", mode="before")
    @classmethod
    def _must_be_str(cls, v: Any) -> Any:
        if not isinstance(v, str):
            raise ValueError("must be a string")
        return v


# ── state machine ────────────────────────────────────────────────────────────
ACCEPTED = "accepted"  # internal only; never reported to FuzeFront
BUILDING = "building"
DEPLOYING = "deploying"
DEPLOYED = "deployed"
FAILED = "failed"
CANCELLED = "cancelled"

TERMINAL = frozenset({DEPLOYED, FAILED, CANCELLED})
_RANK = {ACCEPTED: 0, BUILDING: 1, DEPLOYING: 2, DEPLOYED: 3}


class IllegalTransition(Exception):
    pass


def can_transition(current: str, target: str) -> bool:
    if current in TERMINAL:
        return False
    if target in (FAILED, CANCELLED):
        return True
    return target in _RANK and _RANK[target] > _RANK[current]


# ── persisted record ─────────────────────────────────────────────────────────
@dataclass
class BuildRecord:
    build_session_id: str
    agent_session_ref: str
    organization_id: str
    requested_by_user_id: str
    context: str
    name: str
    brief: str
    callback_url: str
    request_hash: str
    status: str = ACCEPTED
    created_at: float = 0.0
    updated_at: float = 0.0
    # resumable step markers
    artifact: Optional[Dict[str, Any]] = None
    deploy_result: Optional[Dict[str, Any]] = None
    slug: Optional[str] = None
    slugs_tried: List[str] = field(default_factory=list)
    register_attempted: bool = False
    registered: bool = False
    app_slug: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    # transactional outbox of status callbacks (see runtime.py)
    outbox: List[Dict[str, Any]] = field(default_factory=list)
    callbacks_halted: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BuildRecord":
        names = {f for f in cls.__dataclass_fields__}  # tolerate newer/older rows
        return cls(**{k: v for k, v in d.items() if k in names})

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL

    def has_pending_outbox(self) -> bool:
        return any(e["state"] == "pending" for e in self.outbox)

    def advance(self, target: str) -> None:
        """Forward-only transition. ``deployed`` additionally requires a registered app."""
        if not can_transition(self.status, target):
            raise IllegalTransition(f"{self.status} -> {target}")
        if target == DEPLOYED and not (self.registered and self.app_slug):
            raise IllegalTransition("deployed requires a registered app")
        self.status = target

    def enqueue_callback(self, payload: Dict[str, Any], now: float) -> None:
        self.outbox.append(
            {
                "seq": (self.outbox[-1]["seq"] + 1) if self.outbox else 1,
                "payload": payload,
                "state": "pending",
                "attempts": 0,
                "nextAttemptAt": now,
                "lastStatus": None,
                "lastError": None,
            }
        )

    def supersede_pending(self) -> None:
        for e in self.outbox:
            if e["state"] == "pending":
                e["state"] = "superseded"


def request_fingerprint(req: LaunchRequest) -> str:
    """Hash of the identity-bearing request fields, to detect an idempotency conflict."""
    material = json.dumps(
        [req.organizationId, req.requestedByUserId, req.context, req.name, req.brief],
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()
