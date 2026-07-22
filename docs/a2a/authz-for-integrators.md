# AuthZ for integrators

Who is allowed to call whom, why a call gets denied, and why "it just returns
not-found" is the **intended** behaviour. Full model:
[`authz.md`](../../agent-templates/contracts/a2a/v1/authz.md).

---

## The one rule

> **The CALLEE enforces. The caller is opaque and untrusted.** (authz.md §1.)

The callee authenticates every request and authorizes it against **its own** policy.
Nothing in the request body is trusted for authorization — not `tenant`, not `metadata`,
not a self-declared caller name. The **only** trusted input is the authenticated identity
from the transport credential (your OIDC bearer token), resolved to a **repo name** like
`FuzeSales` or an exec principal like `Exec-cto` (authz.md §2).

Network position is **not** identity. Being inside the cluster grants nothing; an
unauthenticated in-cluster request is rejected exactly as an external one is (authz.md §2).

---

## The allowlist: `providesTo` (absent = DENY)

The grant lives in the **callee's** `.fuze/manifest.json`:

```jsonc
{
  "repo": "izzywdev/FuzePlan",
  "providesTo": ["FuzeSales", "FuzeService", "FuzeExecutive"],  // AUTHORITATIVE
  "dependsOn":  ["FuzeContact", "FuzeBI"]                       // advisory only
}
```

| Field | Whose file | Authority |
|---|---|---|
| `providesTo` | **callee's** manifest | **THE grant.** Your identity must appear here to call the callee. |
| `dependsOn` | **your** manifest | **Advisory only.** Listing a callee grants you nothing. |

The asymmetry is deliberate: if `dependsOn` were honoured, any repo could grant itself
access by editing its own file — a self-signed permission. `providesTo` puts the grant in
the file owned and reviewed by the party bearing the risk (authz.md §3).

### Absent means DENY — this is the load-bearing part

The callee's per-request decision (authz.md §3):

```
1. Authenticate the credential.               fail -> AUTH error
2. caller := identity from credential.        (never from the body)
3. callee := tenant -> repo.                  unknown -> TaskNotFoundError
4. providesTo := callee manifest.providesTo
   - ABSENT      -> DENY   (fail closed; unconfigured != permissive)
   - []          -> DENY   (explicitly "no agent callers")
   - caller ∉ it -> DENY
5. skill := requested skill id (or entryRole)
   - not published to this caller -> DENY
   - a2a.scopes present -> token must carry them, else AUTH_REQUIRED
6. dispatch
```

**An absent `providesTo` is DENY, not "open."** "Unconfigured" is never "permissive."
This is what keeps enabling A2A from silently exposing a repo to every caller (authz.md
§3). It is also why, as an integrator, you must **be listed in the callee's
`providesTo`** before you can call it — this is a real precondition on the callee's side,
not something that happens automatically.

At contract-freeze time `providesTo` was present on only 4 surveyed repos (FuzeBI,
FuzeExecutive, FuzeSales, FuzeService) and **absent** on the rest — FuzeAgent, FuzeInfra,
FuzeFront, FuzePlan, FuzeContact, and more (authz.md §3). So if you try to call one of
those today, expect a denial until its owner backfills `providesTo`. If you own a callee,
see the precondition in [enable-your-pod.md](enable-your-pod.md).

---

## Denials look identical on purpose

A denied caller **cannot tell apart** (authz.md §6):

- a callee/tenant that does not exist,
- a callee that exists but does not list you in `providesTo`,
- a skill that exists but is not published to you,
- a task id belonging to another caller.

All four return the **same** shape — `TaskNotFoundError` (`-32001`), or `REJECTED` with a
generic message. This is deliberate: otherwise the error channel becomes an enumeration
oracle letting a caller map every product's capability graph by probing. Detailed reasons
go to the **callee's logs**, never onto the wire (authz.md §6).

**So if you get a not-found / rejected you did not expect, do not infer anything from the
shape.** The likely cause is simply that you are not in the callee's `providesTo`, or the
skill is not published to you. Ask the callee's owner — the answer is in their logs, not
your error.

---

## `REJECTED` vs `AUTH_REQUIRED` — don't confuse them

| Result | Means | Should you retry? |
|---|---|---|
| `TASK_STATE_REJECTED` | "You may not ask me this." An authorization denial. Terminal. | **No.** The grant will never exist by retrying (authz.md §4). |
| `TASK_STATE_AUTH_REQUIRED` | "I, the callee, need a credential/scope to continue" (spec §7.6). | Only after the missing credential/scope is supplied. |

The one legitimate overlap: at decision step 5, if you **are** allowlisted but your token
lacks a `a2a.scopes` scope you could plausibly obtain, you get `AUTH_REQUIRED` (authz.md
§4). Example: the exec CTO skill requires the `a2a.exec.escalate` scope
([`examples/exec-cto.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/exec-cto.agent-card.json),
`securityRequirements`).

---

## A grant is the right to *ask*, not to *command*

Being in `providesTo` grants the right to **ask**, not the right to **command**. All the
callee's own controls still apply downstream of dispatch (authz.md §7):

- `always_ask` permission policies still pause (→ `INPUT_REQUIRED`).
- `_base` guardrails still forbid `kubectl patch` / `helm rollback` /
  `terraform destroy` against prod, and the worker guard-shims still block them at the OS
  level.
- `reach_human` is still required for binding decisions.

So an allowlisted caller **cannot use A2A to escape a restriction it would face
directly**. A2A adds a *front door*; it does not widen any room behind it (authz.md §7).

---

## Two cards: public vs extended

There are two views of a callee's card (authz.md §5):

| | `/.well-known/agent-card.json` | `GetExtendedAgentCard` |
|---|---|---|
| Auth | none | authenticated |
| Skills shown | publicly discoverable ones | all skills **you** are allowlisted for |
| Purpose | discovery | actual routing |

The extended card is computed **per caller**, so two allowlisted callers can legitimately
receive different skill sets from the same agent. Fetch the extended card (see
[call-another-agent.md](call-another-agent.md) §1) to learn what **you** may actually call
— the public card may show less.

---

## Auditing

Every request is logged with: caller identity (from the credential), callee tenant, skill
id, task/session id, the decision, and — on `INPUT_REQUIRED`/`AUTH_REQUIRED` — the pause
reason. Prompt text and artifact content are **not** logged, since they carry the caller's
business context (authz.md §8).
