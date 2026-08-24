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

The credential resolves to a **caller pair**, not a single name. Both halves come from the
validated token; neither may come from the body.

| Half | Token claim | What it is | v1 equivalent |
|---|---|---|---|
| **actor** | `act` (innermost) | the calling agent/repo — a repo name matching `manifest-a2a-extension.schema.json#/$defs/repoName` (e.g. `FuzeSales`), or an exec principal (`Exec-cto`) | this was the whole of v1's identity |
| **principal** | `sub` | the originating human or agent the call is made ON BEHALF OF | **did not exist in v1** |

Anything else in either position is rejected.

**Why this is the v2 change.** In v1 the identity WAS the repo. Two calls arriving through the same
calling repo were therefore indistinguishable to the callee: if `FuzeExecutive` appeared in a
callee's `providesTo`, every call from FuzeExecutive was permitted, whoever was behind it. An agent
acting for the CEO and the same agent acting for a support worker got the same answer. `providesTo`
is a *channel* grant and cannot express that difference — no amount of care in the allowlist makes a
repo-level field answer a person-level question.

**The A2A pod is a DELEGATE, never a principal.** It holds no standing authority over product data.
Its own workload credential authorises exactly one thing: *may present delegated tokens*. Every bit
of data-plane authority arrives with the call, in the token. A pod holding root or near-root on the
product it fronts is the confused-deputy shape: any caller reaching it inherits that authority, and
the only thing between a worker and a destructive operation is application logic remembering to
check.

**Obtaining the pair.** The caller performs an RFC 8693 token exchange before dialling, presenting
its own credential as `actor_token` and the originating principal's as `subject_token`. The result
carries `sub` = principal and `act` = the actor chain. The callee validates the token and reads
both; it never reconstructs either from the request.

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
2. (actor, principal) := from credential.     (never from the body)
   - actor missing/malformed     -> DENY
   - principal missing           -> DENY  (v2: an un-delegated call is not
                                           anonymous, it is unauthorised)
3. callee := tenant -> repo.                  unknown -> TaskNotFoundError
4. providesTo := callee manifest.providesTo
   - ABSENT      -> DENY   (fail closed; unconfigured != permissive)
   - []          -> DENY   (explicitly "no agent callers")
   - caller ∉ it -> DENY
5. skill := requested skill id (or entryRole)
   - not published to this actor (§5) -> DENY
   - a2a.scopes present -> token must carry them, else AUTH_REQUIRED
6. PRINCIPAL AUTHZ (v2, new). Ask the callee's own Permit for a decision on
   `principal` for the requested action/resource.
   - DENY or DECISION_UNAVAILABLE -> DENY   (fail closed; the authz client has
                                             no fail-open option by contract)
7. Effective permission is the INTERSECTION of steps 4-5 and step 6:
   what the ACTOR may broker  AND  what the PRINCIPAL may do.
   Never the union. This closes escalation in both directions — the agent
   cannot grant more than its principal holds, and a principal cannot use the
   agent to reach something the agent is not allowed to broker.
8. dispatch
```

**Step 7 is the whole point.** Steps 4-5 alone are v1: a channel grant. Step 6 alone would let any
repo broker anything its principal happens to hold, dissolving `providesTo`. Only the intersection
expresses "this agent, acting for this person, may do this".

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

## 6a. The non-delegable set (v2)

Three dispositions, and every operation sits in exactly one. There is deliberately no fourth
"unclassified" bucket — an operation nobody has classified is treated as **never-delegable**, not as
delegable-by-default. A closed set is the only shape that stays correct as operations are added,
because the failure mode of an open set is silence.

| Disposition | Meaning |
|---|---|
| **delegable** | any allowlisted actor may broker it for any principal Permit approves |
| **delegable-with-principal-check** | the default: steps 4-7 above, intersection enforced |
| **never-delegable** | refused regardless of actor, principal, or Permit decision |

The never-delegable set is not new policy — v1 already had its seeds, scattered. v2 names them as a
set so they can be enumerated rather than remembered:

- `reach_human` is required for binding decisions (state-mapping.md §4).
- `_base` guardrails forbid `kubectl patch` / `helm rollback` / `terraform destroy` against prod, and
  the worker guard-shims block them at the OS level.
- Anything a repo's own policy marks `always_ask` pauses to `INPUT_REQUIRED` rather than proceeding.

A never-delegable operation returns `TASK_STATE_REJECTED` with the same generic shape as any other
denial (§6) — the fact that an operation is non-delegable is itself not disclosed, or the error
channel becomes a map of what is worth attacking.

## 7. Scope of a grant

`providesTo` grants the right to **ask**, not the right to **command**. Downstream of dispatch the
callee's own controls still apply, unchanged:

- `always_ask` permission policies still pause (→ `INPUT_REQUIRED`, state-mapping.md §4).
- `_base` guardrails still forbid `kubectl patch`/`helm rollback`/`terraform destroy` against prod,
  and the worker guard-shims still block them at the OS level.
- `reach_human` is still required for binding decisions.

An allowlisted caller therefore cannot use A2A to escape a restriction it would face directly. A2A
adds a *front door*; it does not widen any room behind it.

**v2 addition:** `providesTo` now grants the right to ask *on someone's behalf*, and says nothing
about whose behalf. It answers "may this repo talk to me at all" and stops there. Whether the person
behind the call may perform the action is step 6, decided by the callee's Permit on `sub`. Neither
substitutes for the other: a repo in `providesTo` whose principal Permit denies is denied, and a
principal with every permission arriving from a repo absent from `providesTo` is denied.

## 8. Auditing

Every request logs: caller identity (from credential), callee tenant, skill id, task/session id,
decision, and — on `INPUT_REQUIRED`/`AUTH_REQUIRED` — the pause reason. Prompt text and artifact
content are **not** logged (they carry the caller's business context).
