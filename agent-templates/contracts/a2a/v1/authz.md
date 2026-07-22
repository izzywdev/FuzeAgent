# Authorization model (NORMATIVE)

## 1. The rule

> **The CALLEE enforces. The caller is opaque and untrusted.**

This follows A2A's own guidance (spec §7.4–7.5: the server MUST authenticate every request and
authorizes it against *its own* policies). It is also the only model consistent with the point of
A2A: if the caller could assert its own permissions, the callee's credentials would effectively be
delegated to it, and the encapsulation property would be gone.

Concretely, the callee MUST NOT trust **anything** in the request body for authorization: not
`tenant`, not `metadata`, not a self-declared caller name in `Message.metadata`. The only trusted
input is the **authenticated identity from the transport credential**.

## 2. Identity

Per A2A `securitySchemes`, the Fuze profile declares:

| Scheme | Card representation | Use |
|---|---|---|
| `fuze-oidc` | `openIdConnectSecurityScheme` | **Primary.** Bearer access token; the identity is the token's validated subject/claim identifying the calling repo agent. |
| `fuze-mtls` | `mtlsSecurityScheme` | In-cluster defence in depth; client cert subject as a second factor. Declared only when `a2a.external` is false. |

The caller identity resolved from the credential MUST be a **repo name** matching
`manifest-a2a-extension.schema.json#/$defs/repoName` (e.g. `FuzeSales`), or an exec principal
(`Exec-cto`). Anything else is rejected.

Network position is **not** identity. Being inside the cluster grants nothing; an unauthenticated
in-cluster request is rejected exactly as an external one is.

## 3. The allowlist

The grant lives in the **callee's** `.fuze/manifest.json`:

```jsonc
{
  "repo": "izzywdev/FuzePlan",
  "providesTo": ["FuzeSales", "FuzeService", "FuzeExecutive"],   // AUTHORITATIVE
  "dependsOn":  ["FuzeContact", "FuzeBI"]                        // advisory only
}
```

| Field | Whose file | Authority |
|---|---|---|
| `providesTo` | **callee's** manifest | **THE grant.** Caller identity must appear here. |
| `dependsOn` | caller's manifest | **Advisory only.** A caller listing a callee grants nothing. Useful for graph/lint tooling and for the caller to self-check before dialling; never consulted by the callee. |

The asymmetry is deliberate. If `dependsOn` were honoured, any repo could grant itself access by
editing its own file — a self-signed permission. `providesTo` puts the grant in the file owned and
reviewed by the party bearing the risk.

**Decision procedure (callee side, per request):**

```
1. Authenticate the credential.               fail -> AUTH error
2. caller := identity from credential.        (never from the body)
3. callee := tenant -> repo.                  unknown -> TaskNotFoundError
4. providesTo := callee manifest.providesTo
   - ABSENT      -> DENY   (fail closed; unconfigured != permissive)
   - []          -> DENY   (explicitly "no agent callers")
   - caller ∉ it -> DENY
5. skill := requested skill id (or entryRole)
   - not published to this caller (§5) -> DENY
   - a2a.scopes present -> token must carry them, else AUTH_REQUIRED
6. dispatch
```

**Fail-closed is load-bearing.** A **verified** gap at freeze time: `providesTo` is present on only
4 of the surveyed repos (FuzeBI, FuzeExecutive, FuzeSales, FuzeService) and **absent** on FuzeAgent,
FuzeInfra, FuzeFront, FuzeKeys, FuzePlan, FuzeContact, FuzeHub, FuzeSocial, FuzeDeploy and FuzeSDLC.
Had the model treated "absent" as "allow", enabling A2A would have silently opened every one of those
repos to every caller. Backfilling `providesTo` is a **precondition** for enabling A2A on a repo, not
a follow-up — and it is out of scope for this contract PR.

## 4. Denials are terminal, not interrupted

An authorization failure at step 4 or 5 is `TASK_STATE_REJECTED` — terminal. It is **not**
`AUTH_REQUIRED`. `AUTH_REQUIRED` means *"I, the callee, need a credential to continue my work"*
(spec §7.6); `REJECTED` means *"you may not ask me this."* Conflating them invites a caller to retry
forever against a grant that will never exist.

`AUTH_REQUIRED` at step 5 (missing scope) is the one legitimate overlap: the caller is allowlisted
but its token lacks a scope it could plausibly obtain.

## 5. Card visibility: public vs extended

Two cards, deliberately:

| | `/.well-known/agent-card.json` | `GetExtendedAgentCard` |
|---|---|---|
| Auth | none | authenticated |
| Skills | those with `a2a.publish: true` **and** `a2a.extendedOnly: false` | all skills the **authenticated caller** is allowlisted for |
| Purpose | discovery | actual routing |

The extended card is computed **per caller**. Two allowlisted callers can legitimately receive
different skill sets from the same agent. This is why `capabilities.extendedAgentCard` is `true`
across the profile: a single public card cannot express caller-dependent capability without either
over-disclosing or under-advertising.

## 6. Non-disclosure on denial

A denied caller MUST NOT be able to distinguish:

- a callee/tenant that does not exist,
- a callee that exists but does not list it in `providesTo`,
- a skill that exists but is not published to it,
- a task id belonging to another caller.

All four return the same shape (`TaskNotFoundError` / `-32001`, or `REJECTED` with a generic
message). Otherwise the error channel becomes an enumeration oracle for the family's capability
graph — a caller could map every product's skills simply by probing. Detailed reasons go to the
callee's logs, never onto the wire.

## 7. Scope of a grant

`providesTo` grants the right to **ask**, not the right to **command**. Downstream of dispatch the
callee's own controls still apply, unchanged:

- `always_ask` permission policies still pause (→ `INPUT_REQUIRED`, state-mapping.md §4).
- `_base` guardrails still forbid `kubectl patch`/`helm rollback`/`terraform destroy` against prod,
  and the worker guard-shims still block them at the OS level.
- `reach_human` is still required for binding decisions.

An allowlisted caller therefore cannot use A2A to escape a restriction it would face directly. A2A
adds a *front door*; it does not widen any room behind it.

## 8. Auditing

Every request logs: caller identity (from credential), callee tenant, skill id, task/session id,
decision, and — on `INPUT_REQUIRED`/`AUTH_REQUIRED` — the pause reason. Prompt text and artifact
content are **not** logged (they carry the caller's business context).
