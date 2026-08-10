# FuzeAgent contracts

## `openapi.yaml` — the orchestrator API, as deployed

`contracts/openapi.yaml` describes the HTTP surface of
`services/orchestrator/main.py`: the FastAPI application the Helm chart deploys
as the `orchestrator` pod on port 8000, reachable in-cluster at
`http://orchestrator:8000`. 123 paths / 142 operations, every one extracted
statically from an `@app.<method>` decorator; summaries are the handlers' own
docstrings.

It is served live at `GET /openapi.yaml`, and it is what the MCP gateway pod is
configured with.

### `/openapi.yaml` is not `/openapi.json`

FastAPI already serves `/openapi.json`, generated from the code at import time.
That document is accurate about shapes and **says nothing about which operations
dispatch an agent that cannot be recalled**. Both are served. The curated one —
this file, plus the classification `mcp/tools.overrides.yaml` narrows — is the
contract.

## Read this before calling anything

FuzeAgent is not a CRUD API with a dangerous corner. Its purpose is to
**dispatch agents that take real actions**: they write files, run shell commands
in containers, call third-party APIs and spend money on model inference.
`POST /tasks/{task_id}/execute` returns in milliseconds, and by then an agent is
running. `POST /tasks/{task_id}/cancel` stops *future* work; it undoes nothing.

Two structural facts follow from reading the whole contract:

1. There is **no `DELETE /agents/{agent_id}`** and **no `DELETE /tasks/{task_id}`**.
   A created agent and a created task are permanent as far as this API goes.
2. The **only genuine undo** anywhere in the contract is
   `POST /tasks/{task_id}/file-operations/{batch_id}/rollback`, and it undoes an
   approved *file batch* and nothing else.

`mcp/tools.overrides.yaml` marks 16 operations irreversible on that basis —
classified on effect, never on verb. Notably `approveFileOperations` is marked
**reversible** despite writing files, because the rollback above is a real
compensating operation; and `stopMemoryEnabledAgent` is marked **reversible**
despite being a `DELETE`, because it stops an agent that can be deployed again.

## Known gaps

1. **The `hierarchy-api` backend is not covered.** `services/hierarchy_API`
   (the `hierarchy-api` pod, port 8006) is a second FastAPI application with
   roughly forty of its own routes for organizations, teams and agent hierarchy.
   One OpenAPI document maps to one upstream base URL, so covering it needs its
   own contract and its own gateway pod. Until then those operations are not on
   the MCP surface.

2. **Seven duplicate route registrations.** FastAPI keeps the FIRST handler for
   a `(path, method)` pair; the later one is dead code. The contract mirrors
   that, and the shadowed handlers are:

   | Route | Serving | Dead |
   |---|---|---|
   | `POST /agents/{agent_id}/register` | `register_agent` | `register_agent_capabilities` |
   | `POST /agents/{agent_id}/error` | `report_agent_error` | `report_agent_error` (defined twice) |
   | `GET /knowledge/search` | `search_knowledge` | `search_knowledge` (defined twice) |
   | `GET /teams` | `list_teams` | `get_teams` |
   | `GET /organizations/{organization_id}/goals` | `list_organization_goals` | `get_organization_goals` |
   | `GET /goals/{goal_id}` | `get_goal` | `get_goal_details` |
   | `GET /agents/{agent_id}/tasks` | `get_agent_tasks` | `get_agent_tasks_list` |

   `register_agent_capabilities` and `get_agent_tasks_list` are the ones worth a
   look: they are not duplicate definitions of the same thing, they are
   *different implementations* that never run.

3. **`POST /mcp/call-tool` is a passthrough of unknowable reversibility.** It
   invokes a tool on whatever MCP server an agent has configured, so whether the
   effect can be undone is a property of the downstream tool and is not
   derivable from this contract. It keeps the default reversible-write
   classification, which is the least-wrong available claim.

## Keeping the copies honest

The contract exists three times, for reasons Docker and Helm force:

| Copy | Why |
|---|---|
| `contracts/openapi.yaml` | the source of truth |
| `services/orchestrator/contracts/openapi.yaml` | the image is built with `context: services/orchestrator`, so the repo-root tree is not in the build context; this copy ships in the image and is what `GET /openapi.yaml` serves |
| `deploy/helm/fuzeagent/files/openapi.yaml` | Helm can only read files inside the chart directory; this is what the MCP gateway pod mounts |

```bash
scripts/sync-chart-files.sh          # refresh the copies
scripts/sync-chart-files.sh --check  # fail if they drifted (for CI)
```

A stale overrides copy is the dangerous one here: it would present
`startTaskExecution` to a model as an ordinary reversible write.
