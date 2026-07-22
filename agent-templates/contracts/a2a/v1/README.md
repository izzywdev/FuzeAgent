# Fuze A2A contract v1 — FROZEN

**Contract version 1.0.0** · frozen against **A2A specification 1.0.0** (`lf.a2a.v1`,
canonical source `specification/a2a.proto` in [`a2aproject/A2A`](https://github.com/a2aproject/A2A)).

This directory is the **gate**. Backend, tests, devops, MCP/CLI and docs streams all build against
what is here; none of them started before it was frozen.

---

## What A2A is for

Every product runs two surfaces in prod:

| | MCP pod | **A2A pod** (this contract) |
|---|---|---|
| Offers | *tools* — "call my functions" | *agency* — "here is a goal" |
| Caller must hold | the domain's tools + credentials | **nothing** |
| Orchestration | caller's | callee's |

The worked example, which the contract exists to make true:

> A requirements-discussion agent needs Jira tickets. It holds **no Atlassian MCP and no Jira
> skill**. It sends one A2A message to the **FuzePlan** agent — which owns the Jira skill, the
> Atlassian MCP and the credentials — and FuzePlan creates them.

That is **capability + credential encapsulation**. Every rule here is downstream of preserving it;
see `card-projection.md` §7 for the invariant and how the projection enforces it.

Mention-triggers (`@claude`/`@codex`/`@gemini` on GitHub issues) are **not** replaced by A2A. Those
are human→agent; A2A is agent→agent. Both remain first-class (FuzeSDLC baseline §9).

## Read in this order

| Document | What it fixes |
|---|---|
| [`binding.md`](binding.md) | JSON-RPC 2.0 over HTTP + SSE. gRPC/REST explicitly **out** of v1. Methods, errors, transport. |
| [`card-projection.md`](card-projection.md) | How a card is **derived** from `.fuze/manifest.json` + `agent-templates/roles/*/role.json`. Product **and** exec tier. |
| [`state-mapping.md`](state-mapping.md) | A2A ↔ `agent-templates/providers/base.py`. The pod is an **adapter**. |
| [`authz.md`](authz.md) | Callee enforces, caller is untrusted, `providesTo` is the grant, absence **denies**. |
| [`CHANGELOG.md`](CHANGELOG.md) | SemVer policy, decisions recorded, known gaps. |

## Layout

```
schema/
  agent-card.schema.json             Agent Card (ProtoJSON/camelCase)
  fuze-profile.schema.json           family narrowing of the card
  a2a-wire.schema.json               Task/Message/Part/events/JSON-RPC envelope
  manifest-a2a-extension.schema.json .fuze/manifest.json additions (providesTo, a2a block)
  role-a2a-extension.schema.json     optional a2a block on role.json
  values-interface.schema.json       shared-server Helm values INTERFACE (no chart)
client/                              generated Pydantic models + typed A2AClient
mock/                                servable card + canned responses
examples/                            FuzePlan (product) and CTO (exec) cards
VERSION  CHANGELOG.md
```

## The five things most likely to be got wrong

1. **JSON-RPC method names are bare PascalCase** — `SendMessage`, not `message/send` (that is 0.x)
   and not `a2a.SendMessage`. Wrong names fail as `MethodNotFoundError` with no other clue.
2. **A2A 1.0 has no top-level `url`/`preferredTransport`** — endpoints live in `supportedInterfaces`.
3. **`securitySchemes` values are ProtoJSON oneof-wrapped** — `{"openIdConnectSecurityScheme": {…}}`,
   not the OpenAPI shape.
4. **`INPUT_REQUIRED` may not be addressed to you.** The callee may be blocked on `reach_human`.
   Read `TaskStatus.message` before assuming it is your turn, and never impose short timeouts on
   exec-tier tasks (`state-mapping.md` §4).
5. **Absent `providesTo` denies.** It is not "unset means open". Most repos do not have it yet.

## Quick start (caller side)

```python
from fuze_a2a_client import A2AClient, TERMINAL_STATES

card   = A2AClient.fetch_card("http://a2a-shared.fuzeagent.svc.cluster.local:8080")
client = A2AClient(card, token=oidc_token)

task = client.send_message(
    "Create Jira tickets for the requirements in this discussion.",
    skill_id="product-manager",
)
if task.status.state not in TERMINAL_STATES:
    ...  # read task.status.message — see gotcha 4
```

Regenerate models after any schema change: `client/regenerate.sh`. Never hand-edit
`wire_models.py` / `card_models.py`.

## Scope

This is the contract only. **Not** here, by policy (FuzeSDLC baseline §4): the server/adapter
implementation, handlers, Helm chart or Argo application, behaviour tests, CI. Those are the
implementer streams that gate on this document.
