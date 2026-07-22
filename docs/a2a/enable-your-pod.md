# Enable your A2A pod

Make your product's agent — or an exec role — reachable to other agents over A2A.

There is **one shared A2A server** for the whole family, not one deployment per
product. Onboarding your product is therefore **data, not a new chart**: you add a
`tenants` entry and flip a gate. This is fixed by the values interface
([`values-interface.schema.json`](../../agent-templates/contracts/a2a/v1/schema/values-interface.schema.json),
see its `description`) and by card-projection.md §2.

> The Helm chart, Argo Application, and image that consume these values are
> **devops-engineer's** slice. This page documents the **interface** you fill in, not
> the chart that renders it. The value names, types, and defaults below come straight
> from `values-interface.schema.json`.

---

## Precondition: backfill `providesTo` FIRST (not a follow-up)

**Before** you enable A2A on a repo, its `.fuze/manifest.json` must declare a
`providesTo` allowlist. This is a hard precondition, not a later cleanup.

The authorization model **fails closed**: an **absent** `providesTo` means DENY every
caller, and an empty `[]` also means DENY (authz.md §3, decision step 4). That is
deliberate — "unconfigured" must never mean "open to everyone." But it also means that
turning A2A on without a `providesTo` gives you an agent nobody can call.

At contract-freeze time `providesTo` was present on only 4 surveyed repos (FuzeBI,
FuzeExecutive, FuzeSales, FuzeService) and **absent** on the rest — including
FuzeAgent, FuzeInfra, FuzeFront, FuzePlan and others (authz.md §3). So for most repos,
adding `providesTo` is a real step you must do first.

```jsonc
// callee's .fuze/manifest.json — this file OWNS the grant
{
  "repo": "izzywdev/FuzePlan",
  "providesTo": ["FuzeSales", "FuzeService", "FuzeExecutive"],  // who may call you
  "dependsOn":  ["FuzeContact", "FuzeBI"]                       // advisory only
}
```

`providesTo` lives in the **callee's** file because the callee bears the risk of being
called. `dependsOn` in your own file grants you **nothing** — it is advisory (authz.md
§3). See [authz-for-integrators.md](authz-for-integrators.md) for the full rule.

---

## 1. The values you set

You configure the shared server once (server-level) and add one `tenants` entry per
served agent. All fields below are defined in
[`values-interface.schema.json`](../../agent-templates/contracts/a2a/v1/schema/values-interface.schema.json).

### Server-level (`a2a.*`)

| Value | Required | Default | Notes |
|---|---|---|---|
| `a2a.enabled` | yes | `false` | **The gate.** `false` = the shared A2A server is not deployed at all. |
| `a2a.protocolVersion` | — | `"1.0"` | Frozen for contract v1 (const). |
| `a2a.image.repository` | — | `ghcr.io/izzywdev/fuzeagent-a2a` | |
| `a2a.image.tag` | — | — | Immutable tag; prod values bump this, **never `latest`**. |
| `a2a.image.pullPolicy` | — | `IfNotPresent` | |
| `a2a.service.type` | — | `ClusterIP` (const) | **MUST be ClusterIP.** Ingress is Cloudflare-tunnel-only; there is no LoadBalancer/NodePort surface. |
| `a2a.service.port` | — | `8080` | |
| `a2a.auth.oidcIssuerUrl` | yes | — | Issuer whose discovery doc is projected into the card's `fuze-oidc` scheme. |
| `a2a.auth.audience` | — | — | Expected `aud` claim. |
| `a2a.auth.callerClaim` | — | `sub` | Token claim carrying the caller repo identity — **the only trusted caller identity** (authz.md §2). |
| `a2a.auth.mtls.enabled` | — | `false` | In-cluster mTLS as a second factor. |
| `a2a.auth.mtls.caSecretRef` | — | — | `{name, key}` reference to an existing Secret. |
| `a2a.cardSigning.keySecretRef` | yes | — | JWS signing key for the Agent Card. Required because the Fuze profile requires a non-empty `signatures[]`. |
| `a2a.cardSigning.keyId` | — | — | JWS `kid`. |

> **Secrets never go inline.** Every `*SecretRef` is `{name, key}` pointing at an
> existing Kubernetes Secret (SealedSecret-provisioned). Secret **values** never appear
> in `values.yaml` or in git (`values-interface.schema.json` `$defs.secretRef`).

### Per-tenant (`a2a.tenants[]`)

Each entry adds one served agent. Adding a product to A2A is **an entry here — never a
new deployment.**

| Value | Required | Default | Notes |
|---|---|---|---|
| `tenant` | yes | — | Routing key clients echo. MUST equal the card's `AgentInterface.tenant` (card-projection.md §2). Pattern `^[A-Za-z0-9_-]+$`. |
| `repo` | yes | — | `owner/name` whose `.fuze/manifest.json` + `agent-templates/roles/` are the card projection source. |
| `enabled` | yes | `false` | **Per-tenant gate**, independent of the server gate. |
| `ref` | — | `main` | Git ref the manifest/roles are read from — GitOps source of truth, never live-mutated. |
| `entryRole` | — | — | Overrides `manifest.a2a.entryRole`; the role that serves a `SendMessage` naming no skill. |
| `servingRoles` | — | — | Overrides `manifest.a2a.servingRoles`; the roles projected into the card's `skills`. |
| `external` | — | `false` | Publish through the Cloudflare tunnel with an `https://` interface URL. **MUST be `false` for exec-tier tenants.** |
| `provider.*` | — | see below | Managed-Agents runtime binding for this tenant's sessions. |
| `env[]` | — | — | Extra per-tenant session env; values MUST come from `secretRef`, never inline literals. |

**`provider` block** (values reaching `agent-templates/providers/*`):

| Value | Default | Notes |
|---|---|---|
| `provider.name` | `anthropic` | `AgentProvider` implementation id (`base.py name`). |
| `provider.environmentId` | — | Environment the sessions bind to; resolved from the role's `environment` when unset. |
| `provider.apiKeySecretRef` | — | `{name, key}` reference. |
| `provider.vaultIds[]` | — | Vault ids passed to `create_session`. **NEVER projected onto the card** (that is the encapsulation invariant — card-projection.md §7). |
| `provider.memoryResources[]` | — | Memory stores mounted into sessions (e.g. the shared handoff store). |

---

## 2. Two gates, both must be on

To actually serve a tenant, **both** gates must be `true`:

1. `a2a.enabled` — the shared server is deployed at all.
2. `a2a.tenants[<yours>].enabled` — your specific tenant is served.

This is the standard FuzeInfra/FuzeAgent `enabled`-gate convention, one level deeper so
the shared server can carry many tenants while individual ones stay dark.

---

## 3. Which role serves the card

Your card's `skills` are **derived**, not hand-written. The generator is a pure
function of `.fuze/manifest.json` + `agent-templates/roles/*/role.json`
(card-projection.md — "Agent Cards are DERIVED. Hand-writing a published card is a
contract violation").

- The **source set** of skills is `manifest.a2a.servingRoles` (or the `servingRoles`
  values override) if present; otherwise every directory under `agent-templates/roles/`
  **except** `_base`, any `coordinator: true` role, and any role with
  `a2a.publish: false` (card-projection.md §3).
- Each role's skill `id` is its `role` key **verbatim** — this is the join key the
  adapter uses to resolve an incoming `skill_id` back to a role (card-projection.md §3).
- A role's `description` is **required**; if it is absent the projection FAILS rather
  than shipping a placeholder (card-projection.md §3).
- The role that answers a `SendMessage` naming **no** skill is `entryRole`
  (`manifest.a2a.entryRole`, or the per-tenant `entryRole` override).

What is **never** projected onto the card: `tools`, `mcp_servers`, `system`, `persona`,
`model`, `environment`, and `vault` bindings (card-projection.md §3, §7). Those stay on
your side — that is the whole point (see
[mcp-pod-vs-a2a-pod.md](mcp-pod-vs-a2a-pod.md)).

See a real projected result: [`examples/fuzeplan.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/fuzeplan.agent-card.json).

---

## 4. Env / vault binding

Credentials and environment reach a tenant's **sessions**, never its card:

- `provider.apiKeySecretRef`, `provider.vaultIds`, and `env[].valueFrom` all resolve
  to existing Secrets — SealedSecret-provisioned, values never in git.
- The OIDC issuer (`a2a.auth.oidcIssuerUrl`) is what the callee validates every request
  against; the token claim named by `a2a.auth.callerClaim` (default `sub`) is the
  **only** trusted caller identity (authz.md §2). Network position grants nothing.
- `provider.vaultIds` and `memoryResources` are handed to `create_session`
  (state-mapping.md §2) — but are **explicitly not projected onto the card**
  (card-projection.md §3), preserving the encapsulation invariant.

---

## 5. Enabling an exec role (cto / ceo / cfo / ciso)

Exec roles are reachable over A2A too — that is what makes "escalate this architecture
decision to the CTO" an agent-callable action rather than a human-only one
(card-projection.md §5). They project through the **same** rules, with these deltas:

- **One card per exec role, not one per repo.** Each exec role gets its own `tenant`
  named `Exec-<role>` (e.g. `Exec-cto`), so a grant like `dependsOn: ["Exec-cto"]` is
  expressible and auditable. Bundling four exec roles into one card would make "may
  escalate to the CTO" indistinguishable from "may instruct the CFO."
- An exec card is produced when `manifest.tier == "exec"` **or** the role sets
  `metadata.tier == "executive"` (the discriminator already on
  `agent-templates/roles/{ceo,cto,cfo,ciso}/role.json`).
- **`external` MUST be `false`.** Exec agents are in-cluster only; there is no
  tunnel-published exec surface in v1.
- Expect exec tasks to pause on `reach_human` (see
  [call-another-agent.md](call-another-agent.md) and state-mapping.md §4).

See a real exec card: [`examples/exec-cto.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/exec-cto.agent-card.json).

---

## Checklist

1. [ ] `providesTo` present in the callee's `.fuze/manifest.json`, listing every allowed caller (precondition).
2. [ ] `a2a.enabled: true` (server gate).
3. [ ] A `tenants[]` entry with `tenant`, `repo`, and `enabled: true`.
4. [ ] `a2a.auth.oidcIssuerUrl` set; `a2a.cardSigning.keySecretRef` set.
5. [ ] `service.type` is `ClusterIP`; `external: false` for any exec tenant.
6. [ ] Every serving role has a non-empty `description` (else the card projection fails).
7. [ ] All secrets referenced via `secretRef`, never inline.

Everything lands through **GitOps** — commit to the tenant's `ref` (default `main`) and
let Argo sync; the values are the source of truth, never live-mutated state
(`values-interface.schema.json`, `tenant.ref`).
