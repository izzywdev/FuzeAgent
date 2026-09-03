#!/usr/bin/env bash
# Regenerate the typed models from the frozen schemas.
#
# The models are GENERATED ARTIFACTS. Never hand-edit
# fuze_a2a_client/{wire_models,card_models,registration_models}.py — change the
# schema and re-run this.
# Hand-editing a generated model is how a client silently forks from its contract.
#
#   pip install 'datamodel-code-generator>=0.69'
#   ./regenerate.sh
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
schema="$here/../schema"
out="$here/fuze_a2a_client"

gen() {
  datamodel-codegen \
    --input "$1" \
    --input-file-type jsonschema \
    --output "$2" \
    --output-model-type pydantic_v2.BaseModel \
    --target-python-version 3.11 \
    --use-schema-description \
    --use-field-description \
    --disable-timestamp
}

gen "$schema/a2a-wire.schema.json"            "$out/wire_models.py"
gen "$schema/agent-card.schema.json"          "$out/card_models.py"

# tenant-registration.schema.json REFERENCES agent-card.schema.json cross-file for
# the `card` field (the card shape is reused by reference, never redefined —
# tenant-registration.md §4). datamodel-codegen refuses single-file output when a
# schema carries an external $ref ("Modular references require an output directory"),
# so we bundle deterministically: inline agent-card's root + $defs into a temp copy
# and rewrite the external ref to a local one, then codegen a single file. The
# COMMITTED schema keeps the clean cross-file $ref; only this build step dereferences.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
python3 - "$schema/tenant-registration.schema.json" "$schema/agent-card.schema.json" "$tmp/tenant-registration.bundled.json" <<'PY'
import json, sys
reg_path, card_path, out_path = sys.argv[1:4]
reg = json.load(open(reg_path)); card = json.load(open(card_path))
# Merge the card's $defs into the registration $defs (no key collisions by design),
# add an `AgentCard` def holding the card's root, and repoint the external $ref.
reg.setdefault("$defs", {})
for k, v in card.get("$defs", {}).items():
    reg["$defs"][k] = v
reg["$defs"]["AgentCard"] = {k: v for k, v in card.items()
                             if k not in ("$schema", "$id", "$defs")}
def repoint(node):
    if isinstance(node, dict):
        if node.get("$ref") == "agent-card.schema.json":
            node["$ref"] = "#/$defs/AgentCard"
        for v in node.values():
            repoint(v)
    elif isinstance(node, list):
        for v in node:
            repoint(v)
repoint(reg)
json.dump(reg, open(out_path, "w"), indent=2)
PY
gen "$tmp/tenant-registration.bundled.json"   "$out/registration_models.py"

echo "regenerated: $out/wire_models.py $out/card_models.py $out/registration_models.py"
