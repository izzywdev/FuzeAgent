# Fuze Sandbox remote provider

FuzeAgent now has an opt-in asynchronous API client and a remote-workspace
provider in `services/orchestrator/sandbox_manager.py`. The default remains
Docker. The remote provider stores the Sandbox resource ID in the existing
`agent_sandboxes` record, preserves remote workspaces over FuzeAgent process
restarts, and delegates expiry, tenant isolation, quotas, and cleanup to Fuze
Sandbox. The client also exposes Job creation/status/log/cancel, workspace
command/file methods, and preview-grant creation.

## Security boundary

The Fuze Sandbox API key is held by the FuzeAgent service configuration and is
never sent to a workspace. FuzeAgent's Anthropic/provider keys and its
database credentials stay server-side. Remote workspaces receive no arbitrary
provider credentials or secret values. FuzeAgent may request non-secret
environment values, references to operator-provisioned Secrets in that tenant's
namespace, and a bounded non-root init script. The Sandbox API rejects
credential-like environment names; `secret_env` carries only Secret name/key
references and never values. Sandbox image, profile, CPU/memory/storage limits,
runtime class, namespace, and TTL are enforced by the Sandbox service.
The API key must be tenant-bound and include only the operations FuzeAgent
needs: `sandbox:create`, `sandbox:read`, `sandbox:cancel`, `workspace:exec`,
`workspace:files:read`, `workspace:files:write`, and `workspace:preview` when
preview access is required. Never pass tenant IDs from callers; Sandbox derives
the tenant from the API key.

## Configuration

Set these in the FuzeAgent orchestrator's protected deployment configuration,
not in a committed values file:

```text
FUZE_SANDBOX_PROVIDER=fuze-sandbox
FUZE_SANDBOX_API_URL=https://api.sandbox.seaw.dev
FUZE_SANDBOX_API_KEY=<Vault-injected tenant key>
FUZE_SANDBOX_IMAGE=<operator-allowlisted image digest>
FUZE_SANDBOX_PROFILE=agent-small
FUZE_SANDBOX_TTL_SECONDS=86400
FUZE_SANDBOX_WORKSPACE_STORAGE=5Gi
FUZE_SANDBOX_PREVIEW_PORTS=3000
```

Before the manager starts, it requires `/readyz` to report execution enabled,
worker ready, and machine workspace support enabled. A missing URL, key, image,
unready worker, disabled machine API, or unavailable API fails startup rather
than falling back to Docker. Set `FUZE_SANDBOX_PROVIDER=docker` to use the
existing local Docker provider. Do not set both providers as a fallback chain.

## Operations

- A remote workspace remains alive when FuzeAgent shuts down; the service's
  server-side TTL and idle timeout remain authoritative.
- `AgentSandboxManager.execute_command` returns exit code, output, and success
  from a shell exit marker. The command must fit within the Sandbox API's
  4096-character limit.
- File transfers are limited to 1 MB and restricted by the Sandbox API to
  `/workspace` paths. Preview grants are short-lived and bound to declared
  workspace ports; preview URLs must not contain the Fuze Sandbox API key.
- FuzeAgent restart recovery uses the persisted `fuze-sandbox:<resource-id>`
  provider marker. Switching providers leaves records belonging to the other
  provider untouched.
- When remote workspaces are unavailable, the manager reports a bounded error
  without exposing response bodies or credentials. No local Docker fallback
  occurs in remote mode.

## Current integration boundary and remaining work

The authenticated `/sandboxes` API supports remote Job or workspace creation,
status/list/log retrieval, command execution, file transfer, preview-grant
creation, and deletion. A remote sandbox is always bound to the verified JWT
`sub`; callers cannot choose an owner or tenant. The service key remains
server-side. The default Docker provider and its existing local operations are
retained.

Workspace requests accept the validated 60-second to 24-hour TTL and use the
operator-configured image, profile, storage size, and preview ports. Job command
and argument bounds are validated before calling the service; invalid requests
return a client error instead of a provider error.

The existing `TaskExecutionEngine` Git workflow, `FileOperationsEngine`, and
`ClaudeSDKManager` still operate on a local host path and start the Claude Code
process in that local filesystem. They have not yet been migrated to remote
filesystem/command operations. Selecting the remote provider for autonomous
TaskExecutionEngine jobs therefore fails closed and is not an end-to-end
supported configuration. No model-token broker or restricted GitHub App
credential broker has been implemented. Private repository checkout still
needs a safe, short-lived GitHub App credential design that does not expose
repository tokens to untrusted workspace commands. Keep Docker selected for
TaskExecutionEngine jobs; use the remote provider through the direct sandbox
API only until that migration, broker, runner image, and end-to-end acceptance
are implemented.

The Sandbox API currently has machine workspace operations disabled by default.
The Seaw operator must add the shared API/worker secret in Vault, deploy the
chart and explicit Vault token audiences, verify worker authentication, then
enable the feature and run a disposable command/file/preview test before this
provider can start.
