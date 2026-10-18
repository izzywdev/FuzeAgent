# Changelog — Fuze A2A contract

SemVer per `governance/versioning.md`, applied to the **contract**:

- **MAJOR** — a change that breaks an existing caller: removing/renaming a card field or skill id,
  changing a state mapping, tightening the profile, narrowing the allowlist semantics.
- **MINOR** — additive and backward compatible: a new optional card field, an additional
  `supportedInterfaces` entry (e.g. gRPC), a new optional projection input, new error mappings.
- **PATCH** — clarification with no wire effect: wording, examples, mock fixtures.

The contract version is independent of the A2A **protocol** version it is frozen against; the
protocol version appears in the card as `AgentInterface.protocolVersion` and on the wire as the
`A2A-Version` header.

---

## 1.4.0 — 2026-09-22

Additive, backward-compatible MINOR bump within v1. **Caller-side client-credentials
token minting.** The generated client (`fuze_a2a_client`) gains a token *provider* so a
pod that calls a peer can obtain its own `aud=a2a` access token instead of relying on a
statically injected bearer. No wire change: the schemas, cards, error codes, JSON-RPC
methods and state mapping are untouched — this is purely how the CALLER acquires the
bearer it already had to present (`authz.md` §2, `binding.md` §1). Closes the runtime
gap left after FuzeFront-side OIDC provisioning
([izzywdev/FuzeInfra#981](https://github.com/izzywdev/FuzeInfra/issues/981)).

### Added

- `client/fuze_a2a_client/auth.py`:
  - `ClientCredentialsTokenProvider` — mints a token via the OAuth 2.0
    client-credentials grant (RFC 6749 §4.4), resolving `token_endpoint` from the
    provider's OIDC discovery document (`oidcDiscoveryUrl`, fetched in-cluster per
    `deploy/helm/a2a-shared/GO-LIVE.md` §1b), caching the access token and re-minting
    on expiry (with a configurable pre-expiry skew). Thread-safe. Transport-injectable
    like `A2AClient`, so it is unit-testable without a network or `httpx`.
  - `token_provider_from_env()` — builds a provider from the caller-side `A2A_*`
    environment (`A2A_CLIENT_ID`, `A2A_CLIENT_SECRET`/`A2A_CLIENT_SECRET_FILE`,
    `A2A_OIDC_DISCOVERY_URL`/`A2A_OIDC_ISSUER_URL`, `A2A_TOKEN_AUDIENCE`,
    `A2A_TOKEN_SCOPE`), or `None` when unconfigured so a static `A2A_TOKEN` still
    works. The client secret is read from a mounted secret file or env — never
    hardcoded, never projected onto a card.
  - `TokenFetchError`.
- `A2AClient(token=...)` now also accepts a **zero-arg callable** (`TokenSource`), not
  only a `str`. The header is resolved per request, so a provider's refresh is
  transparent to callers. Passing a `str` is unchanged.

### Changed

- `agent-templates/orchestration/a2a_transport.py` (caller runtime) now falls back to a
  `token_provider_from_env()` provider when no static `A2A_TOKEN` is set, so every
  outbound A2A call presents a freshly minted, unexpired `aud=a2a` token.

---

## 1.3.0 — 2026-08-27

Additive, backward-compatible MINOR bump within v1. **Runtime tenant registration.** Tenants may now
be resolved from a runtime DB registry owned by the orchestrator instead of the static
`a2a.tenants[]` values array. Tracking issue: [izzywdev/FuzeAgent#203](https://github.com/izzywdev/FuzeAgent/issues/203).

This freezes the **interface** for the new topology; it is the gate the implementer slices build on
(Slice 1 migration, the orchestrator handlers, Slice 3 server reader, tests, docs). No handler, SQL
or chart is added here.

### Added

- `schema/tenant-registration.schema.json` — the runtime-registry shapes:
  - `RegisteredTenant` — the canonical `a2a_tenants` record (`tenant` unique key, `repo`, `ref`,
    `entryRole`, `servingRoles[]`, `external`, `provider`, `card`, `enabled`, `createdAt`,
    `updatedAt`). Frozen ONCE here so the DB migration and the A2A server reader target one shape.
  - `RegisterTenantRequest` / `RegisterTenantResponse` — the self-registration payload and its
    upsert result.
  - `TenantList` — the `GET /a2a/tenants` response (marked `x-pagination: exempt`: a bounded
    whole-set config read the A2A server resolves atomically).
  - The `card` field **reuses `agent-card.schema.json` by reference** — the projected card shape is
    **not** redefined and remains byte-identical to a card projected from a cloned repo. A pushed
    card MUST additionally satisfy `fuze-profile.schema.json`.
- `tenant-registration.md` — NORMATIVE spec for the two orchestrator HTTP operations
  (`POST /a2a/tenants/register`, `GET /a2a/tenants` [+ `/{tenant}`]): idempotent-upsert semantics,
  the OIDC caller-repo self-registration security rule (a registration whose `tenant`/`repo` ≠ the
  authenticated identity is rejected `403` and never written), and the two-schema card-validation
  rule.
- `examples/registration/fuzeplan.tenant-registration.json` — a worked registration built from the
  frozen FuzePlan card, doubling as a fixture. Placed in a subdirectory so the card-conformance
  suite's `examples/*.json` glob (which treats every flat entry as an Agent Card) does not mistake
  the registration wrapper for a card.
- `client/fuze_a2a_client/registration_models.py` — GENERATED Pydantic models for the new shapes;
  `regenerate.sh` now emits it (bundling the cross-file card ref for single-file codegen). Exported
  from `fuze_a2a_client` (`RegisterTenantRequest`, `RegisteredTenant`, `RegisterTenantResponse`,
  `TenantList`). Client package bumped `1.0.0` → `1.3.0` — the first bump since freeze that changes
  the generated surface, so the package version now tracks the contract version again.

### Backward compatibility

Purely additive. `values-interface.schema.json` and the static `a2a.tenants[]` topology are
**unchanged and still valid**; `agent-card.schema.json`, `fuze-profile.schema.json`,
`a2a-wire.schema.json`, `card-projection.md`, `binding.md`, `state-mapping.md` and `authz.md` are
untouched. A v1 consumer that does not use runtime registration is unaffected; the two topologies
serve **byte-identical cards**. No wire/card *shape* changed, so existing `wire_models` / `card_models`
are byte-identical after regeneration.

---

## 1.2.0 — 2026-08-10

Additive, backward-compatible MINOR bump within v1. **Per-product A2A pods become deployable.**

### Added

- `schema/values-interface.schema.json` — optional `a2a.inClusterUrl` (`string`, `format: uri`,
  default `http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc`). The in-cluster JSON-RPC
  endpoint the server advertises as `AgentInterface.url` on every non-external card it projects.

  Until now that URL was a **constant in the generator**
  (`agent-templates/a2a/card_generator.py`), so any second A2A deployment started healthy and
  published the *shared* server's address — callers following its card never reached it. That single
  constant, not the protocol and not the chart, is why every product's A2A pod shipped disabled.

  It is placed **inside the `a2a` block, not beside the chart-internal `deploy.*` mechanics**,
  because the block is what the chart serialises verbatim into the `values.json` the server parses
  (`config.load_config`); a key under `deploy:` is invisible to the server and would need an invented
  env var to reach it. Substantively it is a *card-projection input* — the published callable
  endpoint — of the same kind as `auth.oidcIssuerUrl`, not a chart knob like `replicas`.

### Changed (documentation only — no wire, card or schema constraint changed)

- Schema `description` and `tenants` description: the "ONE shared server" constraint is now stated as
  the **default** topology rather than the only one. Owner decision: each product gets its own A2A
  agent pod for compartmentalisation and robustness. The shared server is unchanged.
- `card-projection.md` §2: the in-cluster `url` row now names `a2a.inClusterUrl` as its source, with
  the shared address as the default.

Not `required`; **an unchanged values file produces a byte-identical card**, so the live `a2a-shared`
deployment (tenants FuzeAgent, FuzeFront, FuzePlan) is unaffected. No wire/card *shape* change, so
the generated `fuze_a2a_client` (wire/card models only) is not affected.

---

## 1.1.0 — 2026-07-24

Additive, backward-compatible MINOR bump within v1.

### Added

- `schema/values-interface.schema.json` — optional `a2a.auth.oidcDiscoveryUrl` (`string`,
  `format: uri`). Overrides where the shared A2A server fetches OIDC discovery + JWKS (typically an
  in-cluster URL for hardened bring-up), while the token `iss` claim is STILL validated against
  `oidcIssuerUrl`. When unset, discovery is derived from `oidcIssuerUrl` exactly as before.

Not `required`; existing configs that omit it are unchanged. No wire/card change, so the generated
`fuze_a2a_client` (wire/card models only) is not affected. Motivated by the hardened A2A bring-up
(in-cluster JWKS fetch) decided on FuzeFront#364.

---

## 1.0.0 — 2026-07-20

Initial frozen contract. Adopts the **open A2A standard**; supersedes the bespoke
`services/orchestrator/a2a_protocol.py` as the protocol definition.

**Frozen against A2A specification 1.0.0** — canonical source `specification/a2a.proto`
(`package lf.a2a.v1`) in `a2aproject/A2A`. Verified directly against the proto and spec prose,
not against the generated `a2a.json` (which upstream marks non-normative).

### Added

- `schema/agent-card.schema.json` — Agent Card, ProtoJSON/camelCase serialization.
- `schema/fuze-profile.schema.json` — family narrowing of the open card (JSON-RPC only, protocol
  `1.0`, streaming on, push off, signatures required).
- `schema/a2a-wire.schema.json` — wire types for the v1 method set.
- `schema/manifest-a2a-extension.schema.json` — `.fuze/manifest.json` additions (`providesTo`
  allowlist, `a2a` block).
- `schema/role-a2a-extension.schema.json` — optional `a2a` block on `role.json`; every field has a
  derived default, so no existing role manifest needs editing.
- `schema/values-interface.schema.json` — the shared-server Helm values **interface** (no chart).
- `binding.md` — JSON-RPC 2.0 + SSE as the v1 baseline; gRPC and HTTP+JSON explicitly **out**.
- `state-mapping.md` — normative A2A ↔ `agent-templates/providers/base.py` mapping.
- `card-projection.md` — normative derivation of cards from manifest + roles, product and exec tier.
- `authz.md` — callee-enforced, fail-closed authorization.
- `client/` — generated Pydantic models (`regenerate.sh`) plus the typed `A2AClient`.
- `mock/` — servable card and canned responses covering completed / input-required / auth-required /
  rejected / working / canceled and the error paths.
- `examples/` — a product card (FuzePlan) and an exec-tier card (CTO), doubling as fixtures.

### Decisions recorded

- **Open A2A standard adopted** (CTO-tier decision). The existing 794-line
  `services/orchestrator/a2a_protocol.py` has the right concepts but no `jsonrpc` and no
  `/.well-known/`; it interoperates with nothing and is not the protocol. Reconciling it is a
  follow-up, not part of this contract.
- **One shared A2A server**, not one per product. Expressed inside the standard via
  `AgentInterface.tenant`, so this is a deployment topology, not a protocol deviation.
- **The pod is an adapter, not an engine.** `base.py` already provides sessions, blocking,
  approvals, resumption and cancellation.
- **Exec-tier roles get their own cards**, one per role with its own `tenant`, so
  "may escalate to the CTO" is distinguishable from "may instruct the CFO".
- **gRPC/REST deferred**, addable later as a purely additive MINOR bump.

### Known gaps (deliberately not fixed here)

- **`providesTo` is absent on most repos.** Verified at freeze time: present on FuzeBI,
  FuzeExecutive, FuzeSales, FuzeService; **absent** on FuzeAgent, FuzeInfra, FuzeFront, FuzeKeys,
  FuzePlan, FuzeContact, FuzeHub, FuzeSocial, FuzeDeploy, FuzeSDLC. The model therefore **fails
  closed** on absence. Backfilling is a precondition for enabling A2A on a repo and is owned by
  platform-governance/devops.
- Card signing **key material and rotation** are unspecified here (devops slice); the contract fixes
  only that `signatures[]` is required and non-empty.
- The `a2a` blocks are defined here as schemas but are **not yet merged into**
  `agent-templates/schema/role-manifest.schema.json` or the manifest schema — that edit is gated on
  this contract.
