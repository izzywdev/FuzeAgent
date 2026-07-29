# FuzeFront registration

FuzeAgent self-registers with the FuzeFront portal at deploy time.

| File | Purpose |
|---|---|
| `manifest.json` | App identity, Module-Federation contract, `nav` placement |
| `policy.json` | FuzeAgent's own Permit resources/roles, bare keys |
| `register.sh` | Idempotent registration script from `@fuzefront/onboarding-kit` |

## This replaces a hardcoded entry in FuzeFront

FuzeAgent is currently one of only three apps in the portal, and it is registered by a
**hardcoded entry in FuzeFront's `backend/applications/src/app-registry/builtins.ts`** —
i.e. FuzeFront's source has to change for FuzeAgent's portal presence to change. Once
this self-registration is live, that builtin can be retired (deliberately last, and
behind a flag, so the app never vanishes from the menu in the gap).

## Module Federation is real here

Unlike most siblings, `integration.type` is genuinely `module-federation`. The
contract in `manifest.json` is copied from `services/ui-react/vite.config.ts`:

| Field | Value | Source |
|---|---|---|
| `scope` | `fuzeagentApp` | federation `name` |
| `module` | `./FuzeAgentApp` | `exposes` key |
| `remoteEntry` | `https://fuzeagent.prod.fuzefront.com/remoteEntry.js` | `filename` + host |

React and react-dom are shared singletons, so FuzeFront's React instance is reused —
which is what makes mounting into the host shell work at all.

## Menu placement

```jsonc
"nav": { "section": "build", "order": 10 }
```

FuzeAgent leads the **build** stage. Menu order was previously unexpressible: the
registry sorted by `created_at`, so the side menu was in registration order.

## Policy

Derived from `services/orchestrator/models.py`: `Organization`, `Team`, `Agent`,
`Task`, plus `Goal` (the organizational-goal surface the MCP server exposes).

`Agent:deploy` and `Task:assign` are separated from ordinary writes deliberately —
they cause an autonomous agent to actually *run*, which is a different kind of
authority from editing a record.

## MCP is already real

`.fuze/manifest.json` declares `mcp.enabled: true` — not a scaffold.
`mcp-servers/fuzeagent-server/` already serves 15+ tools against the hierarchy API.

**Outstanding:** a `tools.json` declaring `mutates` per tool. Several tools mutate and
must be classified `mutates: true`:

- `assign_task`, `deploy_agent`, `create_custom_agent`, `update_task_status`,
  `create_organizational_goal`, `update_goal_progress`, `create_goal_conversation`

The `list_*` / `get_*` tools are `mutates: false`. `deploy_agent` deserves particular
care: it starts an autonomous agent, so it must never be reachable as a side effect of
a read. Classification is `mcp-maintainer`'s to reconcile.

## A2A is also real

`agent-templates/a2a/` implements card generation, the adapter, authz and identity, and
`agent-templates/roles/agent-orchestrator/role.json` is a fully-described serving role.
The manifest names it accurately but leaves `enabled: false`: flipping it requires
verifying the card projects schema-valid against the frozen contract, which is
`a2a-maintainer`'s call rather than a manifest edit's.

## NOT DONE — init container not wired

`deploy/helm/fuzeagent/` exists, but this repo is a multi-service deployment and
exactly one deployment must run registration; wiring more than one would have them race
and duplicate-register. Choosing the owner is `devops-engineer`'s call and is flagged
rather than guessed. To finish: paste the init container from
[`@fuzefront/onboarding-kit`](https://github.com/izzywdev/FuzeFront/blob/master/packages/onboarding-kit/helm/initcontainer.yaml)
into that one pod spec, and create the `fuzefront-registration` Secret plus a ConfigMap
of this directory.
