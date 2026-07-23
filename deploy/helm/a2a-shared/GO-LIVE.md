# A2A `a2a-shared` — production go-live checklist (FuzeAgent-first)

Prod is **GitOps** (Contabo k3s, Argo CD `a2a-shared` Application, `values-prod.yaml`). Nothing is
hand-deployed. This overlay is staged to `enabled: true` in the rollout PR, but Argo renders it only
once the PR **merges to `main`** — and it will not run correctly until the items below exist.

**None of these can be done by an automated agent** — they are real credentials/config that only the
owner (or the sealed-secrets flow) can provide. The rollout PR leaves `REPLACE_ME` placeholders and
`secretRef` names; you fill the values and seal the secrets.

## 1. Owner-supplied config (edit `values-prod.yaml`)

| Field | What to set |
|---|---|
| `a2a.auth.oidcIssuerUrl` | **Set** to FuzeFront's prod Authentik issuer `https://app.fuzefront.com/application/o/fuzefront/` (from FuzeFront `deploy/helm/fuzefront/values-prod.yaml`). Already filled in `values-prod.yaml`. |
| `a2a.tenants[0].entryRole` | **Set** to `agent-orchestrator` (the serving role added in #94). Already filled. |

### 1b. Machine-identity integration with FuzeFront — RESOLVED (FuzeFront#364)

FuzeFront (identity owner) decided **Option 2: issue repo-name JWTs**, not introspection. Rationale:
it fits the frozen A2A contract (standard stateless JWT validation, no `authz.md §2` amendment),
avoids handing every A2A pod its own introspection credential + a round-trip per call, and removes
the `client_id → repo` lookup that introspection would still require (`sub` is
`hashed_user_id`; the only stable key today is the opaque `client_id`).

**Mechanism:** an Authentik **scope mapping** on each A2A machine provider emits a stable claim,
`{"repo": "<RepoName>", "aud": "a2a"}`. Authentik OAuth2 access tokens are JWTs signed by the
provider and published at the issuer's JWKS, so standard validation works.

**Resolved A2A `auth` values (now in `values-prod.yaml`):**
- `callerClaim: repo` — the custom claim carrying the exact repo name (the allowlist key).
- `audience: a2a` — one dedicated M2M audience across all A2A providers (NOT the human `fuzefront` app).
- `oidcIssuerUrl` (the `iss`) stays the public `https://app.fuzefront.com/application/o/fuzefront/`
  (`issuer_mode: global`), **but JWKS/discovery is fetched in-cluster** to avoid a Cloudflare-tunnel
  hairpin (FuzeFront hit 17–34 s hairpin timeouts before):
  `http://authentik-server.<fuzefront-ns>.svc.cluster.local:9000/application/o/<app-slug>/.well-known/openid-configuration`.
  - The values-interface schema exposes only `oidcIssuerUrl`; a separate **`oidcDiscoveryUrl`**
    override likely needs adding (a small contract/schema touch) so `iss` and the fetch URL can differ.

**Critical-path work items (in order — #93 stays DO-NOT-MERGE until all done):**
1. **FuzeFront PR (backend-engineer):** extend M2M provisioning to attach the `a2a` scope mapping
   emitting `{"repo": <name>, "aud": "a2a"}` on A2A machine providers — mirror the existing
   `provisionM2MClients()` / `ensureScopeMapping()` (`backend/src/authentik/provision-m2m-clients.ts`,
   already does this shape for `fuzefront:apps`). Without it, a registered `FuzeAgent` gets tokens
   that FAIL A2A validation. The #364 handler offered to open this PR on confirmation.
2. **In-cluster registration** of `FuzeAgent` (operator / one-shot Job in the fuzefront ns, where
   `AUTHENTIK_ADMIN_TOKEN` + `AUTHENTIK_BASE_URL=http://authentik-server:9000` already live) →
   returns `client_id`; seal the returned `client_secret` on the FuzeAgent side. Repeat per tenant.
3. **FuzeInfra `@claude`:** a NetworkPolicy allowing `fuzeagent → authentik-server:9000` in the
   fuzefront namespace (cross-namespace JWKS fetch). Not editable from FuzeFront/FuzeAgent.
4. **FuzeAgent #93 finalize:** confirm the exact `iss`/`aud`/`repo` strings by decoding one real
   minted token, wire the in-cluster discovery URL (+ any `oidcDiscoveryUrl` schema field), then
   merge with the secrets sealed.

Handler branch: `claude/issue-364-20260723-1718` (no PR opened yet — awaiting Option-2 confirmation).

## 2. SealedSecrets that must exist in namespace `fuzeagent` before Argo sync

Seal each with `kubeseal` against the **prod cluster's** sealed-secrets controller cert. Names/keys
must match `values-prod.yaml` exactly:

| SealedSecret `name` | key | Purpose | Required? |
|---|---|---|---|
| `a2a-provider-anthropic` | `api-key` | Anthropic API key the server's provider uses | **Yes** |
| `ghcr-pull` | (dockerconfigjson) | Pull the private `fuzeagent-a2a` image from GHCR | **Yes** |
| `a2a-mtls-ca` | `ca.crt` | In-cluster mTLS CA (defence-in-depth) | Only if `a2a.auth.mtls.enabled: true` — set `false` to skip |
| `a2a-card-signing` | `jws.key` | JWS key to sign Agent Cards | Only if the `a2a.cardSigning` block is kept — comment it out to skip (unsigned in-cluster) |
| `a2a-repos-git` | `token` | Git token to clone **private** tenant repos | Only if a tenant repo is private |

> Minimal first bring-up: keep only `a2a-provider-anthropic` + `ghcr-pull`, set `mtls.enabled:false`,
> and comment out the `cardSigning` block. Add mTLS + signing later.

## 3. `providesTo` backfill (authz — fail-closed)

FuzeAgent's `.fuze/manifest.json` has **no `providesTo`**, so with A2A enabled it will accept **no
callers** — safe, and fine for the first bring-up (nothing else is enabled to call it yet). Before a
consumer (FuzePlan, a product) is allowed to call FuzeAgent, add FuzeAgent's `providesTo` from the
approved graph (**FuzeSDLC#54**) in the same PR that enables that consumer. Do the same for each
tenant as it is added.

## 4. The image (auto-built on merge — one caveat)

`release.yml` builds/pushes `ghcr.io/izzywdev/fuzeagent-a2a` and rewrites the `tag:` in this file on
push to `main` under `deploy/helm/a2a-shared/**`. It has **not** run for the A2A merges because the
squash-merge commit bodies inherited a `[skip ci]` line from the governance-sync reconcile commits.

➡️ **Merge this rollout PR with a CLEAN squash message (no `[skip ci]`)** so `release.yml` fires,
builds the image, and bumps `a2a.image.tag`. Verify afterward: `gh api
user/packages/container/fuzeagent-a2a/versions`.

## 5. Merge → verify

1. Fill §1, seal §2, confirm §3 for the first tenant.
2. Merge the rollout PR (clean squash message).
3. `release.yml` builds the image + bumps `tag`; Argo syncs the `a2a-shared` Application.
4. Verify: pod healthy (`GET /healthz`), card resolves at the well-known path, and the
   `a2a-acceptance.yml` gate run against the live URL is green.

## Rollout order (this PR = step 1 only)

**FuzeAgent** (this PR) → **exec tier** (`Exec-cto/ceo/cfo/ciso` cards, per FuzeSDLC#54) →
**spine** (`FuzePlan` next — unblocks the real cross-product ticket scenario — then the other spine
services as they expose agents) → **leaves**. Each step: add the tenant + backfill that repo's
`providesTo` in one PR, merge clean, let Argo sync.
