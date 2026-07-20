# agent-templates — Managed-Agents orchestration runtime (ported from FuzeInfra)

The **agent-orchestration runtime**: role definitions projected onto a provider's
managed-agents API, cross-session **handoff** (spawn / ask / resume / reach_human), a shared
memory store, and a self-hosted worker that runs privileged tools inside our network.

Prototyped in FuzeInfra (which had the richest cluster-capable example); this is its
destination — FuzeAgent is the agent product, so application-level agent orchestration
belongs here, not in the shared infra repo.

> **Not yet integrated with `services/orchestrator/`.** This landed as a self-contained,
> additive module. FuzeAgent already has its own orchestration (`a2a_protocol`,
> `agent_manager`, `claude_sdk_manager`). Reconciling the two is a deliberate follow-up —
> see [INTEGRATION.md](INTEGRATION.md). Nothing here is wired into the existing services.

## The three-way split (org-wide)

| Layer | Home | What |
|---|---|---|
| **Framework / pattern** | **FuzeSDLC** (canonical) | `schema/`, `roles/_base/`, `sync/`, `providers/` — reconciled into each repo by `governance-sync` |
| **Concrete definitions** | **each repo** | its own `roles/`, `environments/`, `vaults/`, `coordinator/` — declared in `.fuze/manifest.json` `roles` |
| **Orchestration runtime** | **FuzeAgent** (here) | `orchestration/` (handoff MCP + relay), `worker/`, and the deployed services |

The framework files here are copies of the FuzeSDLC canonical — change them **there**, not
here; `governance-sync` reconciles this repo's copies on its next PR.

## Layout

| Path | What |
|---|---|
| `orchestration/handoff_mcp/` | the handoff MCP server (`spawn_agent`/`ask_agent`/`resume_session`/`reach_human`/memory), its Dockerfile + k8s manifests |
| `orchestration/relay.py` | deterministic session-resume / memory hand-forward relay |
| `worker/` | self-hosted worker image + destructive-verb guard shims + k8s deploy |
| `providers/` | provider seam: `base.py`, registry, `anthropic/` (ref) + `openai`/`hermes` stubs, `provision.py` |
| `sync/` | stdlib REST client, session driver, manifest loader, validate, launch |
| `schema/`, `roles/_base/` | manifest schemas + the shared guardrail role |

## Run the handoff MCP locally

```bash
docker compose up handoff-mcp     # serves streamable-HTTP MCP at http://localhost:8010/mcp
```

It needs `ANTHROPIC_API_KEY`, a bearer `HANDOFF_MCP_TOKEN` (unauthenticated without it — it
warns loudly), and the provisioned **id state** in `/state` (`agent-ids.json`,
`vault-ids.json`, `memory-ids.json`). That state is produced by `provision.py` (CI publishes
it as an artifact / ConfigMap) — ids are not secrets. Point each role's `HANDOFF_MCP_URL` at
this service.

## Why the handoff MCP exists

Agents hand work off by **session-resume**, never by copying transcripts: the originating
session already holds its history server-side, so a callee returns only a concise summary (or
a `context_ref` pointer into the shared memory store). A waiting session goes idle at **no
cost** and resumes cleanly. `reach_human` bridges an `always_ask` pause to a person's digital
persona across their real channels instead of stalling.
