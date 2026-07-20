# Protocol binding (NORMATIVE)

Frozen against **A2A specification 1.0.0** — canonical source `specification/a2a.proto`
(`package lf.a2a.v1`) in `a2aproject/A2A`. Per the upstream `specification/json/README.md`, the
published `a2a.json` is a *non-normative generated artifact*; the proto is normative, so this
contract is derived from the proto and the spec prose, not from the JSON bundle.

## 1. What is IN v1

**JSON-RPC 2.0 over HTTP(S), with Server-Sent Events for streaming.** Only that.

| Property | Value |
|---|---|
| Transport | HTTP/1.1 or HTTP/2 |
| Endpoint | `POST /rpc` (single endpoint, all methods) |
| Content-Type | `application/json` (requests, unary responses) |
| Streaming Content-Type | `text/event-stream` |
| Method naming | **Bare PascalCase**, matching gRPC method names |
| Field naming | **camelCase** in JSON (`contextId`, `protocolVersion`) — never the proto snake_case |
| Enum encoding | ProtoJSON string names, SCREAMING_SNAKE_CASE (`"TASK_STATE_INPUT_REQUIRED"`, `"ROLE_USER"`) |
| Timestamps | ISO 8601, UTC, `Z` suffix |
| Version header | `A2A-Version: 1.0` — **clients MUST send it on every request** |

> Verified against spec §9.1: *"Method Naming: PascalCase method names matching gRPC conventions
> (e.g. `SendMessage`, `GetTask`)"*. Note this is **not** the 0.x style (`message/send`, `tasks/get`)
> and **not** namespaced (`a2a.SendMessage`) — a plausible-looking mistake that will silently produce
> `MethodNotFoundError`. Implementers: use the bare name.

### Methods

| JSON-RPC `method` | Supported in v1 |
|---|---|
| `SendMessage` | yes |
| `SendStreamingMessage` | yes (SSE) |
| `GetTask` | yes |
| `ListTasks` | yes (scoped to the calling identity) |
| `CancelTask` | yes |
| `SubscribeToTask` | yes (SSE) |
| `GetExtendedAgentCard` | yes |
| `CreateTaskPushNotificationConfig` | **no** → `-32003` |
| `GetTaskPushNotificationConfig` | **no** → `-32003` |
| `ListTaskPushNotificationConfigs` | **no** → `-32003` |
| `DeleteTaskPushNotificationConfig` | **no** → `-32003` |

### Agent Card discovery

`GET /.well-known/agent-card.json` — registered well-known URI suffix `agent-card.json`
(spec §8.2, §14.3). Served unauthenticated. The authenticated **extended** card is
`GetExtendedAgentCard` (JSON-RPC) / `GET /extendedAgentCard`; see authz.md §5 for what differs
between them.

Cards SHOULD be served with `ETag` and honour conditional requests (spec §8.6).

### Request envelope

```http
POST /rpc HTTP/1.1
Host: a2a-shared.fuzeagent.svc.cluster.local:8080
Content-Type: application/json
Authorization: Bearer <OIDC access token>
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "SendMessage",
  "params": {
    "tenant": "FuzePlan",
    "message": {
      "messageId": "1f0c…",
      "role": "ROLE_USER",
      "parts": [{ "text": "Create Jira tickets for the attached requirements." }]
    },
    "configuration": { "returnImmediately": false }
  }
}
```

`tenant` MUST match the `tenant` of the selected `AgentInterface` on the callee's card.

### Streaming frames

```text
data: {"jsonrpc": "2.0", "id": "req-1", "result": { /* StreamResponse */ }}

data: {"jsonrpc": "2.0", "id": "req-1", "result": { /* StreamResponse */ }}
```

Each `StreamResponse` carries a `Task`, `Message`, `TaskStatusUpdateEvent`, or
`TaskArtifactUpdateEvent`.

## 2. What is OUT of v1 (explicitly)

| Binding | Status | Why |
|---|---|---|
| **gRPC** | **OUT** | Requires proto codegen and HTTP/2 plumbing through Traefik for zero present benefit — every v1 caller is in-cluster Python already speaking JSON. Re-evaluate if a non-Python or latency-sensitive consumer appears. |
| **HTTP+JSON / REST** | **OUT** | Redundant with JSON-RPC for agent-to-agent traffic and doubles the adapter's surface. The `:send`/`:stream` custom-verb paths would also need separate Traefik routing. |
| **Push notifications (webhooks)** | **OUT** | No egress webhook path is frozen; `SubscribeToTask` covers the async need in-cluster. |
| **`Part.url` / `Part.raw` inputs** | **OUT** | Large state passes by reference via the handoff memory store. |

These are **binding** omissions, not protocol forks. The card declares exactly one interface, so a
conformant third-party A2A client discovers JSON-RPC and uses it without special-casing. Adding gRPC
later is a purely additive `supportedInterfaces` entry and a **minor** version bump — no breaking
change, which is precisely why deferring them is safe.

## 3. Errors

Standard JSON-RPC codes (`-32700`, `-32600`, `-32601`, `-32602`, `-32603`) plus the A2A range:

| A2A error | JSON-RPC code | Used here for |
|---|---|---|
| `TaskNotFoundError` | `-32001` | Unknown/forbidden task id (see authz.md §6 — indistinguishable on purpose). |
| `TaskNotCancelableError` | `-32002` | `CancelTask` on a terminal task, or `archive_session` failure. |
| `PushNotificationNotSupportedError` | `-32003` | Any push-notification-config method. |
| `UnsupportedOperationError` | `-32004` | `SubscribeToTask` on a terminal task. |
| `ContentTypeNotSupportedError` | `-32005` | `Part.url`/`Part.raw` input; unsupported media type. |
| `InvalidAgentResponseError` | `-32006` | Provider returned an unmappable result. |
| `ExtendedAgentCardNotConfiguredError` | `-32007` | — (extended card is always configured in the Fuze profile). |
| `ExtensionSupportRequiredError` | `-32008` | — (no required extensions in v1). |
| `VersionNotSupportedError` | `-32009` | `A2A-Version` other than `1.0`. |

`error.data` is an **array**, each element carrying `@type` (ProtoJSON `Any`), e.g.
`type.googleapis.com/google.rpc.ErrorInfo` with `reason`/`domain`/`metadata`.

## 4. Transport and network

- **In-cluster (default):** plain HTTP over Kubernetes service DNS
  (`a2a-shared.fuzeagent.svc.cluster.local:8080`). Confidentiality comes from the cluster network
  boundary; identity comes from the OIDC bearer token, never from network position (authz.md §2).
- **External (opt-in, `manifest.a2a.external: true`):** HTTPS only, through the **Cloudflare tunnel**
  to Traefik (`ClusterIP`, tunnel-only — there is no LoadBalancer/NodePort surface), with Cloudflare
  Access in front. Exec-tier agents MUST NOT be published externally.
- A2A requires HTTPS for production deployments (§7.1). The in-cluster exemption is a deliberate,
  scoped deviation: traffic never leaves the cluster network. Any surface reachable outside the
  cluster is HTTPS, no exceptions.
