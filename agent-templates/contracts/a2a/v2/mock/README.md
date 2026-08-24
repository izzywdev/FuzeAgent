# Mock configuration

Lets every downstream stream — backend, tests, MCP/CLI clients — work against the frozen
contract **before** the real adapter exists. Nobody waits on the server.

## What is here

| File | Purpose |
|---|---|
| `agent-card.mock.json` | A servable public Agent Card. Serve at `/.well-known/agent-card.json`. |
| `responses.mock.json` | Canned JSON-RPC responses, one per method, covering the full `TaskState` range including both interrupted states. |

## Serving it

Any static file server plus a JSON-RPC stub works. The card is the only endpoint with a
fixed path:

```bash
# card discovery
GET /.well-known/agent-card.json   ->  mock/agent-card.mock.json

# JSON-RPC
POST /rpc  ->  look up params-independent fixture by `method` in responses.mock.json
```

The client points at a mock by injecting a transport — no code change:

```python
from fuze_a2a_client import A2AClient, AgentCard
card = AgentCard.model_validate(json.load(open("mock/agent-card.mock.json")))
client = A2AClient(card, token="mock", transport=MyMockTransport())
```

## The scenarios that matter

`responses.mock.json` deliberately includes the cases most likely to be mishandled:

- `SendMessage.completed` — the happy path.
- `SendMessage.inputRequired` — an `always_ask` pause. `TaskStatus.message` explains the ask.
  A caller that does not read this message cannot behave correctly (state-mapping.md §4).
- `SendMessage.authRequired` — a missing-credential pause. Distinct from the above.
- `SendMessage.rejected` — an authorization denial. **Terminal**, not retryable (authz.md §4).
- `GetTask.working` — a task still running.
- `CancelTask.canceled` — cancellation.
- `error.taskNotFound` — the deliberately-ambiguous denial (authz.md §6).
- `error.pushNotSupported` — every push-notification method in v1.

Consumers should exercise the interrupted and rejected fixtures, not only the happy path;
those are where the A2A/Managed-Agents seam is easiest to get wrong.

> Fixtures are illustrative shapes conforming to `../schema/a2a-wire.schema.json`. They are
> not behaviour tests — independent contract tests are `test-engineer`'s slice and are gated
> on this contract.
