# Worked example: FuzeFront plans itself via FuzePlan

This is the scenario A2A exists to make true (README.md "What A2A is for"):

> A FuzeFront workstream needs a delivery plan and Jira tickets. The agent doing the
> asking holds **no Atlassian MCP and no Jira skill**. It hands one goal to the
> **FuzePlan** agent — which owns the planning skill, the Atlassian MCP, and the
> credentials — and FuzePlan produces the plan and the tickets.

If the caller ever needs Jira knowledge of its own, the design has failed. That
*encapsulation invariant* is the whole point.

---

## The actors

| Actor | Role in the flow |
|---|---|
| **FuzeFront-context agent** | A Managed-Agents role running on **FuzeAgent's runtime**. It knows FuzeFront's goal; it knows nothing about Jira. |
| **handoff MCP** | The **client** side of A2A. The agent calls `ask_agent`/`spawn_agent`; the MCP resolves the target card and speaks the wire for it. It is a thin transport, not a second brain. |
| **shared A2A server** | The one family server (`a2a-shared.fuzeagent.svc.cluster.local:8080`). It serves **each tenant's** card and dispatches `SendMessage` into that tenant's role. FuzePlan is one tenant. |
| **FuzePlan planning role** | FuzePlan's serving role (the `product-manager` skill in [`examples/fuzeplan.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/fuzeplan.agent-card.json)). Owns the Atlassian MCP + Jira credentials. |
| **Authentik** | Mints the caller's OIDC token carrying `repo=FuzeFront`, `aud=a2a` (see [go-live-checklist.md](go-live-checklist.md)). |

There is **no** separate "FuzePlan deployment" — the same shared server serves FuzePlan
because FuzePlan is listed as a `tenants` entry (enable-your-pod.md). "FuzeAgent
discovers FuzePlan" means the FuzeFront agent, hosted on FuzeAgent's runtime, resolves
FuzePlan's card through that shared server and the discovery registry.

---

## The flow

1. **A FuzeFront goal arrives.** A FuzeFront-context agent on the FuzeAgent runtime
   needs a plan for a feature.
2. **It asks, it doesn't do.** The agent calls the handoff MCP:
   `ask_agent(target="FuzePlan", goal="Produce a delivery plan + Jira epics/stories for <feature>")`.
   It passes **only a goal** — no Jira project, no board, no credentials.
3. **Discover FuzePlan's card.** The A2A client resolves the target from the discovery
   registry → the shared server, and fetches
   `GET {base}/.well-known/agent-card.json` (tenant `FuzePlan`). The card advertises the
   `product-manager` skill and the `fuze-oidc` scheme (call-another-agent.md §1).
4. **Get a caller token.** The client presents an Authentik OIDC access token whose
   validated claims are `repo=FuzeFront`, `aud=a2a`. The callee trusts **only** that
   token for identity — never anything in the request body (authz.md §2).
5. **AuthZ is enforced by FuzePlan.** FuzePlan's `.fuze/manifest.json` `providesTo`
   must contain `FuzeFront`. It already does — FuzePlan's `providesTo` lists the whole
   family. Absent/empty would be DENY, indistinguishable from "not found" (authz.md
   §3/§6).
6. **`SendMessage`.** The client sends the goal to the shared server with the `FuzePlan`
   tenant echoed (binding.md). The server dispatches it into FuzePlan's planning role.
7. **FuzePlan does the work with its own credentials.** The planning role uses
   **FuzePlan's** Atlassian MCP + Jira creds to create the epics/stories. The FuzeFront
   agent is not in this loop and holds none of it.
8. **Tickets come back as artifacts.** Created ticket keys/links are returned as
   `Task.artifacts` on the completed task (state-mapping.md); the FuzeFront agent reads
   them and proceeds with its work.

If FuzePlan needs a decision it can't make (e.g. which board, or approval to create),
it pauses to `INPUT_REQUIRED`/`AUTH_REQUIRED` and the caller resolves it via
`reach_human` — it does **not** guess (state-mapping.md §4).

---

## What this depends on being in place

| Dependency | State |
|---|---|
| FuzeAgent shared A2A server live | ✅ live in prod (serves the signed card) |
| FuzePlan `providesTo` ⊇ `FuzeFront` | ✅ already declared |
| FuzePlan **serving role** (`agent-templates/roles/product-manager/`) | ⛔ **gap** — FuzePlan has no serving role yet, so its card can't project. This is FuzePlan product work + real Atlassian creds. |
| FuzePlan **tenant** in the shared server's values | ⛔ **gap** — a `tenants` entry (kept `enabled:false` until the serving role ships). |
| handoff MCP + discovery registry **deployed** | ⛔ **gap** — the client exists in `agent-templates/orchestration/handoff_mcp/` but isn't running in prod yet. |
| FuzeFront **caller identity** registered in Authentik | ⛔ **gap** — run `register-a2a-cli FuzeFront` (go-live-checklist.md) so step 4's token exists. |

The mesh is real and FuzeAgent is on it; wiring FuzePlan onto it is the above four
steps, three of which are pure deployment/data and one (the planning role) is FuzePlan
product work.
