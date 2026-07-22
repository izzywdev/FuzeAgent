# Card generation projection (NORMATIVE)

**Agent Cards are DERIVED. Hand-writing or hand-editing a published card is a contract violation.**

The card is a pure function of two inputs already present in every repo:

```
.fuze/manifest.json                 -> identity, provider, interfaces, authZ allowlist
agent-templates/roles/*/role.json   -> skills
                                    -> AgentCard  (/.well-known/agent-card.json)
```

Purity matters for a specific reason: the card is the *published capability boundary*. If it can
drift from the role manifests, the callee can advertise a skill it cannot serve, or serve a skill it
never advertised — and the whole encapsulation property (§7) collapses. A generator that reads only
these two files, deterministically, is what keeps the card honest.

Determinism requirement: the generator MUST be a pure function of the two inputs — same inputs, byte-identical
card (modulo `signatures`). Iteration order MUST be explicit (see §3), never filesystem order.

---

## 1. Identity and provider

| Card field | Source | Rule |
|---|---|---|
| `name` | `manifest.repo` + serving tier | `"<RepoName> agent"` for product/infra; `"<RepoName> <role> agent"` when the card serves a single exec role (§5). `<RepoName>` is the segment after `/`. |
| `description` | `manifest.repo`, `manifest.expert`, serving roles | Composed sentence naming what the repo's agent does and that it holds its own tools/credentials. MUST NOT enumerate MCP servers, vault ids, or credential names — see §7. |
| `provider.organization` | constant | `"FuzeOne"` |
| `provider.url` | constant | `"https://github.com/izzywdev"` |
| `version` | `agent-templates/contracts/a2a/v1/VERSION` + repo role-set hash | SemVer of the *agent*, bumped when the projected skill set changes. |
| `documentationUrl` | `manifest.a2a.documentationUrl` | Default `https://github.com/<manifest.repo>` |
| `iconUrl` | `manifest.a2a.iconUrl` | Omitted if unset. |

## 2. Interfaces

Exactly one interface in v1 (profile-enforced):

| Field | Value |
|---|---|
| `url` | in-cluster: `http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc`<br>external (`manifest.a2a.external: true`): `https://a2a.<repo-slug>.prod.fuzefront.com/rpc` |
| `protocolBinding` | `"JSONRPC"` |
| `protocolVersion` | `"1.0"` |
| `tenant` | `<RepoName>` — the repo name segment. |

`tenant` is what makes ONE shared server able to front twenty product agents: every card points at the
same URL and is disambiguated by `tenant`, which the client MUST echo per A2A §4.4.6. This is the
mechanism that makes decision #2 ("one shared A2A server, not 20 implementations") expressible in
the standard rather than as a Fuze deviation.

## 3. Skills — the core of the projection

**Source set.** `manifest.a2a.servingRoles` if present; otherwise every directory under
`agent-templates/roles/` **except**:

- `_base` (a template, not a role), and
- any role with `coordinator: true` (routing machinery, not a callable capability), and
- any role with `a2a.publish: false`.

Roles are emitted in `servingRoles` order when given, otherwise **lexicographic by role key** — never
filesystem enumeration order, which is not stable across platforms.

**Per-role field mapping:**

| `AgentSkill` field | Source in `role.json` | Rule |
|---|---|---|
| `id` | `role` | Verbatim. **This is the join key** — the adapter resolves an incoming skill id back to the role manifest to pick the agent to run. It MUST match `^[a-z0-9_-]+$`, which the existing role schema already enforces. |
| `name` | `name` | Verbatim (already human-readable, e.g. `"FuzeInfra backend-engineer"`). |
| `description` | `description` | Verbatim. If absent, the projection MUST FAIL rather than emit a placeholder — an undescribed skill is unroutable, and silently shipping one is worse than a build error. |
| `tags` | derived + `a2a.tags` | Derived set (always included): the role key; `manifest.tier`; `"executive"` if `metadata.tier == "executive"`; each `services` key whose grant is not `"none"` (e.g. `github`, `k8s`). Union with `a2a.tags`, de-duplicated, sorted. |
| `examples` | `a2a.examples` | Omitted if unset. Generator SHOULD warn — see role-a2a-extension rationale. |
| `inputModes` / `outputModes` | `a2a.inputModes` / `a2a.outputModes` | Omitted if unset (card defaults apply). |
| `securityRequirements` | `a2a.scopes` | `[{ "fuze-oidc": [<scopes>] }]` if scopes set; omitted otherwise (card-level requirement applies). |

**Explicitly NOT projected** — and this is deliberate, not an oversight:
`tools`, `mcp_servers`, `system`, `system_append`, `persona`, `model`, `environment`, `vault`
bindings. These are exactly the things that must stay on the callee's side. A card that leaked
`mcp_servers` would tell a caller which credentials the callee holds, and would invite callers to
reason about the callee's tools instead of its outcomes — reintroducing the coupling A2A removes.

## 4. Capabilities, modes, security

| Field | Value | Why |
|---|---|---|
| `capabilities.streaming` | `true` | The Managed-Agents driver already holds an SSE stream; exposing it costs nothing. |
| `capabilities.pushNotifications` | `false` | No webhook egress path is frozen in v1. Callers use `SubscribeToTask` or poll `GetTask`. |
| `capabilities.extendedAgentCard` | `true` | Required by the split-visibility model (§5 of authz.md). |
| `defaultInputModes` | `["text/plain", "application/json"]` | |
| `defaultOutputModes` | `["text/plain", "application/json"]` | |
| `securitySchemes` | `{"fuze-oidc": {"openIdConnectSecurityScheme": {"openIdConnectUrl": "<issuer>/.well-known/openid-configuration"}}}` plus `{"fuze-mtls": {"mtlsSecurityScheme": {}}}` when `a2a.external` is false | |
| `securityRequirements` | `[{"fuze-oidc": []}]` | |

## 5. Exec-tier roles

Exec roles (`ceo`, `cto`, `cfo`, `ciso`) are **not a special case in the protocol** — they project
through the same rules. What differs is where they live and how they are gated. This is what makes
"escalate this architecture decision to the CTO" reachable by an agent rather than only by a human.

An exec card is produced when either:

- `manifest.tier == "exec"`, or
- the role manifest sets `metadata.tier == "executive"` (the discriminator already used by
  `FuzeInfra/agent-templates/roles/{ceo,cto,cfo,ciso}/role.json`).

Deltas from the product projection:

1. **One card per exec role, not one per repo.** Each exec role gets its own card and its own
   `tenant` (`Exec-<role>`, e.g. `Exec-cto`), so `dependsOn: ["Exec-cto"]` is an expressible and
   auditable grant. Bundling four exec roles into one card would make "may escalate to the CTO"
   indistinguishable from "may instruct the CFO".
2. **`name`** = `"FuzeOne <ROLE> agent"` (e.g. `"FuzeOne CTO agent"`), from `role.name`.
3. **Tags** always include `"executive"` and the role key.
4. **`a2a.external`** MUST be `false`. Exec agents are in-cluster only; there is no tunnel-published
   exec surface in v1.
5. **Allowlist default is deny-all-but-declared.** Exec `providesTo` is expected to be broad for
   *escalation* skills and empty for *directive* skills — expressed with per-skill
   `a2a.scopes` rather than by widening the card.
6. **`reach_human` is the expected terminal step.** An exec agent asked for a binding decision will
   commonly pause to `reach_human` its digital persona; callers MUST therefore be prepared for
   `TASK_STATE_INPUT_REQUIRED` with a long dwell time (see state-mapping.md §4). An exec escalation
   that returns instantly is more suspicious than one that blocks.

## 6. Signing

The generator canonicalizes the card (RFC 8785 JCS) **excluding** `signatures`, then emits a JWS
per A2A §8.4 into `signatures[]`. Key material and rotation are a devops concern and out of scope
for this contract; the contract fixes only that the field is REQUIRED and non-empty in the Fuze
profile.

## 7. The encapsulation invariant (the property this whole contract exists to preserve)

> A caller learns **what a callee can accomplish**. It never learns **how**, and never acquires the
> means.

Concretely, the projection guarantees:

- A card contains **no** credential, vault id, MCP server URL, or tool name.
- A caller needs **no** skill, MCP server, or secret belonging to the callee's domain.
- The worked example holds: a requirements-discussion agent with **no Atlassian MCP and no Jira
  skill** sends `SendMessage` to the FuzePlan agent naming skill `product-manager`, and FuzePlan —
  which owns the Jira skill, the Atlassian MCP and the credentials — creates the tickets and returns
  artifacts.

Any future projection change MUST be checked against this invariant. If a proposed field would let a
caller infer the callee's toolset, it does not go on the card.
