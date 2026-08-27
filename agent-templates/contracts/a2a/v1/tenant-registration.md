# Tenant registration (NORMATIVE) — runtime A2A tenant registry

Added in contract **v1.3.0** (additive within v1). Freezes the two orchestrator HTTP operations and
the record shape behind the runtime-registration topology decided in
[izzywdev/FuzeAgent#203](https://github.com/izzywdev/FuzeAgent/issues/203).

## 0. Why this exists

Through v1.2.0 the shared A2A server learned its tenant set at **git/build time**: the static
`a2a.tenants[]` array in `deploy/helm/a2a-shared/values-prod.yaml`
(`values-interface.schema.json`) was rendered to a ConfigMap the server read via `A2A_VALUES_FILE`,
and an initContainer cloned each tenant repo so the server could **project** the card from
`.fuze/manifest.json` + `agent-templates/roles/*`.

`#203` moves this to **runtime**:

- Consumers **self-register** into a DB registry **owned by the orchestrator**.
- The A2A server stays **stateless and DB-free**; it **fetches** the resolved tenant set from the
  orchestrator over HTTP (decision #1).
- The consumer **pushes its already-projected Agent Card as data** at registration; the server
  **validates and stores** it — **no server-side repo cloning** (decision #2).
- FuzeAgent stops knowing consumers at git/build time.

This is **purely additive**. The static `a2a.tenants[]` topology is untouched and still valid; a
deployment that never calls these endpoints behaves exactly as in v1.2.0. Nothing here removes,
renames or re-types a frozen field. **This document is the contract only** — the migration
(Slice 1), the orchestrator handlers (this endpoint pair) and the A2A server reader (Slice 3) are
implementer streams that gate on it. No handler, SQL, or chart is defined or implied here.

## 1. Surface

Two operations on the **orchestrator** (NOT the A2A JSON-RPC `/rpc` surface — these are ordinary
REST over the orchestrator's HTTP API, which is why they are documented here rather than in
`binding.md`). Shapes are frozen in `schema/tenant-registration.schema.json`.

| Method & path | `$def` in / out | Auth | Purpose |
|---|---|---|---|
| `POST /a2a/tenants/register` | `RegisterTenantRequest` → `RegisterTenantResponse` | OIDC bearer, caller-repo claim (§3) | A consumer self-registers / re-registers itself. Idempotent upsert keyed on `tenant`. |
| `GET /a2a/tenants` | — → `TenantList` | service credential (§3) | The A2A server resolves the full tenant set. `?enabled=true` filters to served tenants. **Not paginated** (§5). |
| `GET /a2a/tenants/{tenant}` | — → `RegisteredTenant` (404 if unknown) | service credential (§3) | Single-tenant read. Singleton; inherently unpaginated. |

Field naming is **camelCase** in JSON, ISO-8601 UTC (`Z`) timestamps — same wire conventions as the
rest of the contract (`binding.md` §1).

## 2. Idempotent-upsert semantics

`tenant` is the **unique registry key** (the record's natural id — there is no separate minted
uuid; see `identifier-standard §4.2` and the `x-client-assigned-id: allowed` marker on
`RegisterTenantRequest`).

- First registration of a `tenant` **inserts** the row → **`201 Created`**, response
  `created: true`.
- A registration of an existing `tenant` **replaces** the mutable fields
  (`repo`, `ref`, `entryRole`, `servingRoles`, `external`, `provider`, `enabled`, `card`) →
  **`200 OK`**, response `created: false`. `createdAt` is preserved; `updatedAt` advances.
- The operation is therefore safe to run on **every pod start, every restart, and concurrently
  across replicas** — the same property the existing `registration/register.sh` init-container
  relies on. Concurrent upserts of the same `tenant` MUST converge to a single row (the writer uses
  an atomic upsert on the `tenant` unique key); they never create duplicates.

`createdAt` / `updatedAt` are **server-owned**. They appear only on the stored `RegisteredTenant`
(and in the response), never in `RegisterTenantRequest` — a client that sends them is rejected
(`additionalProperties: false`).

`GET /a2a/tenants` returns `enabled` tenants under `?enabled=true` (what the A2A server asks for) and
all rows otherwise (operator view). Disabling a tenant is an orchestrator-side flag flip on
`enabled`; it does not require the consumer to re-register.

## 3. Self-registration authorization (fail-closed identity binding)

Registration is authenticated by the **same OIDC caller-repo claim the A2A server already validates
today** — `auth.callerClaim` in `values-interface.schema.json`, the caller identity of
`authz.md` §2. Network position is **not** identity (`authz.md` §2); an unauthenticated request is
rejected exactly as an external one is.

**The binding rule (normative):**

> A `RegisterTenantRequest` whose `repo` — or whose `tenant`, which MUST be derivable from that
> `repo` — is **not equal to** the authenticated caller identity is **REJECTED with `403`** and
> **never written**.

```
1. Authenticate the credential.                      fail      -> 401
2. caller := repo identity from auth.callerClaim.    (never from the body)
3. body.repo != caller                               -> 403  (identity mismatch)
4. body.tenant not derivable from caller repo        -> 403  (a caller may register
                                                              ONLY its own tenant slug)
5. validate body.card (see §4)                       invalid   -> 422
6. upsert (see §2)                                    -> 201 / 200
```

A consumer can therefore register **only itself**. It cannot register, mutate, or disable another
product's tenant, and it cannot smuggle a foreign `tenant`/`repo` through the body — the body is
untrusted for identity, exactly as `authz.md` treats the request body as untrusted for
authorization. This is the registration-time analogue of the callee-enforced model: **the registry
owner enforces; the caller is untrusted.**

`GET /a2a/tenants` and `GET /a2a/tenants/{tenant}` are read by the **A2A server** (and operators),
not by arbitrary product agents; they require a service credential authorized for registry reads.
The registry read surface is **not** an A2A capability graph and is not subject to `providesTo`.

**`providesTo` is untouched by registration.** Self-registering (and self-`enabled: true`) grants a
tenant **no** caller access. The A2A authorization grant still lives in the **callee's**
`.fuze/manifest.json` `providesTo` and is still enforced **fail-closed** by the callee at call time
(`authz.md` §3). A tenant that registers itself but whose `providesTo` is absent still denies every
caller. Enabling A2A on a repo still requires backfilling `providesTo` — out of scope here.

## 4. Card validation (the pushed card must be a real, served card)

The consumer pushes its **projected** Agent Card in `card`. It is **byte-identical** to what the
generator used to project from a cloned repo — `#203` changes only **how the card arrives**, not
**what it looks like** (`card-projection.md` is unchanged). The server does not clone the repo and
does not re-project; it **validates the pushed card and stores it verbatim**.

Validation is the **same two-schema check** a served card satisfies today (`fuze-profile.schema.json`
§ "A card MUST validate against BOTH"):

1. Structural: `card` MUST validate against **`agent-card.schema.json`** (referenced by the `card`
   field — the shape is **not** redefined in the registration schema).
2. Profile: `card` MUST **additionally** validate against **`fuze-profile.schema.json`** —
   non-empty `signatures[]`, exactly one `JSONRPC`/`1.0` interface carrying a `tenant`,
   `capabilities.streaming=true` / `pushNotifications=false` / `extendedAgentCard=true`,
   `provider.organization="FuzeOne"`.

A card failing **either** check is rejected with **`422`** and never written. Additionally, the
card's interface `tenant` MUST equal the record `tenant`, and (unless `external: true`) the card's
interface `url` MUST be an in-cluster address — a stored card whose `url` no caller can follow is
useless (`card-projection.md` §2). The encapsulation invariant (`card-projection.md` §7) is a
property of the card itself and is therefore preserved unchanged: a pushed card carries no
credential, vault id, MCP server URL or tool name, because it is the same projected card.

Because the card is **signed** (`signatures[]` required, RFC 8785 JCS over the card excluding
`signatures`), a consumer cannot forge capabilities it was not projected to hold: an altered card
fails signature verification. Signing key material / rotation remain a devops concern
(`card-projection.md` §6), out of scope for this contract.

## 5. Pagination

`GET /a2a/tenants` is marked **`x-pagination: exempt`** in the schema (`TenantList`). It is a
**bounded whole-set configuration read**, not an open-ended collection: its consumer is the
stateless A2A server resolving its **complete** routing table, it needs every enabled tenant
atomically, and the set is bounded by the number of products in the family (~two dozen). Cursoring it
would make the server page its own configuration and risk a torn routing table. `GET
/a2a/tenants/{tenant}` is a singleton read and inherently unpaginated. If the registry ever grows
beyond a whole-set read (it is not expected to), adding a paginated variant is a future additive
MINOR bump.

## 6. What this does NOT change (regression guard)

- `values-interface.schema.json` — unchanged. Static `a2a.tenants[]` remains a valid topology.
- `agent-card.schema.json`, `fuze-profile.schema.json`, `a2a-wire.schema.json`,
  `card-projection.md`, `binding.md`, `state-mapping.md`, `authz.md` — unchanged.
- The projected **card shape** — unchanged and reused by reference.
- The A2A JSON-RPC `/rpc` surface and its method set — unchanged.

A v1 consumer that does not use runtime registration is entirely unaffected.
