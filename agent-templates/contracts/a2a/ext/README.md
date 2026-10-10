# A2A contract extensions

`contracts/a2a/v1` is **frozen**. Capability added after the freeze lands here as
a versioned extension, never as an edit to v1 and never as a v2 unless the wire
protocol itself must change.

The mechanism is the one A2A already defines: `AgentCapabilities.extensions[]` on
the Agent Card, which v1's `agent-card.schema.json` already accepts. A callee
publishes an extension URI to say it enforces those rules; a callee that does not
publish it behaves exactly as v1.

## The test for "extension, not version"

**Adopting it must not require editing anything frozen, and not adopting it must
not change anything.** Both halves matter, and the first one has teeth: the
`delegated-principal` policy lives in its own `.fuze/a2a-delegation.json` file
precisely because v1's `manifest-a2a-extension.schema.json` sets
`additionalProperties: false` on the `a2a` block — putting the policy there would
have made every adopting repo's manifest fail v1 validation, which would have made
this a version wearing an extension's name.

| Extension | Version | What it adds |
|---|---|---|
| [`delegated-principal`](delegated-principal/v1/) | 1.0.0 | The ORIGINATING principal rides in the credential (RFC 8693 `sub`/`act`), so a callee can tell a CEO from a warehouse worker arriving through the same repo — which v1 cannot. Plus intersection-not-union authorization and a closed delegable/principal-required/never-delegable classification. |
