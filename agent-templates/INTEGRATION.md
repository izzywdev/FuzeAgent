# Integration status — this module vs `services/orchestrator/`

**This port is additive and NOT wired into the existing services.** It was landed as a
self-contained module so the runtime exists in its destination repo without disturbing
FuzeAgent's in-flight work. The architectural reconciliation below is a deliberate,
reviewed follow-up — not something to merge blind.

## The overlap (why this needs a decision, not a merge)

FuzeAgent already implements agent orchestration in `services/orchestrator/`:

| Concern | `services/orchestrator/` (existing) | `agent-templates/` (ported) |
|---|---|---|
| agent-to-agent messaging | `a2a_protocol.py` | handoff MCP: `spawn_agent` / `ask_agent` / `resume_session` |
| agent lifecycle | `agent_manager.py`, `container_manager.py` | provider `create_session` + managed environments |
| agent definitions | `agent_templates.py` | `roles/*/role.json` + persona `.md` (+ `_base` inheritance) |
| model/runtime binding | `claude_sdk_manager.py`, `claude_code_wrapper.py` | `providers/` seam (anthropic ref; openai/hermes stubs) |
| durable context | `context_service.py`, `conversation_manager.py` | managed-agents memory store + session-resume |

These are two answers to the same question. They should not both run.

## The substantive difference

The ported module is built on the **provider's managed-agents API**: sessions are persistent
**server-side**, so a waiting agent idles at zero cost and resumes without replaying history,
and access is a property of a **declared environment** (fixed at definition time, credential-
scoped via vaults) rather than negotiated per-call. `services/orchestrator/` manages
containers and conversation state itself. The trade is control vs. not operating that plane.

## Options (for the owner to decide)

1. **Adopt the managed-agents plane** — `services/orchestrator/` becomes a thin façade over
   `providers/` + the handoff MCP; drop bespoke container/session management. Most leverage,
   biggest change.
2. **Keep both, bounded** — the handoff MCP serves *cross-repo/cross-environment* handoff
   (its real strength: org-global agent namespace), `services/orchestrator/` keeps in-product
   agents. Requires one clear boundary rule, or drift is guaranteed.
3. **Reject the port** — keep FuzeAgent's own orchestration; FuzeInfra's roles then need a
   different home for the handoff MCP. (Then delete this module rather than let it rot.)

## What is safe about landing this now

- Nothing imports it; no existing service changed. The only wiring is an **opt-in**
  `handoff-mcp` compose service (does not start with the default `docker compose up`
  of other services; it has no `depends_on` from them).
- The framework files (`schema/`, `roles/_base/`, `sync/`, `providers/`) are copies of the
  FuzeSDLC canonical and are reconciled by `governance-sync` — change them **there**.
- No concrete roles/environments/vaults were ported: those are FuzeInfra's own definitions.
  FuzeAgent declares its own if/when it adopts this plane (`managed-agents-roles` skill).
