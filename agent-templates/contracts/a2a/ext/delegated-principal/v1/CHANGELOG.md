# Changelog — `delegated-principal`

This extension keeps its own changelog. `contracts/a2a/v1/CHANGELOG.md` is frozen
along with the rest of v1, and appending to it would be an edit to the thing this
extension exists to avoid editing.

## 1.0.0

Initial release.

### Added

- **The originating principal rides in the credential.** RFC 8693 `sub` (the human
  or service the work is ultimately for) plus an `act` chain (the immediate actor,
  then its actor). v1 carried a single `caller` string, so a CEO and a warehouse
  worker arriving through the same repo were indistinguishable to the callee.
- **Intersection authorization**: `effective = permitted(sub) ∩ brokerable(actor)`.
  Both terms are required. The agent cannot grant more than the subject has, and
  the subject cannot reach past what the agent may broker.
- **A closed skill classification**: `delegable` / `principal-required` /
  `never-delegable`. No fourth member and no default — an unclassified skill is
  denied. `never-delegable` is the machine-readable form of the `reach_human` and
  `_base` guardrails authz.md §7 already describes in prose.
- `schema/delegated-principal-token.schema.json`, `schema/delegation-policy.schema.json`,
  worked examples, and `a2a/delegation.py` wired into `authz.authorize()`.

### Compatibility

Additive in both directions, which is the test for an extension rather than a
version:

- A callee that does not publish the extension URI behaves exactly as v1.
- A caller that sends no delegated credential is handled exactly as v1.
- The policy lives in its own `.fuze/a2a-delegation.json`, **not** under the
  manifest's `a2a` block — v1's `manifest-a2a-extension.schema.json` sets
  `additionalProperties: false` there, so a `delegation` key would have made every
  adopting repo's manifest fail v1 validation.

### Not included

The **token-exchange endpoint**. Minting the delegated token before dialling is
the caller's side of the work and is where the remaining implementation sits.
This release is the callee-side enforcement plus the contract it enforces against.
