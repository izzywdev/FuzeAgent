# Argo CD wiring for FuzeAgent — a FuzeInfra delegation

**FuzeInfra owns Argo `Application` and `AppProject` resources.** A product repo
does not author them; two repos independently declaring an Application for the
same workload is the competing-unrestricted-app failure FuzeMarket PR #61
removed. This file is the **handoff spec**, not a manifest.

> **The manifests already in this directory are live wiring. This change
> neither adds, edits nor removes any of them.**

| Existing manifest | Deploys |
|---|---|
| `app-of-apps.yaml` | recursive discovery of `applications/` |
| `applications/fuzeagent.yaml` | `deploy/helm/fuzeagent` — the product chart this change extends |
| `applications/fuzeagent-sealed.yaml` | the sealed-secret bundle |
| `applications/a2a-shared.yaml` | `deploy/helm/a2a-shared` — **the family's only A2A server** |

## The A2A finding — read this first

**`a2a-shared` is wired for deployment, not merely implemented.** This was the
open question for the whole family, so here is the evidence rather than a claim:

- `deploy/argocd/applications/a2a-shared.yaml` exists **on `main`**, targeting
  `path: deploy/helm/a2a-shared`, `targetRevision: main`,
  `valueFiles: [values-prod.yaml]`, `destination.namespace: fuzeagent`, with
  `automated: {prune: true, selfHeal: true}`.
- `deploy/helm/a2a-shared/values-prod.yaml` **on `main`** has `a2a.enabled: true`
  and a pinned image `ghcr.io/izzywdev/fuzeagent-a2a:e2d7d1c2b55a`.
- `helm template` against those prod values renders a **Deployment and a Service
  both named `a2a-shared`, port 8080**, whose selector matches exactly one
  workload — i.e. precisely the address the image hardcodes on every Agent Card
  (`agent-templates/a2a/card_generator.py:29`,
  `http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc`). The chart's
  `_helpers.tpl` pins that name deliberately and says why.
- Three tenants are enabled in those values: `FuzeAgent`
  (entryRole `agent-orchestrator`), `FuzeFront` (`app-shell-platform`, ref
  `master`), `FuzePlan` (`product-manager`).
- The four SealedSecrets it needs (`a2a-provider-anthropic`, `a2a-mtls-ca`,
  `a2a-card-signing`, `a2a-repos-git`) are rendered by the chart itself.

**What could NOT be verified from here:** whether the pod is actually *running
and healthy* in the cluster. There is no cluster access in this session, by
constraint. Everything above is GitOps declaration, which is the source of
truth for what Argo will apply — but "declared" is not "up".

Two things to check on the cluster before relying on the surface:

1. `kubectl -n fuzeagent get deploy,svc a2a-shared` and the pod's `/healthz`.
2. The repo-sync init container clones each tenant at its `ref`. **FuzePlan is a
   private repo**, so the `a2a-repos-git` SealedSecret must carry a token that
   can read it, or that tenant's card projection fails.

One dead value, noted while reading: `deploy.stateConfigMap: a2a-state` is set
in `values-prod.yaml` but `templates/deployment.yaml` mounts an `emptyDir` for
`/state` and never references it. Nothing creates a ConfigMap called
`a2a-state`. Harmless today (the mount works), but the value is a no-op.

## What FuzeAgent needs for the product chart

| Field | Value |
|---|---|
| `repoURL` | `https://github.com/izzywdev/FuzeAgent.git` |
| `path` | `deploy/helm/fuzeagent` |
| `targetRevision` | `main` |
| `helm.valueFiles` | `values-prod.yaml` |
| `destination.namespace` | `fuzeagent` |
| `syncOptions` | `CreateNamespace=true` |

## What this change adds to the render

One new workload, behind its own gate, **shipping OFF**:

| Pod | Gate | Ships as | To flip it |
|---|---|---|---|
| backend (`orchestrator`) | `orchestrator.enabled` | **on** (unchanged) | — now also serves `GET /openapi.yaml` |
| frontend (`ui`) | `ui.enabled` | **on** (unchanged) | — |
| MCP SSE gateway (`fuzeagent-mcp`) | `mcp.enabled` | **off** | needs `ghcr.io/izzywdev/fuze-mcp-gateway:0.1.0` in GHCR |
| A2A (`a2a-shared`) | separate chart | **on** | already deployed — see above |

With `mcp.enabled: false` the rendered set is identical to today's apart from
one added env var on the orchestrator (`OPENAPI_SPEC_PATH`).

**Note the namespace ResourceQuota.** `resourceGovernance.quota` allows 20 pods
and `limitsCpu: 6`. The MCP pod requests 50m/64Mi and limits 500m/256Mi, which
fits, but the quota is already sized deliberately for `a2a-shared` plus its
rolling-update surge — worth re-checking before enabling.

## Infrastructure assumptions to confirm

None was verified against a live cluster:

- **Ingress class `traefik`** behind the Cloudflare tunnel; only `/` is routed,
  to the `ui` Service, whose nginx reverse-proxies `/api/orchestrator` and
  `/api/hierarchy` same-origin.
- **`ghcr.io/izzywdev/fuze-mcp-gateway:0.1.0` exists in GHCR.** It is FuzeFront's
  image and **no workflow in this repo builds it**. If absent, flipping
  `mcp.enabled` gives `ImagePullBackOff`, not a working pod.
- **`ghcr-pull` image pull secret** and `fuzeagent-secrets` exist in the
  namespace — existing workloads already depend on both.
- **`release.yml` builds the orchestrator image on push to `main`** matching
  `services/orchestrator/**`, so the new `GET /openapi.yaml` route and the
  contract copy inside the image ship on the next release. That path filter does
  **not** include `contracts/**`, which is why the contract is synced into
  `services/orchestrator/contracts/` rather than referenced across the tree.
