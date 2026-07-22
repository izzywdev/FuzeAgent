# `agent-templates/a2a` — shared A2A server + card generator

The **callee side** of the frozen A2A contract v1
(`agent-templates/contracts/a2a/v1`). ONE server fronts every product and exec-tier
agent in the family; a repo onboards by adding a `tenant` entry to the Helm values —
never a new pod. This package is a **thin adapter** over the existing Managed-Agents
runtime (`agent-templates/providers` + `orchestration`); it holds **no task engine**.

> Scope note: this is backend-engineer's slice. The image/Dockerfile, Helm chart,
> Argo Application and CI image build are **devops-engineer's**; independent
> conformance / authZ-negative tests are **test-engineer's**; the handoff-MCP-over-A2A
> client routing is **mcp-engineer's**; operator docs are **docs-maintainer's**.

## Modules

| module | responsibility | contract |
|---|---|---|
| `card_generator.py` | project `manifest.json` + `roles/*/role.json` → Agent Card | `card-projection.md` |
| `validation.py` | validate a card against `agent-card.schema.json` + `fuze-profile.schema.json` | `schema/` |
| `task_mapper.py` | `run_until_block` result → A2A `Task`; INPUT vs AUTH_REQUIRED classifier | `state-mapping.md` |
| `authz.py` | callee-enforced `providesTo` allowlist, **fail-closed** | `authz.md` |
| `identity.py` | transport credential → trusted caller identity (OIDC bearer) | `authz.md §2` |
| `session_store.py` | caller-ownership index + reflected `Task` snapshot (NOT an engine) | `state-mapping.md §7` |
| `adapter.py` | wire methods → `AgentProvider` seam (the translation) | `state-mapping.md` |
| `server.py` | JSON-RPC 2.0 over HTTP + SSE (`POST /rpc`, well-known card) | `binding.md` |
| `config.py` | parse the `values-interface.schema.json` document | `values-interface` |
| `runtime.py` | compose config → adapter → server with a real provider + OIDC | — |

## Key invariants enforced here

- **Cards are derived, deterministic, and signed.** Same inputs → byte-identical card
  (modulo `signatures`). Never hand-authored. `tools`/`mcp_servers`/`vault` are never
  projected (encapsulation invariant, `card-projection.md §7`).
- **The callee enforces; the caller is opaque.** Authorization uses only the validated
  credential identity, never the request body. Absent `providesTo` → **DENY**.
- **No new task engine.** `Task.id` IS the provider `session_id`. Continuations use
  `confirm_tool` / `resume_session`, never transcript replay. `FAILED` is not retried.
- **Interrupted ≠ terminal.** An `always_ask` pause is `INPUT_REQUIRED`; a missing
  credential/grant is `AUTH_REQUIRED`; both may be resolved out-of-band by `reach_human`
  with no caller message, and the adapter never downgrades them on timeout.
- **Dual-runtime clean.** Pure-Python, service-DNS addressing, `ClusterIP`-only,
  config from env/secret; no assumption that holds in only compose or only Helm.

## Run the unit tests

```bash
pip install pydantic starlette httpx jsonschema pytest
cd agent-templates/a2a && python -m pytest tests -q
```

The contract client package is put on `sys.path` automatically by `_contract.py`, so no
editable install is required.

## Local run

```bash
export A2A_VALUES_FILE=/path/to/values.json   # the a2a.* block
export A2A_REPOS_DIR=/repos                    # tenant repo checkouts
export AGENT_PROVIDER=anthropic
python -m a2a.runtime
```
