# Call another product's agent

Hand a **goal** to another product's agent over A2A. You do not need any of that
product's tools, skills, or credentials — that is the point (see
[mcp-pod-vs-a2a-pod.md](mcp-pod-vs-a2a-pod.md)). The callee owns the tools and the
credentials; you own the goal.

The worked example the contract exists to make true (README.md "What A2A is for"):

> A requirements-discussion agent needs Jira tickets. It holds **no Atlassian MCP and
> no Jira skill**. It sends one A2A message to the **FuzePlan** agent — which owns the
> Jira skill, the Atlassian MCP and the credentials — and FuzePlan creates them.

There is a generated Python client — `fuze_a2a_client` — so you rarely hand-build wire
frames. It ships in [`contracts/a2a/v1/client/`](../../agent-templates/contracts/a2a/v1/client/).
The steps below use it; the raw JSON-RPC underneath is in
[`binding.md`](../../agent-templates/contracts/a2a/v1/binding.md).

---

## 1. Resolve the callee's Agent Card

Fetch the card at the registered well-known path — served unauthenticated (binding.md
"Agent Card discovery", spec §8.2):

```
GET {base_url}/.well-known/agent-card.json
```

```python
from fuze_a2a_client import A2AClient, TERMINAL_STATES

card = A2AClient.fetch_card("http://a2a-shared.fuzeagent.svc.cluster.local:8080")
```

The card tells you:

- **Where to send** — the interface `url`, `protocolBinding: "JSONRPC"`,
  `protocolVersion: "1.0"`, and the **`tenant`** you must echo on every call
  (card-projection.md §2). In v1 there is exactly one interface; there is no top-level
  `url`/`preferredTransport` (that is a common mistake — README.md "five things").
- **What it can do** — each `skill.id` (e.g. `product-manager`) with a human
  description and `examples`. See
  [`examples/fuzeplan.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/fuzeplan.agent-card.json).
- **How to authenticate** — the `fuze-oidc` scheme. You send a bearer OIDC access
  token; the callee's validated view of your token is your identity (authz.md §2).

The public card lists only broadly-discoverable skills. To see the skills **you** are
actually allowlisted for, fetch the authenticated **extended** card — it is computed
per caller, so two callers legitimately see different skill sets (authz.md §5):

```python
client   = A2AClient(card, token=oidc_token)
ext_card = client.fetch_extended_card()   # GetExtendedAgentCard
```

---

## 2. Hand over a goal — `SendMessage`

Send a natural-language goal and the `skill_id` you want:

```python
task = client.send_message(
    "Create Jira tickets for the requirements in this discussion.",
    skill_id="product-manager",     # a skill id from the card
)
```

- Omit `skill_id` and the callee's **`entryRole`** handles it (state-mapping.md §2).
- The client echoes the card's `tenant` for you and sends the required `A2A-Version: 1.0`
  header (binding.md §1). The `tenant` MUST match the selected interface's `tenant`.
- By default the call **blocks** until the task settles (terminal or interrupted) —
  `SendMessageConfiguration.returnImmediately` is `false` (state-mapping.md §2). Pass
  `return_immediately=True` to get a `TASK_STATE_SUBMITTED` task back at once and poll.

Watch a task progress instead of blocking with `send_streaming_message(...)` (SSE) —
the same underlying call, framed as events (binding.md streaming; state-mapping.md §2).

### The result is a `Task` with a `state`

```python
if task.status.state in TERMINAL_STATES:
    ...   # COMPLETED / FAILED / REJECTED / CANCELED — done
else:
    ...   # INPUT_REQUIRED / AUTH_REQUIRED — see §3; read task.status.message FIRST
```

Terminal states (state-mapping.md §3):

| State | Meaning |
|---|---|
| `TASK_STATE_COMPLETED` | Done. Final text is the agent's `Message`; structured outputs are `Artifact`s. |
| `TASK_STATE_FAILED` | The callee errored. `text` is in `TaskStatus.message`. **Not retried automatically — it is yours to re-drive** (state-mapping.md §7). |
| `TASK_STATE_REJECTED` | "You may not ask me this" — an authorization denial. Terminal. Do **not** retry against a grant that will never exist (authz.md §4). |
| `TASK_STATE_CANCELED` | You cancelled it (`CancelTask`). |

---

## 3. Handle `INPUT_REQUIRED` / `AUTH_REQUIRED` coming back

A non-terminal task means the callee **paused**. This is normal — the callee's own
`always_ask` guards (e.g. "may I open this PR against prod?") and exec `reach_human`
escalations both surface this way (state-mapping.md §4).

### Rule: read `TaskStatus.message` before assuming it is your turn

> **A caller MUST NOT treat `INPUT_REQUIRED` as its own obligation until it has read
> `TaskStatus.message`.** (state-mapping.md §4, and README.md gotcha 4.)

The pause may be addressed to **you**, or it may be addressed to a **human the callee is
reaching that you cannot see** (`reach_human`). The callee resolves a `reach_human`
pause **entirely on its own side** — the human's answer arrives out-of-band and the task
can leave `INPUT_REQUIRED` with **no input from you at all** (state-mapping.md §4). So:

- **Polling `GetTask` until terminal, or `SubscribeToTask`, is always safe.**
- Only answer if `TaskStatus.message` is actually asking *you* for a decision/info.

### Discriminating the two blocked states

| State | Means | Who supplies the answer |
|---|---|---|
| `TASK_STATE_INPUT_REQUIRED` | The callee has what it needs but wants a **decision or more information** (an `always_ask` pause). | You (via the callee) — **or** a human via `reach_human`. |
| `TASK_STATE_AUTH_REQUIRED` | The callee lacks a **credential or authorization grant** it needs to proceed (A2A §7.6). | Someone outside the session supplies the credential; may resolve out-of-band. |

`AUTH_REQUIRED` is **not** the same as `REJECTED`. `AUTH_REQUIRED` = "I, the callee, need
a credential to continue my work." `REJECTED` = "you may not ask me this" (authz.md §4).
Do not retry a `REJECTED` task.

### Answering a pause addressed to you

Send `SendMessage` again with the **same `task_id`** and your answer in the text. The
callee resumes its session — it never replays a transcript (state-mapping.md §1, §4):

```python
answer = client.send_message(
    "Yes, proceed — use the 2026-Q3 board.",
    task_id=task.id,
)
```

### Exec-tier tasks: expect long, legitimate pauses

When you call an exec agent (e.g. `Exec-cto`) for a binding decision, it will commonly
pause on `reach_human` to the human's digital persona and sit in `INPUT_REQUIRED`
**possibly for hours** while the human is reached (card-projection.md §5,
state-mapping.md §4). This is expected — an exec escalation that returns instantly is
*more* suspicious than one that blocks.

> **Callers MUST NOT impose short timeouts on exec-tier tasks.** (state-mapping.md §4.)

See the exec card's own description of this behaviour:
[`examples/exec-cto.agent-card.json`](../../agent-templates/contracts/a2a/v1/examples/exec-cto.agent-card.json).

---

## 4. Follow-up methods

| Client call | A2A method | Use |
|---|---|---|
| `client.get_task(task_id)` | `GetTask` | Poll a task's current state. `history_length` bounds returned messages. |
| `client.subscribe_to_task(task_id)` | `SubscribeToTask` | Re-attach to a live task's event stream (SSE). Raises `UnsupportedOperationError` (`-32004`) if already terminal. |
| `client.list_tasks()` | `ListTasks` | Lists **only your own** tasks — cross-caller visibility is a disclosure bug (state-mapping.md §5). |
| `client.cancel_task(task_id)` | `CancelTask` | Archives the session → `TASK_STATE_CANCELED`. |

Push-notification / webhook methods are **not supported in v1** — they return
`PushNotificationNotSupportedError` (`-32003`). Use `SubscribeToTask` or poll `GetTask`
instead (binding.md §1, state-mapping.md §5).

---

## 5. Input constraints (v1)

- **Text and JSON in, text and artifacts out.** `Part.text` is joined into the prompt in
  order; `Part.data` is serialized as fenced JSON (state-mapping.md §6).
- **No inline large state.** `Part.url` / `Part.raw` inputs are rejected with
  `ContentTypeNotSupportedError` (`-32005`). Pass large state **by reference** through the
  handoff memory store and name it in a `data` part (binding.md §2, state-mapping.md §6).
- **No transcript crosses the wire.** A `Message` carries the *request*, not history; the
  callee's session already holds its own history server-side (state-mapping.md §1).

---

## Common mistakes (from README.md "five things")

1. JSON-RPC methods are **bare PascalCase** — `SendMessage`, not `message/send`, not
   `a2a.SendMessage`. The client handles this; only relevant if you go raw.
2. There is **no top-level `url`/`preferredTransport`** — read the interface from
   `supportedInterfaces`.
3. `securitySchemes` values are ProtoJSON oneof-wrapped
   (`{"openIdConnectSecurityScheme": {…}}`), not the OpenAPI shape.
4. `INPUT_REQUIRED` **may not be addressed to you** — read `TaskStatus.message` first.
5. **Absent `providesTo` denies.** If you get `REJECTED`/not-found, you are probably not
   in the callee's `providesTo` — see [authz-for-integrators.md](authz-for-integrators.md).
