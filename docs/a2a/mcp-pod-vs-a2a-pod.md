# MCP pod vs A2A pod

A product can expose **two** surfaces in prod, and they answer two different questions.
They are **complementary, not competing** — most products will run both.

| | **MCP pod** | **A2A pod** |
|---|---|---|
| Offers | *tools* — "call my functions" | *agency* — "here is a goal" |
| The caller says | "run this function with these arguments" | "accomplish this outcome" |
| Who holds the credentials | **the caller** holds the tools + credentials | **nothing** — the callee holds them |
| Who orchestrates | the **caller** | the **callee** |
| Analogy | a library / SDK you drive | a colleague you delegate to |

(Source: [`contracts/a2a/v1/README.md`](../../agent-templates/contracts/a2a/v1/README.md),
"What A2A is for".)

---

## The distinction, concretely

**MCP pod = tool surface.** You call a specific function and you supply the inputs — and
you must hold whatever credentials that function needs. You are the orchestrator: you
decide the sequence of calls, handle intermediate results, and drive to the outcome. The
credentials and the reasoning live on **your** side.

**A2A pod = agent surface.** You hand over a **goal** and the callee's agent figures out
how to accomplish it, using **its own** tools, skills, and credentials. You hold none of
them. The orchestration lives on the **callee's** side.

The worked example (README.md):

> A requirements-discussion agent needs Jira tickets. It holds **no Atlassian MCP and no
> Jira skill**. It sends one A2A message to the **FuzePlan** agent — which owns the Jira
> skill, the Atlassian MCP and the credentials — and FuzePlan creates them.

- With **MCP**, the discussion agent would need the Atlassian MCP server wired in and
  Jira credentials in its own environment, then make the create-ticket calls itself.
- With **A2A**, it needs none of that. It states the goal; FuzePlan's agent does the rest.

---

## Why this is the point: the encapsulation invariant

A2A exists to preserve one property (card-projection.md §7):

> A caller learns **what a callee can accomplish**. It never learns **how**, and never
> acquires the means.

This is why an Agent Card **never** carries credentials, vault ids, MCP server URLs, or
tool names. The card projection deliberately does **not** emit `tools`, `mcp_servers`,
`system`, `persona`, `model`, `environment`, or `vault` bindings (card-projection.md §3,
§7). A card that leaked `mcp_servers` would tell a caller which credentials the callee
holds — reintroducing exactly the coupling A2A removes.

So the two surfaces sit on opposite sides of the credential boundary:

- **MCP** hands the caller the tools (and expects it to hold the credentials to use them).
- **A2A** keeps the tools and credentials entirely on the callee and hands the caller only
  an outcome.

That is **capability + credential encapsulation** — the property every A2A rule is
downstream of.

---

## When to offer which

- Offer an **MCP pod** when consumers legitimately want to drive your functions
  themselves and can hold the relevant credentials — a tool/SDK integration.
- Offer an **A2A pod** when consumers want an outcome without taking on your domain's
  tools or secrets — delegation.
- Offering **both** is normal: "every product runs two surfaces in prod" (README.md).
  They do not compete; a caller picks the one that matches what it wants (a function call
  vs. a delegated goal).

> The MCP surface is owned by **mcp-engineer**; the A2A server/adapter by
> **backend-engineer**; the chart/image by **devops-engineer**. This page explains the
> *distinction* for integrators — it does not document either implementation.

---

## Exec-tier roles get A2A pods too

The exec roles — `cto`, `ceo`, `cfo`, `ciso` — also get **A2A pods**. This is what makes
"escalate this architecture decision to the CTO" an **agent-reachable** action rather than
a human-only one (card-projection.md §5).

An exec role is not a special case in the protocol — it projects through the same rules —
but:

- **One card per exec role**, each with its own `tenant` (`Exec-cto`, `Exec-cfo`, …), so
  a grant like "may escalate to the CTO" is distinct and auditable from "may instruct the
  CFO" (card-projection.md §5).
- Exec pods are **in-cluster only** (`external: false`) — there is no tunnel-published
  exec surface in v1 (card-projection.md §5).
- An exec agent asked for a **binding** decision commonly pauses on `reach_human` to the
  human's digital persona, so the calling agent should expect a long
  `TASK_STATE_INPUT_REQUIRED` dwell (card-projection.md §5, state-mapping.md §4). See
  [call-another-agent.md](call-another-agent.md) §3.

So the CTO becomes reachable **as an agent**: another agent delegates the architecture
question as a goal (A2A), and the CTO agent either rules on it or escalates to the human —
without the caller ever holding the CTO's tools or authority.

See [`examples/exec-cto.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/exec-cto.agent-card.json)
for the exec pod's projected card.
