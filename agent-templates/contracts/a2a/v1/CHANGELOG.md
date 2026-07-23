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
