# a2a-shared — the ONE shared A2A server (deploy runbook)

A single Deployment/Service (`a2a-shared` in namespace `fuzeagent`) fronts **every**
tenant. Onboarding a repo is an `a2a.tenants[]` entry — **DATA, never a new chart or
pod**. The operator surface is frozen by the contract:
`agent-templates/contracts/a2a/v1/schema/values-interface.schema.json`
(`binding.md`, `card-projection.md`, `authz.md`). This chart implements exactly that
surface; deploy mechanics (`deploy.*`) are kept out of the `a2a` block so it stays
byte-conformant to the interface.

- **In-cluster (default):** `http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc`
  and `…/​.well-known/agent-card.json`. HTTP; identity is the OIDC bearer, never network
  position (`authz.md §2`).
- **External (opt-in per tenant `external: true`):** `https://a2a.<repo-slug>.prod.fuzefront.com/rpc`
  through the Cloudflare tunnel → Traefik (ClusterIP). Exec-tier tenants MUST be
  `external: false` (`card-projection.md §5`). No LoadBalancer/NodePort surface.

**Prod is GitOps** (Argo CD `a2a-shared` Application, `selfHeal: true`). Never
`kubectl apply/patch/edit` — change values in git and let Argo reconcile.

## Ships DISABLED — go-live preconditions (out of this chart's scope)

`values-prod.yaml` sets `a2a.enabled: false`, so the Argo app renders nothing until:

1. **Server image exists** — `ghcr.io/izzywdev/fuzeagent-a2a` is built by `release.yml`
   from `agent-templates/a2a/` (backend-engineer). The tag is auto-bumped in
   `values-prod.yaml` on merge.
2. **`providesTo` backfill** — `authz.md §3` is fail-closed (absent `providesTo` == DENY).
   Backfilling it on every served repo's manifest is a **precondition**, not a follow-up.
3. **Card-signing SealedSecret** — the Fuze profile requires non-empty `signatures[]`
   (`card-projection.md §6`).

## Go-live (single GitOps PR, human-gated)

1. Provision the SealedSecrets in `deploy/contabo/sealed/` (synced by `fuzeagent-sealed`):
   - `a2a-provider-anthropic` (key `api-key`) — Managed-Agents key, exported as
     `ANTHROPIC_API_KEY` for session provisioning; set `deploy.providerApiKeySecretRef`.
   - `a2a-repos-git` (key `token`) — token for cloning PRIVATE tenant repos in the
     repo-sync init container; set `deploy.reposGitTokenSecretRef`. Omit for public repos.
   - `a2a-mtls-ca` (key `ca.crt`) if in-cluster mTLS is enabled.
   - Card-signing: the server reads `cardSigning.keyId` from the values doc; the JWS
     signer injection is still a server-side TODO ("production injects a real JWS signer"
     in `card_generator.py`), so no signing-key env is wired yet.
   Seal with `scripts/seal-secret.sh` (same flow as handoff-mcp).
2. Provide the Managed-Agents id-state (agent/vault/memory/environment ids) as a ConfigMap
   mounted at `FUZE_STATE_DIR=/state` — same mechanism as handoff-mcp — and set
   `deploy.stateConfigMap`.
3. In `values-prod.yaml`: set `a2a.enabled: true`, uncomment `auth` (real family OIDC
   issuer) + `cardSigning`, and add the `tenants[]` (only repos whose `providesTo` is
   backfilled). Keep the single `tag:` line — `release.yml` owns it.
4. Merge → Argo syncs the Deployment/Service (+ the `values.json` ConfigMap the server
   reads via `A2A_VALUES_FILE`, the repo-sync init container, per-external-tenant Ingress).

### Runtime shape (matches the merged server, `agent-templates/a2a/`)
- Entrypoint `python -m a2a.runtime` → `build_from_env()` reads `A2A_VALUES_FILE`
  (the `a2a` block as JSON), `A2A_REPOS_DIR=/repos`, `AGENT_PROVIDER`, `HOST`.
- The image vendors `a2a/` + `providers/` + `sync/` (runtime imports `providers`, whose
  anthropic adapter delegates to the `sync/` modules) + the frozen `fuze_a2a_client`.
- Per-tenant card projection reads each repo's `.fuze/manifest.json` + `roles/` from
  `/repos/<repo-name>`, populated by the `repo-sync` init container at each tenant `ref`.

## Validate (matches `helm-validate.yml`)

```bash
helm lint deploy/helm/a2a-shared
helm lint deploy/helm/a2a-shared -f deploy/helm/a2a-shared/values-prod.yaml
# enabled path (default/prod render nothing while gated off):
helm template a2a-shared deploy/helm/a2a-shared -f deploy/helm/a2a-shared/ci/enabled-values.yaml \
  | kubeconform -strict -summary -kubernetes-version 1.29.0 -ignore-missing-schemas
```

> Remaining server-side gap (tracked, non-blocking): a real JWS card signer injection
> (`card_generator.py` — "production injects a real JWS signer"). The health/readiness
> probe uses the server's `GET /healthz`. None block validation; the chart renders and
> passes kubeconform, and the image composes the app from the chart's `values.json`.
