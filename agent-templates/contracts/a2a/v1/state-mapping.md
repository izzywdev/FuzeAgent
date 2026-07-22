# A2A ↔ Managed-Agents state mapping (NORMATIVE)

**The A2A pod is an ADAPTER. There is no new task engine.**

`agent-templates/providers/base.py` already defines an `AgentProvider` seam whose primitives line up
with A2A almost one-to-one. The adapter's entire job is translation: A2A wire objects in, provider
calls out, provider results back to A2A objects. If an implementer finds themselves writing a
scheduler, a retry loop, a state machine, or a transcript store, they have missed this document —
all four already exist below the seam.

Sources frozen against: A2A spec **1.0.0** (`lf.a2a.v1`, `a2a.proto`) and
`agent-templates/providers/base.py` @ `35969a4`.

---

## 1. Identity mapping

| A2A | Managed Agents | Rule |
|---|---|---|
| `Task.id` | provider `session_id` | **The session id IS the task id.** No side table, no id mapping. Sessions persist server-side, so `GetTask` is a session lookup. |
| `Task.contextId` | conversation/thread id | Stable across the task chain; a follow-up `SendMessage` carrying `taskId` joins the same session. |
| `tenant` | serving repo | Selects which repo's role set the request resolves against. |
| skill `id` | `role` key | Selects the role manifest → `ensure_agent` → `agent_id`/`version`. |
| `Message.parts[].text` | prompt text | Concatenated in order. Non-text parts per §6. |

**No transcript ever crosses the wire.** A2A `Message` carries the *request*, not history. This
mirrors the existing handoff rule (`resume_session(summary=…)`, never replay) and is a correctness
requirement, not an optimization: the callee's session already holds its own history server-side, so
replaying it would both duplicate context and leak the caller's internal deliberation into the
callee's window.

## 2. `SendMessage` / `SendStreamingMessage`

For a request with **no** `taskId` (new task):

```
1. resolve tenant -> repo; resolve skill id -> role.json  (default: manifest.a2a.entryRole)
2. session_id = provider.create_session(
       agent_id, version, environment_id,
       vault_ids=<from role>, memory_resources=<from role>,
       title=<caller identity + first 80 chars of prompt>)
3. emit Task{ id: session_id, status.state: TASK_STATE_SUBMITTED }
4. result = provider.run_until_block(session_id, prompt=<joined parts>)
5. map result.status -> TaskState per §3
```

For a request **with** `taskId` (continuation) — see §4; it is `resume_session`, never
`create_session`.

**Blocking semantics.** `SendMessageConfiguration.returnImmediately` selects the shape:

- `false` (A2A default): the adapter awaits `run_until_block` and returns the Task in its settled
  state — terminal or interrupted. This is the natural fit, because `run_until_block` returns at
  exactly the A2A-significant moments and nowhere else.
- `true`: return `TASK_STATE_SUBMITTED` immediately; run `run_until_block` out of band. The caller
  then polls `GetTask` or opens `SubscribeToTask`.

**Streaming.** `SendStreamingMessage` frames the SAME provider call as SSE
(`Content-Type: text/event-stream`, each event `data: {"jsonrpc":"2.0","id":<id>,"result":<StreamResponse>}`).
The driver already opens an SSE stream to the provider; the adapter re-frames those events as
`TaskStatusUpdateEvent` / `TaskArtifactUpdateEvent`. It does **not** open a second execution path —
streaming and non-streaming MUST run the identical provider call, or the two will drift.

## 3. Status mapping (the core table)

`run_until_block` returns `{'text', 'status': idle|blocked|error, 'pending': {...}|None}`.

| provider result | A2A `TaskState` | Notes |
|---|---|---|
| `status == 'idle'` | `TASK_STATE_COMPLETED` | Terminal. `text` → final agent `Message`; structured outputs → `Artifact`s. |
| `status == 'error'` | `TASK_STATE_FAILED` | Terminal. `text` → `TaskStatus.message`. |
| `status == 'blocked'`, `pending` is a tool approval | `TASK_STATE_INPUT_REQUIRED` | Interrupted. See §4. |
| `status == 'blocked'`, `pending` is a credential/auth request | `TASK_STATE_AUTH_REQUIRED` | Interrupted. See §4. |
| adapter refuses before dispatch (allowlist deny, unknown skill) | `TASK_STATE_REJECTED` | Terminal. Never leak *why* beyond "not authorized" (authz.md §6). |
| `archive_session` on caller request | `TASK_STATE_CANCELED` | Terminal. See §5. |
| pre-dispatch, session created | `TASK_STATE_SUBMITTED` | |
| dispatched, no result yet | `TASK_STATE_WORKING` | Emitted on the stream; not a resting state. |

`TASK_STATE_UNSPECIFIED` MUST never be emitted.

**Discriminating `INPUT_REQUIRED` from `AUTH_REQUIRED`.** Both arise from `status: 'blocked'`, so the
adapter inspects `pending`:

- The pause is `AUTH_REQUIRED` when what is missing is a **credential or an authorization grant** —
  the callee lacks a token/permission it needs to proceed, and someone outside the session must
  supply it (A2A §7.6, in-task authorization).
- Otherwise it is `INPUT_REQUIRED` — the callee has everything it needs but wants a **decision or
  more information** (the ordinary `always_ask` permission pause, e.g. "may I open this PR against
  prod?").

Getting this split wrong is the most likely adapter bug, because both look identical at the
`base.py` seam (`status: 'blocked'`) and only differ in the `pending` payload. Implementers MUST
branch on `pending`, never on the status string alone.

## 4. Interrupted tasks: `always_ask` and `reach_human`

This is where the Managed-Agents permission model meets the A2A protocol, and the mapping is exact.

**How a pause surfaces.** A role whose tool carries
`permission_policy: {"type": "always_ask"}` (e.g. every `slack` toolset in the exec roles, and every
production/third-party action per the `_base` guardrails) causes `run_until_block` to return
`status: 'blocked'` with a `pending` descriptor. The adapter:

1. Maps to `TASK_STATE_INPUT_REQUIRED` (or `AUTH_REQUIRED`, per §3).
2. Sets `TaskStatus.message` to an agent-role `Message` describing **what** is being asked and
   **why**, sourced from the `pending` description. A2A §7.6.1 makes this message mandatory for
   `AUTH_REQUIRED`; the Fuze profile requires it for `INPUT_REQUIRED` too — a pause a caller cannot
   interpret is a hang.
3. Keeps the task non-terminal and, per A2A §7.6.1, keeps any open response stream alive.

**How the caller resolves it.** The caller sends `SendMessage` with the same `taskId` and its answer
in `parts`. The adapter:

```
provider.confirm_tool(session_id, tool_use_id=<from pending>,
                      allow=<parsed from caller reply>,
                      deny_message=<caller's reason, if deny>)
result = provider.run_until_block(session_id)   # continue; no prompt replay
```

**`reach_human` is the other resolution path, and it is first-class.** When the pause needs a *human*
rather than the calling agent — a binding decision, a production approval — the callee's own agent
calls `reach_human` (handoff MCP) against the relevant digital persona. Crucially this happens
**entirely on the callee's side**: the caller sees only a task sitting in `INPUT_REQUIRED`/
`AUTH_REQUIRED`, and the human's answer arrives out-of-band (A2A §7.6.1 explicitly permits
out-of-band credential/decision delivery and allows the agent to resume without a follow-up client
message). The adapter therefore MUST NOT assume every interrupted task is resolved by the caller;
it MUST tolerate a task transitioning out of `INPUT_REQUIRED` with no client input at all.

Consequence for callers, stated normatively: **a caller MUST NOT treat `INPUT_REQUIRED` as its own
obligation until it has read `TaskStatus.message`.** Some pauses are addressed to it; some are
addressed to a human it cannot see. Polling until terminal, or subscribing, is always safe.

This is also the escalation path in §5 of card-projection.md: an agent asks the CTO agent for an
architecture ruling, the CTO agent pauses on `reach_human` to the human CTO's digital persona, and
the task sits in `INPUT_REQUIRED` — legitimately, possibly for hours — until the human answers.
Callers MUST NOT impose short timeouts on exec-tier tasks.

## 5. `GetTask`, `SubscribeToTask`, `ListTasks`, `CancelTask`

| A2A method | Provider call | Notes |
|---|---|---|
| `GetTask` | session lookup by id | `historyLength` bounds returned `Message`s. |
| `SubscribeToTask` | re-attach to the session's SSE stream | MUST return `UnsupportedOperationError` (`-32004`) if already terminal, per spec. |
| `ListTasks` | sessions filtered by caller identity | A caller MUST see only tasks **it** created. Cross-caller visibility is a disclosure bug. |
| `CancelTask` | `provider.archive_session(session_id)` | → `TASK_STATE_CANCELED`. `archive_session` is best-effort; if it fails the adapter still reports `CANCELED` only once archival is confirmed, otherwise `TaskNotCancelableError` (`-32002`). |

Push-notification methods are **not supported in v1** (`capabilities.pushNotifications: false`) and
MUST return `PushNotificationNotSupportedError` (`-32003`).

## 6. Parts and artifacts

| A2A | Handling |
|---|---|
| `Part.text` | Joined into the prompt in order. |
| `Part.data` | Serialized as fenced JSON in the prompt; `metadata` preserved. |
| `Part.url` / `Part.raw` | v1: **not accepted** on input → `ContentTypeNotSupportedError` (`-32005`). Large state is passed by reference through the existing handoff memory store (`/handoff/<session-id>.md`) and named in a `data` part — consistent with the established "never inline large state" rule. |
| Output `Artifact` | Files the callee produced. `artifactId` MUST be stable across `append` chunks. |

## 7. What the adapter MUST NOT do

- Persist its own task table. `Task` state is derived from the session; a second store guarantees drift.
- Replay transcripts. Continuations use `resume_session(summary=…)` / `confirm_tool`.
- Retry a failed task automatically. `FAILED` is terminal and belongs to the caller to re-drive.
- Interpret or rewrite the callee's `system`/`system_append`. The role manifest is the callee's, not the wire's.
- Downgrade an interrupted state to a terminal one on timeout. An abandoned task stays
  `INPUT_REQUIRED`; reaping is an operational policy, not a protocol event.
