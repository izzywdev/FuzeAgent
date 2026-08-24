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

## 2.0.0 — 2026-08-24

**MAJOR.** Caller identity changes shape. v1 stays frozen and supported at `../v1` (1.2.0); this is
not a deprecation, and a product may stay on v1 indefinitely.

### Why this is MAJOR and not MINOR

By this file's own rule a MAJOR is "a change that breaks an existing caller ... **narrowing the
allowlist semantics**". That is precisely what happens: a call that v1 authorises on `providesTo`
alone can now be denied at step 6 because the *principal* behind it lacks the permission. Existing
callers that send no delegated principal are rejected outright. Nothing about that is additive.

### Added

- **Caller principal.** The credential now resolves to a `(actor, principal)` pair — `act` (the
  calling repo/agent, which was the whole of v1's identity) and `sub` (the human or agent the call is
  made ON BEHALF OF). Both come from the validated token; neither may come from the body. Obtained by
  RFC 8693 token exchange before dialling.
- **Step 6, principal authorization.** The callee asks its own Permit for a decision on `sub`.
  `DENY` and `DECISION_UNAVAILABLE` both deny — the authz client is fail-closed by contract.
- **Step 7, intersection.** Effective permission is what the ACTOR may broker AND what the PRINCIPAL
  may do. Never the union. This closes escalation in both directions.
- **§6a, the non-delegable set.** Three dispositions — delegable / delegable-with-principal-check /
  never-delegable — with an unclassified operation treated as never-delegable. v1 already had the
  seeds (`reach_human`, the `_base` prod guardrails, `always_ask`); v2 names them as a set so they
  can be enumerated rather than remembered.

### Changed

- `authz.md` §2 (identity), §3 (decision procedure), §7 (scope of a grant).
- `schema/values-interface.schema.json` — `a2a.inClusterUrl` default follows the workload rename to
  `a2a-<product>`: `http://a2a-fuzeagent.fuzeagent.svc.cluster.local:8080/rpc`. The same rename is
  applied to the normative examples in `binding.md`, `card-projection.md`, `README.md`, the two
  example cards and the client docstring. **The 1.2.0 entry below is left as written** — it records
  what shipped then, and rewriting history to match the present is how a changelog stops being
  evidence.

### The problem this solves

In v1 the identity WAS the repo, so two calls arriving through the same calling repo were
indistinguishable to the callee. If `FuzeExecutive` appeared in a callee's `providesTo`, every call
from FuzeExecutive was permitted — an agent acting for the CEO and the same agent acting for a
support worker got the same answer. `providesTo` is a channel grant; no amount of care in the
allowlist makes a repo-level field answer a person-level question.

The corollary, stated in §2 because it is the part most likely to be got wrong: **the A2A pod is a
delegate, never a principal.** It holds no standing authority over product data. A pod with root on
the product it fronts is the confused-deputy shape — any caller reaching it inherits that authority,
and the only thing between a worker and a destructive operation is application logic remembering to
check.

### Not yet implemented

This document is the contract. The runtime (`agent-templates/a2a/authz.py`) still implements v1:
`AuthContext` carries a single `caller`, and there is no Permit call. Implementation is tracked
separately — the contract is the gate, and it lands first, exactly as v1 did.

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
