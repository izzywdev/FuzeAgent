# Vendored copy — DO NOT EDIT

These three files are byte-identical vendored copies of the FROZEN A2A contract
schemas at `agent-templates/contracts/a2a/v1/schema/` (`tenant-registration.schema.json`,
`agent-card.schema.json`, `fuze-profile.schema.json`).

Why a copy instead of a reference: the orchestrator's Docker build context is
`services/orchestrator` only (`.github/workflows/release.yml` → `context:
services/orchestrator`), so a file outside this directory tree is not present in the
built image and would 500 at runtime. `a2a_tenant_registration.py` therefore reads its
validation schemas from here, not from `agent-templates/`.

These files are owned by the contract (`izzywdev/FuzeAgent#203` /
`tenant-registration.md`), NOT by this service — never hand-edit them here. If the
contract changes, re-sync via:

```
cp agent-templates/contracts/a2a/v1/schema/{tenant-registration,agent-card,fuze-profile}.schema.json \
   services/orchestrator/contracts/a2a/v1/schema/
```

`tests/test_a2a_tenant_registration.py::test_vendored_schemas_match_frozen_contract`
asserts byte-identity against the source and fails the build if they drift.
