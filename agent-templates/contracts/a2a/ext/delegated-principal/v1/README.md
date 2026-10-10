# `delegated-principal` — A2A extension v1.0.0

**URI:** `https://contracts.fuzefront.com/a2a/ext/delegated-principal/v1`

An **extension**, not a v2. `contracts/a2a/v1` is frozen and this tree does not
edit one byte of it. The mechanism is the one A2A already defines:
`AgentCapabilities.extensions[]` on the card (`agent-card.schema.json` →
`AgentExtension`), which v1's schema already accepts. A callee that does not
publish this URI behaves exactly as v1 specifies; a caller that does not send a
delegated credential is handled exactly as v1 specifies.

## The gap it closes

v1's `AuthContext.caller` is a **single string**, and `valid_caller_identity()`
accepts a bare repo name or an `Exec-*` principal (authz.md §2). There is no
end-user subject anywhere in the model.

So a CEO and a warehouse worker arriving through the same calling repo are
**literally indistinguishable to the callee**. If `FuzeExecutive` is in
`FuzePlan`'s `providesTo`, both pass, identically.

The contract's authors already stated the intent in authz.md §7 — *"`providesTo`
grants the right to ask, not the right to command… A2A adds a front door; it does
not widen any room behind it."* What was missing was the identity precision to act
on it, because identity resolved to a **repo** rather than a **person**.

## The pod is a delegate, never a principal

The A2A pod holds **no standing authority over product data**. Its workload
credential authorizes exactly one thing: *may present delegated tokens*. Every bit
of data-plane authority arrives with the call.

The rejected alternative — give the pod broad rights and have it check the caller
before acting — is the confused deputy. It makes the guard a matter of the pod
remembering to look, which is a convention, not a construction.

## Four layers

| # | Layer | Mechanism | Status in v1 |
|---|---|---|---|
| 1 | **Channel** — may repo X reach repo Y at all? | `providesTo` | ✅ exists, unchanged |
| 2 | **Principal** — may *this subject* do this action? | RFC 8693 `sub` + `act` chain, in the credential, never the body | ❌ this extension |
| 3 | **Intersection** — effective = subject's rights **∩** agent's brokerable set | both escalation directions closed | ❌ this extension |
| 4 | **Non-delegable set** — operations no principal reaches via A2A | closed classification, no unclassified bucket | partial (§7 seeds it) |

Layer 3 is the load-bearing one: the agent cannot grant more than the caller has,
**and** a caller cannot use the agent to reach what the agent may not broker.

## Files

| Path | What |
|---|---|
| `spec.md` | the normative rules |
| `schema/delegated-principal-token.schema.json` | the credential claims |
| `schema/delegation-policy.schema.json` | the per-callee classification, closed |
| `examples/` | a token, a policy, and the card capability entry |

Implementation: `agent-templates/a2a/delegation.py`, wired into `authz.authorize()`
behind `AuthContext.delegation` — absent means v1 behaviour, exactly.
