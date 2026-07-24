# Go-live checklist

Turning a product's A2A pod on in prod, and the deployment gotchas we hit bringing
FuzeAgent up first. Prod is **GitOps** — every change lands via Git and Argo syncs it;
never `kubectl patch`/`edit` a live A2A resource (Argo selfHeal reverts it).

The chart, image, and Argo Application are **devops-engineer's** slice; this page is the
operator runbook that consumes them.

---

## 1. Preconditions (before you flip `enabled`)

1. **Backfill `providesTo`** on the callee's `.fuze/manifest.json` — the authZ allowlist.
   Absent/empty = DENY every caller (authz.md §3). Non-negotiable first step.
2. **A serving role exists** — the tenant's repo has `agent-templates/roles/<entryRole>/role.json`.
   The card projects its `skills` from the repo's roles (card-projection.md §2); a tenant
   with no serving role yields an empty/failing card. Keep the tenant `enabled:false`
   until this ships.
3. **The four SealedSecrets exist** in the `fuzeagent` namespace (the shared server reads
   them; missing ones wedge the pod at `Init`/`CreateContainerConfigError`):

   | SealedSecret | key | what |
   |---|---|---|
   | `a2a-provider-anthropic` | `api-key` | the Managed-Agents provider key |
   | `ghcr-pull` | `.dockerconfigjson` | pull the private image |
   | `a2a-mtls-ca` | `ca.crt` | in-cluster mTLS CA (defence in depth) |
   | `a2a-card-signing` | `jws.key` | JWS key that signs the served card |

   Generate + seal them with `kubeseal` against the `kube-system/sealed-secrets-controller`
   and commit the sealed manifests (they're encrypted — safe to commit).

---

## 2. Enable a tenant (the actual onboarding — it's data)

One shared server, so onboarding is a `tenants` entry in the a2a-shared values, not a
new deployment (enable-your-pod.md):

```yaml
a2a:
  tenants:
    - tenant: FuzePlan
      repo: izzywdev/FuzePlan
      ref: main
      enabled: true            # only after the serving role (precondition 2) ships
      entryRole: product-manager
      external: false
      provider: { name: anthropic, apiKeySecretRef: { name: a2a-provider-anthropic, key: api-key } }
```

Commit → Argo syncs → the shared server clones the tenant repo and serves its card.

---

## 3. Register a **caller** identity (only needed to CALL others)

A callee needs no client credential — it validates incoming tokens with the issuer's
public JWKS. A **caller** needs an OIDC identity so its token carries `repo=<Repo>`,
`aud=a2a`. Provision it in-cluster (prod Authentik admin, never from CI/laptop):

```bash
kubectl -n fuzefront exec deploy/<backend> -- \
  env AUTHENTIK_BASE_URL=http://authentik-server:9000 \
  node dist/authentik/register-a2a-cli.js <Repo>     # e.g. FuzeFront
```

It prints the `client_id` (safe to share) and a masked secret; retrieve the full secret
from the Authentik UI and seal it on the caller's side. FuzeFront needs this before it
can call FuzePlan (worked example, step 4).

---

## 4. Verify

`GET /.well-known/agent-card.json` on the pod returns a schema-valid, **signed** card
whose `skills` match the tenant's roles. The image lacks `curl`/`wget`, so probe with
its Python:

```bash
kubectl -n fuzeagent exec deploy/a2a-shared -c a2a-shared -- \
  python -c "import urllib.request as u,json; print(json.load(u.urlopen('http://127.0.0.1:8080/.well-known/agent-card.json')))"
```

`url`/`protocolVersion` live inside the single interface (`additionalInterfaces`), **not**
at the top level — top-level nulls there are correct, not a bug (call-another-agent.md §1).

---

## 5. Deployment gotchas we hit (so you don't)

These bit the FuzeAgent bring-up and are fixed in the chart/image, but know them — CI
couldn't catch them because the acceptance gate ran from a source checkout where every
runtime file-read "worked":

1. **`ResourceQuota` headroom.** The pod won't schedule if the namespace CPU quota is
   maxed (`FailedCreate ... exceeded quota`). Raise `limits.cpu` first.
2. **`/state` must be a writable `emptyDir`.** `FUZE_STATE_DIR=/state` is where the
   server persists in-flight session state — a read-only ConfigMap mount wedges the pod
   at `Init`. (Fixed in the chart.)
3. **repo-sync clones to `/repos/<tenant>` (case-preserved).** The server resolves the
   repo by the **tenant** name, not a lowercased slug — a mismatch 500s the card.
4. **The image must vendor `contracts/a2a/v1/`.** `card_generator` reads
   `/app/contracts/a2a/v1/VERSION` + `schema/` at runtime; the Dockerfile must `COPY` the
   contract dir, not only its `client/` subtree.
5. **`release.yml`'s GitOps tag-bump can't self-merge.** Its auto tag-bump PR races and
   is blocked from self-approval, so after a release you currently bump the image tag in
   `values-prod.yaml` manually with a `[skip ci]` commit. (Tracked for a proper fix —
   switch to a direct commit or admin token.)
