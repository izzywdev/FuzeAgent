"""Unit tests for the ``a2a`` block added to ``schema/role-manifest.schema.json`` (FA-12).

The block is additive and OPTIONAL — no existing role.json needs it — but it must:
  * accept a well-formed ``a2a`` block (so a role can carry ``examples``/``scopes``),
  * reject unknown keys (``additionalProperties: false``), and
  * stay in lockstep with the frozen contract's ``role-a2a-extension.schema.json``
    (the contract is canonical; the manifest schema mirrors its ``a2a`` property).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
_CONTRACT_DIR = (
    Path(__file__).resolve().parents[2] / "contracts" / "a2a" / "v1" / "schema"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def role_schema() -> dict:
    return _load(_SCHEMA_DIR / "role-manifest.schema.json")


def _base_manifest(**a2a) -> dict:
    m = {"role": "infra-operator", "name": "Infra Operator"}
    if a2a:
        m["a2a"] = a2a
    return m


def test_schema_itself_is_valid(role_schema):
    jsonschema.Draft202012Validator.check_schema(role_schema)


def test_role_without_a2a_block_still_valid(role_schema):
    jsonschema.validate(_base_manifest(), role_schema)


def test_wellformed_a2a_block_validates(role_schema):
    jsonschema.validate(
        _base_manifest(
            publish=True,
            extendedOnly=True,
            tags=["infra"],
            examples=["which chart owns the Grafana dashboards?"],
            scopes=["infra:operate"],
        ),
        role_schema,
    )


def test_unknown_a2a_key_is_rejected(role_schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_base_manifest(providesTo=["FuzeInfra"]), role_schema)


def test_a2a_block_mirrors_frozen_contract(role_schema):
    """The manifest schema's ``a2a`` property must match the frozen contract's, so a
    role.json valid against one is valid against the other. Compare the property set and
    the additionalProperties gate; descriptions may differ, structure may not."""
    contract = _load(_CONTRACT_DIR / "role-a2a-extension.schema.json")
    contract_a2a = contract["properties"]["a2a"]
    manifest_a2a = role_schema["properties"]["a2a"]

    assert manifest_a2a["additionalProperties"] is False
    assert manifest_a2a["additionalProperties"] == contract_a2a["additionalProperties"]
    assert set(manifest_a2a["properties"]) == set(contract_a2a["properties"])
    # each property's declared type matches the contract
    for key, spec in contract_a2a["properties"].items():
        assert manifest_a2a["properties"][key].get("type") == spec.get("type")
