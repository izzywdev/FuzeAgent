# `agent-templates/a2a` — A2A server + card generator

The **callee side** of the frozen A2A contract v1
(`agent-templates/contracts/a2a/v1`). This package is a **thin adapter** over the existing
Managed-Agents runtime (`agent-templates/providers` + `orchestration`); it holds **no task
engine**.

Two deployment topologies, **one codebase and one values document**:

- **Shared server** (`a2a-shared`, namespace `fuzeagent`) — many `a2a.tenants[]`; a repo
  onboards by adding an entry, never a new pod. Cards at one URL, disambiguated by
  `AgentInterface.tenant`, which callers echo.
- **Per-product pod** (contract v1.2.0) — one deployment per product serving a single
  tenant, for compartmentalisation. It differs ONLY in `len(tenants) == 1` and in setting
  `a2a.inClusterUrl` to its own Service. That key is what made it possible: the advertised
  endpoint used to be a constant in `card_generator.py`, so a per-product pod started
  healthy and published the *shared* server's address — every caller that followed its card
  missed it. See `docs/a2a/per-product-pod.md`.

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
| `config.py` | parse the `values-interface.schema.json` document; union static + registry tenants | `values-interface` |
| `registry.py` | fetch the orchestrator's runtime tenant registry over HTTP (`httpx`, no DB) | `tenant-registration.md` |
| `runtime.py` | compose config → adapter → server with a real provider + OIDC | — |

## Key invariants enforced here

- **Cards are derived, deterministic, and signed.** Same inputs → byte-identical card
  (modulo `signatures`). Never hand-authored. `tools`/`mcp_servers`/`vault` are never
  projected (encapsulation invariant, `card-projection.md §7`).
- **The callee enforces; the caller is opaque.** Authorization uses only the validated
  credential identity, never the request body. Absent `providesTo` → **DENY**.
- **No new task engine.** `Task.id` IS the provider `session_id`. Continuations use
  `confirm_tool` / `resume_session`, never transcript replay. `FAILED` is not retried.
- **Stateless, DB-free tenant resolution (contract v1.3.0, `#203`).** The runtime
  tenant set is the UNION of the static `A2A_VALUES_FILE` ConfigMap and, when
  `A2A_REGISTRY_URL` is set, the orchestrator's HTTP tenant registry
  (`GET {url}/a2a/tenants?enabled=true`, fetched with `httpx` — never a DB client). A
  registry-sourced tenant carries its already-projected Agent Card as data, so it is
  served with no repo clone. An unreachable registry logs a warning and falls back to
  the static source alone — never a crash, never a served-tenant outage window.
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
export A2A_REPOS_DIR=/repos                    # tenant repo checkouts (static tenants)
export AGENT_PROVIDER=anthropic
export A2A_REGISTRY_URL=https://orchestrator.internal   # optional; contract v1.3.0
python -m a2a.runtime
```
