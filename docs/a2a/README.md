# A2A integration guide

How a FuzeOne product joins the **agent-to-agent (A2A)** mesh: how to make your
product's agent reachable, and how to hand a goal to another product's agent.

These pages are **integration docs only** — the how-to for product and platform
owners. They document what the **frozen v1 contract** already defines. The contract
itself is the source of truth and is never restated here in full; every claim below
links back to it:

- [`contracts/a2a/v1/README.md`](../../agent-templates/contracts/a2a/v1/README.md) — what A2A is for, the five common mistakes, caller quick-start.
- [`binding.md`](../../agent-templates/contracts/a2a/v1/binding.md) — JSON-RPC 2.0 over HTTP + SSE; methods, errors, transport.
- [`card-projection.md`](../../agent-templates/contracts/a2a/v1/card-projection.md) — how an Agent Card is derived from your manifest + roles.
- [`authz.md`](../../agent-templates/contracts/a2a/v1/authz.md) — callee enforces, allowlist is `providesTo`, absent = DENY.
- [`state-mapping.md`](../../agent-templates/contracts/a2a/v1/state-mapping.md) — task states, `INPUT_REQUIRED`/`AUTH_REQUIRED`, `reach_human`.
- [`values-interface.schema.json`](../../agent-templates/contracts/a2a/v1/schema/values-interface.schema.json) — the Helm values interface you set to be served.

> **Contract version:** v1.0.0, frozen against A2A specification 1.0.0. If something
> below looks wrong, the contract wins — file it, don't work around it.

## The pages

| Page | Read it when you want to… |
|---|---|
| [enable-your-pod.md](enable-your-pod.md) | Make your product (or an exec role) reachable over A2A — the values you set, the `enabled` gate, and the precondition you must satisfy first. |
| [call-another-agent.md](call-another-agent.md) | Hand a goal to another product's agent — resolve its card, `SendMessage`, and handle `INPUT_REQUIRED`/`AUTH_REQUIRED` coming back. |
| [mcp-pod-vs-a2a-pod.md](mcp-pod-vs-a2a-pod.md) | Decide whether you want a tool surface (MCP) or an agent surface (A2A) — and why exec roles get A2A pods. |
| [authz-for-integrators.md](authz-for-integrators.md) | Understand who is allowed to call whom, and why "it just returns not-found" is the intended behaviour. |

## What is NOT in these docs (owned elsewhere)

The A2A server/adapter (backend-engineer), its Helm chart and Argo Application and
image (devops-engineer), the behaviour/contract tests (test-engineer), and the MCP
client (mcp-engineer) are separate slices. This guide describes the operator- and
integrator-facing contract; it does not document server internals that are still being
built. Where a detail depends on the adapter, the page cites the contract's normative
statement rather than a running implementation.
