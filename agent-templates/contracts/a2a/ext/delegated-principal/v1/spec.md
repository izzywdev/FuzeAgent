# `delegated-principal` v1 — normative spec

Key words per RFC 2119.

## §1 Negotiation

A callee that enforces this extension MUST publish it in its Agent Card:

```json
{ "capabilities": { "extensions": [
  { "uri": "https://contracts.fuzefront.com/a2a/ext/delegated-principal/v1",
    "required": true,
    "description": "Calls carry the originating principal; see spec.md" } ] } }
```

`required: true` means a call WITHOUT a conforming credential MUST be denied for
every skill this callee classifies as `principal-required` or `never-delegable`.
It does not change the handling of `delegable` skills, which remain exactly v1.

A callee that does not publish the URI MUST behave as v1. A caller that does not
send the credential to such a callee MUST be handled as v1. **Neither side gets a
new failure mode from an unadopted extension** — that is what makes this an
extension rather than a version.

## §2 The credential

Delegation is carried by **RFC 8693 token exchange**, in the credential, and
**NEVER in the request body**. v1 authz.md §1 already forbids trusting the body
for authorization; this extension adds a claim, not an exemption.

```json
{
  "iss":  "https://auth.fuzefront.com/",
  "aud":  "a2a-shared",
  "sub":  "user:izzy@fuzefront.com",
  "act":  { "sub": "repo:FuzeExecutive",
            "act": { "sub": "agent:a2a-shared" } }
}
```

- **`sub` is the ORIGINATING principal** — the human or service on whose behalf the
  work is ultimately done. This is what Permit decides on.
- **`act` is the actor chain**, outermost first: the immediate actor, then its
  actor, and so on. It BOUNDS what `sub` can reach; it never widens it.
- The chain MUST be non-empty when `sub` is present, and every entry MUST be a
  typed reference (`repo:`, `agent:`, `service:`). A bare id is REJECTED — an
  untyped actor cannot be checked against the brokerable set.
- The callee MUST verify the credential's signature and `aud` before reading any
  claim. An unverified `sub` is worth less than no `sub`, because it looks like
  authority.

## §3 Where the policy lives

The policy is its own file: **`.fuze/a2a-delegation.json`**, validated against
`schema/delegation-policy.schema.json`.

It is deliberately NOT a key inside the manifest's `a2a` block. v1's
`manifest-a2a-extension.schema.json` sets `additionalProperties: false` on that
block, so a `delegation` key there would make **every adopting repo's manifest
fail v1 validation**. An extension that requires editing the frozen contract in
order to adopt it is a version, not an extension. A separate file keeps it
additive — a repo that has not adopted has no such file, and nothing changes for
it.

## §4 Classification is CLOSED

Every skill a callee publishes MUST fall in exactly one class:

| Class | Meaning |
|---|---|
| `delegable` | any allowlisted caller may invoke; no principal needed (v1 behaviour) |
| `principal-required` | requires a verified `sub` AND an ALLOW from Permit for that subject |
| `never-delegable` | no principal reaches it through A2A, regardless of `sub` |

**There is no fourth bucket.** A skill that is not classified MUST be DENIED, not
treated as `delegable`. An "unclassified" default is how a new endpoint acquires
the weakest rule in the system by being written rather than by being decided —
the same closed-set property applied by the route-ownership and OpenAPI gates.

`never-delegable` is the machine-readable form of what authz.md §7 already seeds:
`reach_human` for binding decisions, and the `_base` guardrails on `kubectl patch`,
`helm rollback`, `terraform destroy`.

## §5 Intersection, never union

For a `principal-required` skill the effective permission is

```
effective = permitted(sub, action, resource)  ∩  brokerable(actor_chain, skill)
```

Both terms MUST be evaluated and both MUST allow. Specifically:

- **The agent cannot grant more than the subject has.** A subject with no right to
  delete a ticket does not acquire one by asking through an agent that has it.
- **The subject cannot reach past what the agent may broker.** A CEO with every
  right in Permit still cannot use an agent to reach a skill that agent is not
  permitted to broker.

Implementations MUST NOT short-circuit on either term alone. A union — "allow if
either permits" — is not a weaker version of this rule; it is the opposite of it.

## §6 Failure is closed and uninformative

- Missing `sub` on a `principal-required` skill → DENY.
- Unverifiable credential → DENY.
- Permit unreachable → DENY. `DECISION_UNAVAILABLE` is never an allow; there is no
  fail-open mode and no configuration flag that creates one.
- Unclassified skill → DENY (§4).
- Untyped actor entry → DENY (§2).

Wire errors MUST NOT disclose which of these applied, per v1 authz.md §6. The
distinction belongs in the callee's logs.

## §7 What this extension does NOT do

- It does not weaken `providesTo`. Channel authz still runs first, and a caller
  outside `providesTo` is denied before any of this is consulted.
- It does not move authorization into the request body.
- It does not give the pod standing authority. The pod's own credential authorizes
  presenting delegated tokens and nothing else.
- It does not define the token-exchange endpoint. Obtaining the delegated token is
  the CALLER's side of the work and is out of scope here — which is where the real
  remaining implementation sits.
