# Run your own A2A pod (per-product deployment)

**Owner decision: each product gets its OWN A2A agent pod**, rather than a tenant row on
the one shared server. This page is the recipe: the values a product chart must set, the
secrets it needs, and what the product repo itself must contain.

Compartmentalisation is the reason. One pod per product means one blast radius per
product: a wedged repo checkout, an exhausted provider key, a crash loop or an OOM in
*your* agent stops *your* agent, not FuzeAgent's, FuzeFront's and FuzePlan's at once. It
also means your pod scales, restarts and rolls on your schedule, in your namespace, with
your Argo Application.

> **This does not remove the shared server.** `a2a-shared` (namespace `fuzeagent`) keeps
> serving its existing tenants unchanged. Both topologies run the *same* image and the
> *same* values document; see [Two topologies, one server](#two-topologies-one-server).

---

## The blocker this replaces (read this first — it explains the one required value)

Until contract **v1.2.0** the in-cluster endpoint a card advertised was a **constant in
the card generator**:

```python
IN_CLUSTER_URL = "http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc"
```

`_interface()` returned it for every non-external card. So a per-product pod would come
up, pass every probe, serve a perfectly valid signed card — and that card would name
**the shared server**. A caller doing the correct thing (fetch card → follow
`supportedInterfaces[0].url`) would be routed to a pod that never heard of it. Nothing
was unhealthy; the deployment was simply undiscoverable through its own card. That is why
every product's A2A pod shipped disabled.

The fix is one value, `a2a.inClusterUrl`. **If you set nothing else on this page
correctly, set that.** The card is the callable contract — a pod that advertises an
address it does not own is unreachable no matter how green its probes are.

---

## 1. What the product REPO must contain

The card is a **pure projection** of two files in your repo (card-projection.md). The pod
reads them from a checkout at `/repos/<tenant>`; there is no hand-authored card and no
fallback. **Both must exist on the served `ref` or the pod fails to project a card.**

### `.fuze/manifest.json`

```jsonc
{
  "repo": "izzywdev/FuzePlan",
  "tier": "product",
  "providesTo": ["FuzeSales", "FuzeService"],   // WHO MAY CALL YOU — absent == DENY ALL
  "a2a": {
    "entryRole": "product-manager",              // serves a SendMessage naming no skill
    "servingRoles": ["product-manager", "ux-designer"]   // optional; else all eligible roles
  }
}
```

- **`providesTo` is a hard precondition, not a follow-up.** The authorization model fails
  closed: absent means DENY every caller, and `[]` also means DENY (authz.md §3). Turning
  on a pod without it gives you an agent nobody can call — and the rejection is
  deliberately indistinguishable from "no such tenant" (non-disclosure), so it is easy to
  misread as a routing bug.

### `agent-templates/roles/<entryRole>/role.json`

```jsonc
{
  "role": "product-manager",
  "name": "FuzePlan product-manager",
  "description": "Turns a product requirement into an epic and its tickets."
}
```

- The role key **is** the skill `id` — the join key the adapter uses to resolve an
  incoming `skillId` back to a role.
- `description` is **required**. An undescribed skill is unroutable, so the projection
  **fails loudly** rather than emitting a placeholder. A pod whose `entryRole` has no
  `role.json`, or a `role.json` with no `description`, cannot serve a card at all.
- `_base`, any `coordinator: true` role and any role with `a2a.publish: false` are never
  projected.

Verify the projection **before** deploying anything — it needs no cluster and no LLM:

```bash
cd agent-templates/a2a
python -c "
from a2a import card_generator as cg
from a2a.loader import load_repo
from a2a.validation import card_errors
m, r = load_repo('/path/to/your/repo')
card = cg.project_product_card(
    m, r, in_cluster_url='http://a2a-<product>.<ns>.svc.cluster.local:8080/rpc')
print(card['supportedInterfaces'][0])
print('errors:', card_errors(card) or 'none')
"
```

If that prints your endpoint and `errors: none`, the pod will serve the same card.

---

## 2. The values a product chart must set

The document is the frozen values interface
([`values-interface.schema.json`](../../agent-templates/contracts/a2a/v1/schema/values-interface.schema.json)),
unchanged except that `a2a.inClusterUrl` now exists. It is
`additionalProperties: false` at every level — you cannot add a key of your own, and a
typo is a validation failure rather than a silently ignored value.

```yaml
a2a:
  enabled: true

  image:
    repository: ghcr.io/izzywdev/fuze-a2a    # the SAME image; there is no per-product image
    tag: <immutable-sha>                          # never `latest` in prod
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP        # MUST be ClusterIP — ingress is Cloudflare-tunnel-only
    port: 8080             # there is NO port env var; this is the listen port AND the Service port

  protocolVersion: "1.0"

  # ⇩⇩ THE ONE VALUE A PER-PRODUCT POD MUST NOT GET WRONG ⇩⇩
  # Must equal what YOUR Service resolves to: scheme + Service DNS + port + /rpc.
  # Unset would default to the SHARED server and your pod would be unreachable
  # through its own card.
  inClusterUrl: http://a2a-fuzeplan.fuzeplan.svc.cluster.local:8080/rpc

  auth:
    oidcIssuerUrl: https://app.fuzefront.com/application/o/fuzefront/   # the `iss` anchor
    oidcDiscoveryUrl: http://authentik-server.fuzefront.svc.cluster.local:9000/application/o/fuzefront/.well-known/openid-configuration
    audience: a2a
    callerClaim: repo      # the claim carrying the caller repo name — the ONLY trusted identity
    mtls:
      enabled: true
      caSecretRef: { name: a2a-mtls-ca, key: ca.crt }

  cardSigning:
    keySecretRef: { name: a2a-card-signing, key: jws.key }
    keyId: a2a-v1

  # A per-product pod serves ONE tenant. Exactly one entry.
  tenants:
    - tenant: FuzePlan                 # MUST equal the card's AgentInterface.tenant
      repo: izzywdev/FuzePlan          # projection source
      ref: main                        # YOUR default branch (FuzeFront's is `master`)
      enabled: true                    # the per-tenant gate, independent of a2a.enabled
      entryRole: product-manager
      external: false
      provider:
        name: anthropic
        apiKeySecretRef: { name: a2a-provider-anthropic, key: api-key }
```

### Values that are NOT in the `a2a` block

Pure deployment mechanics live in a sibling `deploy:` block that the contract deliberately
does not define (no templates are implied by an interface). Copy the shape from
[`deploy/helm/a2a-shared/values.yaml`](../../deploy/helm/a2a-shared/values.yaml):
`replicas`, `imagePullSecrets`, `resources`, `ingressClassName`, `externalDomain`,
`agentProvider`, `gitImage`, `reposGitTokenSecretRef`, `providerApiKeySecretRef`,
`stateConfigMap`.

**`inClusterUrl` is deliberately NOT one of them.** It sits inside `a2a` because that
block is what the chart serialises verbatim into the `values.json` the server parses
(`config.load_config`); a key under `deploy:` never reaches the server, and reaching it
would require inventing an env var. Substantively it is a *card-projection input* — the
published callable endpoint, like `auth.oidcIssuerUrl` — not a chart knob like `replicas`.

### Two gates, both must be on

`a2a.enabled: true` **and** `tenants[0].enabled: true`. Same convention as everything else
on FuzeInfra, one level deeper.

---

## 3. Secrets

All are `{name, key}` references to existing Kubernetes Secrets, SealedSecret-provisioned
**in your product's namespace**. Secret *values* never appear in values.yaml or in git.
A shared-server SealedSecret is sealed for `fuzeagent/<name>` under kubeseal's strict
scope and **cannot be reused in another namespace** — you must seal your own.

| Secret | Referenced by | Required? |
|---|---|---|
| `a2a-provider-anthropic` (`api-key`) | `provider.apiKeySecretRef` + `deploy.providerApiKeySecretRef` (exported as `ANTHROPIC_API_KEY`) | Yes, for any real provider |
| `a2a-card-signing` (`jws.key`) | `cardSigning.keySecretRef` | Yes in prod — the Fuze profile requires non-empty `signatures[]` |
| `a2a-repos-git` (`token`) | `deploy.reposGitTokenSecretRef` | Only if YOUR repo is private (the init container clones it) |
| `a2a-mtls-ca` (`ca.crt`) | `auth.mtls.caSecretRef` | Only if `auth.mtls.enabled: true` |
| `ghcr-pull` | `deploy.imagePullSecrets` | Yes — the image is in private GHCR |

> Card signing is still key-material-only: the server reads `cardSigning.keyId`, and
> `card_generator.sign_card` emits a deterministic **placeholder** signature until a real
> JWS signer is injected. That gap is identical on the shared server and is not made
> worse by a per-product pod.

---

## 4. Pod shape

Use [`deploy/helm/a2a-shared`](../../deploy/helm/a2a-shared) as the reference
implementation — the templates are small and the per-product chart is the same objects
with your names. What the container actually requires:

**Env** — exactly the surface the image defines. There are no others, and no port var:

| Var | Value |
|---|---|
| `HOST` | `0.0.0.0` (the server defaults to loopback, so the Service cannot reach it unset) |
| `A2A_VALUES_FILE` | `/config/values.json` — the `{"a2a": {...}}` document above |
| `A2A_REPOS_DIR` | `/repos` |
| `AGENT_PROVIDER` | `anthropic` |
| `FUZE_STATE_DIR` | `/state` |
| `ANTHROPIC_API_KEY` | from `providerApiKeySecretRef` |

**Volumes**

- `/config` — ConfigMap holding `values.json` (`{{ dict "a2a" .Values.a2a | toJson }}`).
  Annotate the pod template with its checksum so a values change rolls the pod.
- `/repos` — `emptyDir`, filled by an init container that shallow-clones your repo at
  `ref` into `/repos/<tenant>` (**keyed on the TENANT name**, not the repo slug).
- `/state` — writable `emptyDir` for `FUZE_STATE_DIR`.

**Service** — `ClusterIP`, port `8080`, and its DNS name **must match
`a2a.inClusterUrl`**. This is the one cross-check to make on every render.

**Probes** — `GET /healthz`. Keep the shared chart's tolerant tuning: a `startupProbe`
with a long `failureThreshold` (repo clone + boot) and a 5s liveness timeout. The shared
deployment was being killed by the default 1s timeout under cluster strain.

**Security context** — image runs as non-root UID `10001`; set `runAsNonRoot`,
`runAsUser: 10001`, `fsGroup: 10001`, `allowPrivilegeEscalation: false`, drop all caps.

---

## 5. Verify after rollout

```bash
# 1. The card names YOUR pod. A single-tenant pod needs no ?tenant=.
kubectl -n <ns> exec deploy/<a2a-pod> -- \
  python -c "import urllib.request,json; \
    print(json.load(urllib.request.urlopen('http://127.0.0.1:8080/.well-known/agent-card.json'))['supportedInterfaces'])"
```

The `url` must be your Service, **not** `a2a-shared.fuzeagent.svc.cluster.local`. If it
says `a2a-shared`, `inClusterUrl` is unset or misspelled — that is the whole failure mode
this page exists for, and it looks completely healthy from every other angle.

```bash
# 2. It is reachable at the address it advertises (from another namespace).
kubectl -n <other-ns> run curl --rm -it --image=curlimages/curl --restart=Never -- \
  curl -s http://a2a-<product>.<ns>.svc.cluster.local:8080/healthz
```

Then a real `SendMessage` from an allowlisted caller. Note the caller **must echo
`tenant`** in `params` — the shipped `A2AClient` does this automatically from the card, but
a hand-rolled caller that omits it gets a generic `TASK_STATE_REJECTED` (fail-closed,
non-disclosing), which reads like an authz failure and is not.

---

## Two topologies, one server

| | Shared server (`a2a-shared`) | Per-product pod |
|---|---|---|
| Deployments | 1, namespace `fuzeagent` | 1 per product, in its own namespace |
| `a2a.tenants[]` | many | exactly one (plus that repo's `Exec-<role>` tenants, if it serves any) |
| `a2a.inClusterUrl` | unset → default | **set to its own Service** |
| Card discovery | `?tenant=` selects | no query param needed |
| Blast radius | all tenants | one product |
| Image / server code | identical | identical |

Onboarding onto the shared server is still just a `tenants` entry —
[enable-your-pod.md](enable-your-pod.md) covers that path and remains correct.

## Checklist

1. [ ] `providesTo` present in your `.fuze/manifest.json`, naming every allowed caller.
2. [ ] `agent-templates/roles/<entryRole>/role.json` exists on the served `ref`, with a non-empty `description`.
3. [ ] `ref` is YOUR default branch (`main` vs `master` — FuzeFront is `master`).
4. [ ] `a2a.inClusterUrl` equals your Service's DNS name, port and `/rpc` path.
5. [ ] `a2a.enabled: true` **and** the single `tenants[0].enabled: true`.
6. [ ] `service.type: ClusterIP`; `external: false` unless you genuinely want a tunnel host.
7. [ ] SealedSecrets sealed **for your namespace** (they are not portable).
8. [ ] `HOST=0.0.0.0` set; `/config`, `/repos`, `/state` mounted; repo-sync init container clones to `/repos/<tenant>`.
9. [ ] Card fetched after rollout advertises YOUR endpoint.
