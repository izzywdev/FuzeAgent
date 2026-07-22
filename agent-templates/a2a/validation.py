"""Validate a generated card against the frozen contract schemas.

A card MUST validate against BOTH ``agent-card.schema.json`` (the open A2A shape) and
``fuze-profile.schema.json`` (the family constraints layered on top). The profile
``$ref``s the card schema by relative filename, so we resolve refs against the schema
directory.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

from ._contract import SCHEMA_DIR


@lru_cache(maxsize=None)
def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validator(root_schema_name: str) -> Draft202012Validator:
    schema = _schema(root_schema_name)
    # Resolve sibling $ref filenames (agent-card.schema.json) against the schema dir.
    store = {
        s["$id"]: s for s in (_schema(p.name) for p in SCHEMA_DIR.glob("*.json")) if "$id" in s
    }
    base = SCHEMA_DIR.as_uri() + "/"
    resolver = RefResolver(base_uri=base, referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)


def validate_card(card: dict[str, Any]) -> None:
    """Raise ``jsonschema.ValidationError`` if the card violates schema or profile."""
    _validator("agent-card.schema.json").validate(card)
    _validator("fuze-profile.schema.json").validate(card)


def card_errors(card: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for name in ("agent-card.schema.json", "fuze-profile.schema.json"):
        for e in _validator(name).iter_errors(card):
            errs.append(f"[{name}] {'/'.join(str(p) for p in e.absolute_path)}: {e.message}")
    return errs
