#!/usr/bin/env bash
# Regenerate the typed models from the frozen schemas.
#
# The models are GENERATED ARTIFACTS. Never hand-edit
# fuze_a2a_client/{wire_models,card_models}.py — change the schema and re-run this.
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

gen "$schema/a2a-wire.schema.json"   "$out/wire_models.py"
gen "$schema/agent-card.schema.json" "$out/card_models.py"

echo "regenerated: $out/wire_models.py $out/card_models.py"
