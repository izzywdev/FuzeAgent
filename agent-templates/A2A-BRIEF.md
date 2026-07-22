# Initiation prompt — A2A contract for the Fuze family

> Paste everything below the line into a fresh Claude Code session started in `D:\source\FuzeAgent`.
> It is self-contained: it assumes no memory of the session that produced it.

---

You are the **contract-designer** for a new capability in the Fuze/Mendys family. Your job this
session is to produce **ONE contract PR and nothing else**. Do not implement anything.

## The goal (why this exists)

Every product in the family will run, in prod, **two pods**:

- an **MCP pod** (already the pattern; owned by `mcp-engineer`) — the product's **tool surface**:
  *"here are my functions; you call them, you orchestrate, you hold the creds."*
- an **A2A pod** (what you are designing) — the product's **agent surface**:
  *"here is a goal; my agent figures it out."*

The distinction is the whole point and you must preserve it. Worked example from the owner:

> *A requirements-discussion chat needs Jira tickets created. It must NOT have the Atlassian MCP,
> and must NOT have a Jira skill. It simply asks the **FuzePlan agent** over A2A: "make tickets for
> this." FuzePlan's agent — which already owns the Jira skill, the Atlassian MCP, and the
> credentials — does it.*

That is **capability + credential encapsulation**. Any product can ask any other product's agent to
do work, during work, without acquiring that product's tools, knowledge, or secrets. This is stated
by the owner to be **the main purpose of FuzeAgent**.

## Decisions ALREADY MADE (do not relitigate)

1. **Adopt the OPEN A2A standard** (a2a-protocol.org — Linux Foundation), not a bespoke protocol.
   Spec: Agent Card at a well-known endpoint · bindings JSON-RPC 2.0 / gRPC / HTTP+REST ·
   methods `SendMessage` / `SendStreamingMessage` / `GetTask` / `ListTasks` / `SubscribeToTask` /
   `CancelTask` / push-notification config / `GetExtendedAgentCard` · task states
   `SUBMITTED · WORKING · COMPLETED · FAILED · CANCELED · REJECTED · INPUT_REQUIRED · AUTH_REQUIRED` ·
   security schemes API-Key / HTTP / OAuth2 / OIDC / mTLS. **Verify the current spec yourself before
   freezing** — do not trust this summary as normative.
2. **ONE shared A2A server, owned by FuzeAgent** — NOT 20 per-product implementations. Products
   *declare* an Agent Card and enable a chart; they do not implement the protocol. (20 bespoke pods
   = 20 chances to get authN wrong; A2A's own guidance makes the **callee** responsible for authZ.)
3. **It lives in FuzeAgent**, beside `agent-templates/orchestration/`. The runtime port already
   landed there (PR #49, `1b5dfc9`).
4. **A2A is the wire; Managed Agents is the execution runtime.** The pod is a thin **adapter**, not
   a new engine.

## The load-bearing insight — reuse, don't rebuild

`agent-templates/providers/base.py` (already in FuzeAgent `main`) is an abstract `AgentProvider`
with exactly the primitives A2A needs:

```
create_session(agent_id, version, environment_id, vault_ids, memory_resources, title)
send_message(session_id, text)
run_turn(session_id, prompt, approver)
run_until_block(session_id, prompt)   -> {'text', 'status': idle|blocked|error, 'pending': {...}|None}
resume_session(session_id, summary, context_ref)
confirm_tool(session_id, tool_use_id, allow, deny_message)
archive_session(session_id)
```

The mapping is unusually tight — **specify it exactly, in the contract**:

| A2A | Managed Agents (existing) |
|---|---|
| `SendMessage` / `SendStreamingMessage` | `create_session(role, env)` → `run_until_block` (stream via the SSE the driver already opens) |
| task `COMPLETED` | `run_until_block` → `status: idle` |
| task `FAILED` | `status: error` |
| **`INPUT_REQUIRED` / `AUTH_REQUIRED`** | **`status: blocked` + `pending`** — i.e. an `always_ask` permission pause. **`reach_human` (handoff MCP) is already the mechanism that satisfies it** |
| `GetTask` / `SubscribeToTask` | session id ↔ task id; sessions persist server-side |
| resume after input | `resume_session(session_id, summary)` — **never** replays transcripts |
| `CancelTask` | `archive_session` |

Nothing new is needed for execution. If you find yourself designing a task engine, stop — you have
missed this.

## What the contract must define (the deliverable)

1. **Agent Card** — JSON Schema + the well-known path. Fields: identity/provider, capabilities
   (`streaming`, `pushNotifications`), **skills**, securitySchemes, interfaces, signature.
2. **Card generation** — the card is **derived, not hand-written**: `skills` come from the repo's
   `agent-templates/roles/*/role.json`; identity/provider from `.fuze/manifest.json`. Specify the
   projection precisely (which manifest/role fields → which card fields).
3. **The binding** — JSON-RPC 2.0 over HTTP + SSE streaming is the baseline; say explicitly whether
   gRPC/REST are in or out of v1.
4. **The state mapping** — the table above, normatively, incl. how an `always_ask` pause surfaces as
   `INPUT_REQUIRED`/`AUTH_REQUIRED` and how `reach_human` resolves it.
5. **AuthZ model** — **the callee enforces; the caller is opaque and untrusted.** The allowlist
   already exists in SHAPE: **`dependsOn` / `providesTo` in `.fuze/manifest.json`** — but it is **NOT yet populated fleet-wide.** Verified 2026-07-21: present on only **5 of 20** repos (FuzeBI, FuzeContact, FuzeExecutive, FuzeSales, FuzeService); absent on FuzeAgent, FuzeInfra, FuzeFront, FuzeKeys, FuzePlan, FuzeCall, FuzeDeploy, FuzeHub, FuzeMarket, FuzeMerchandize, FuzePicker, FuzeSocial, FuzeX, MendysRobotics, MendysRoboticsWP. An earlier revision of this brief wrongly claimed "live on all 20 repos" — do not rely on it.
   **Therefore: absence MUST deny, never allow.** A permissive default would expose every un-backfilled repo to every caller the moment A2A is enabled. Backfilling the graph is a PRECONDITION of enabling A2A authZ, not a follow-up.
   Specify identity (FuzeKeys / OIDC / mTLS per A2A securitySchemes), and that in-cluster service
   DNS is the transport (CF Access only if a surface is external).
6. **The shared server's interface** — the Helm values contract each product sets (`enabled` gate,
   which role serves the card, env/vault binding). Config, not code.
7. **Event/async surface** if any (AsyncAPI/Zod), per baseline §4.
8. **Version + changelog** (SemVer; `governance/versioning.md`).

## HARD RULES — read these before you touch a file

- **The contract PR contains the contract and NOTHING ELSE.** This was just made explicit policy
  (FuzeSDLC PR #45; baseline §4 + `skills/api-contract-first` + `agents/contract-designer.md`).
  Permitted: spec/schemas · the **generated** typed client · approved UI frames + mock config ·
  version bump/changelog. **Forbidden in this PR:** the server implementation, handlers, Helm/Argo,
  tests of behaviour, drive-by fixes. Verify before opening:
  `git diff --name-only origin/main...HEAD` must list only contract-set files.
  Rationale: the contract PR is a **gate**; a gate carrying implementation cannot be reviewed *as* a
  gate — the interface gets waved through while implementation rides along unexamined.
- **Your merged PR is the hard precondition for EVERY implementer stream:** `backend-engineer`,
  `database-engineer`, `frontend-engineer`, `test-engineer`, `frontend-test-engineer`,
  `devops-engineer`, `mcp-engineer`, `cli-engineer`, `mobile-app-engineer`, `desktop-app-engineer`,
  `docs-maintainer`. None of them start until it is merged. Do not fan out yourself — return the
  merged contract and let the orchestrator fan out.
- **Load the `api-contract-first` skill** and follow it. Consult **`fuzeagent-expert`** for repo
  context (baseline §2: consult the expert, do not read another product's source).
- Do **not** enter plan mode / brainstorm inside an agent run. If blocked on a genuine product
  decision, push what you have and return `BLOCKED: <question>`.
- Report the done-contract honestly: `SCOPE DONE (verified): …` + `OUT OF SCOPE — NOT DONE: …`.
  Never call the *feature* done — you own the contract slice only.

## Landmines (each of these has already bitten this codebase)

- **`services/orchestrator/a2a_protocol.py` (794 lines) already exists in FuzeAgent and is a
  DECOY.** It has the right *concepts* (`AgentCard`, `A2ATask`, registry, Postgres task tables) but
  **no `jsonrpc`, no `/.well-known/`** — it is bespoke and shares only the *name* with the standard.
  It will not interoperate with any A2A client/SDK. Read it for concepts; do **not** treat it as the
  protocol, and do not assume "A2A" in this repo means the standard. Reconciling it is a follow-up
  (see `agent-templates/INTEGRATION.md`), **not** your contract PR.
- **FuzeAgent's CI is RED on `main`** and not your fault: flake8 `F821` (undefined `HTTPException`
  in `agent_manager.py`; `DatabaseManager` in `hierarchy_endpoints.py`), `test-backend` fails on
  `TypeError: 'Connection' object does not support the asynchronous context manager protocol`, and
  12/13 frontend integration tests fail. **14 rival `claude-auto-fix-ci` PRs are open** attacking
  the same breakage. Do not try to fix it inside your contract PR (that would violate contract-only).
- **The repo has ~65 uncommitted files** from another session's in-flight work. **Use a git worktree
  off `main`**; never touch that checkout. (`git worktree add <path> -b feat/a2a-contract main`.)
- **`gh pr` commands are GraphQL and fail SILENTLY at the rate limit** — they return empty instead of
  erroring, which already caused a script to report "NO-PR" for 18 PRs that existed. Prefer
  `gh api` (REST, separate quota): `gh api -X POST repos/izzywdev/FuzeAgent/pulls --input body.json`.
- Windows/git-bash: don't pass MSYS `/tmp/...` paths to Windows Python; stale `.git/**/*.lock`
  (including `refs/heads/main.lock`, at depth 3) blocks ref updates after a timed-out git op.
- **Verify, don't trust.** Confirm the remote SHA and the PR via the API before reporting done —
  a prior run in this family reported a PR number that did not exist.

## Context you may need

- **FuzeSDLC** is the L0 standard hub (private). Repos pin `baselineRef: v1` — a **moving major tag**
  (`v1` = `v1.0.0` = `87f9ad3`). Policy: `governance/versioning.md` §5, `governance/agent-ownership.md`.
- `governance-sync` reconciles managed files on every PR (currently **skipping** fleet-wide until
  `FUZESDLC_DEPLOY_KEY` is distributed — that is expected, not a bug).
- FuzeAgent `main` already has: `agent-templates/{orchestration,providers,sync,worker,schema,roles}`
  + an opt-in `handoff-mcp` compose service on `:8010`.
- The handoff MCP (`ask_agent`/`spawn_agent`/`resume_session`/`reach_human`) is the intended
  **client** side: dev agents keep calling `ask_agent`; A2A becomes the transport underneath.

## Definition of done for THIS session

A single **contract-only PR** open on FuzeAgent containing: the Agent Card schema + well-known path,
the JSON-RPC/SSE binding, the normative A2A↔Managed-Agents state mapping, the card-generation
projection from `.fuze/manifest.json` + `agent-templates/roles/`, the authZ model
(`dependsOn`/`providesTo` allowlist, callee-enforced), the shared-server values interface, the
generated client, Spectral-clean, versioned — and **`git diff --name-only` proving no implementation
file is in it**. Then report `SCOPE DONE (verified)` with the PR URL confirmed via the API, and
`OUT OF SCOPE — NOT DONE:` naming the streams that gate on you.
