# A2A `a2a-shared` — production go-live checklist (FuzeAgent-first)

Prod is **GitOps** (Contabo k3s, Argo CD `a2a-shared` Application, `values-prod.yaml`). Nothing is
hand-deployed. This overlay is staged to `enabled: true` in the rollout PR, but Argo renders it only
once the PR **merges to `main`** — and it will not run correctly until the items below exist.

**None of these can be done by an automated agent** — they are real credentials/config that only the
owner (or the sealed-secrets flow) can provide. The rollout PR fills all config values (§1) and leaves
`secretRef` names; you seal the secrets (§2) and confirm the token (§1b step 6).

> **⛔ DO NOT MERGE #93 until (a) the 4 SealedSecrets in §2 exist in the `fuzeagent` namespace AND
> (b) a real minted token has been decoded to confirm the exact `iss` / `aud` / `repo` claim strings
> and the `fuzefront` app slug.** Until then #93 is not on `main`, so Argo renders nothing.

## 1. Owner-supplied config (edit `values-prod.yaml`)

| Field | What to set |
|---|---|
| `a2a.auth.oidcIssuerUrl` | **Set** to FuzeFront's prod Authentik issuer `https://app.fuzefront.com/application/o/fuzefront/` (from FuzeFront `deploy/helm/fuzefront/values-prod.yaml`). The `iss` anchor. Already filled in `values-prod.yaml`. |
| `a2a.auth.oidcDiscoveryUrl` | **Set** to the in-cluster discovery URL `http://authentik-server.fuzefront.svc.cluster.local:9000/application/o/fuzefront/.well-known/openid-configuration`. The server fetches JWKS/discovery from HERE while still validating `iss` against `oidcIssuerUrl`. Added to the frozen interface in **contract v1.1.0** (FuzeAgent#96, optional + additive). Already filled. |
| `a2a.auth.audience` | `a2a` (dedicated M2M audience). Already filled. |
| `a2a.auth.callerClaim` | `repo` (custom claim carrying the exact repo name — the allowlist key). Already filled. |
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
- `oidcIssuerUrl` (the `iss` anchor) stays the public `https://app.fuzefront.com/application/o/fuzefront/`
  (`issuer_mode: global`), **but JWKS/discovery is fetched in-cluster** to avoid a Cloudflare-tunnel
  hairpin (FuzeFront hit 17–34 s hairpin timeouts before), via **`oidcDiscoveryUrl`**:
  `http://authentik-server.fuzefront.svc.cluster.local:9000/application/o/fuzefront/.well-known/openid-configuration`.
  - The `oidcDiscoveryUrl` override is now a **first-class field in the frozen interface as of
    contract v1.1.0** (FuzeAgent#96 — optional + purely additive; the server validates `iss` against
    `oidcIssuerUrl` while fetching keys from `oidcDiscoveryUrl`). It is set in `values-prod.yaml`.
    App slug is **`fuzefront`** (confirm against a real minted token before go-live).

**Critical-path work items (in order — #93 stays DO-NOT-MERGE until all done):**
1. **Contract v1.1.0 (contract-designer) — DONE:** `auth.oidcDiscoveryUrl` added to the frozen
   values-interface (FuzeAgent#96, merged to `main`). #93 is rebased onto it, so helm-validate sees
   a schema that accepts `oidcDiscoveryUrl`.
2. **Server `oidcDiscoveryUrl` support (backend-engineer, parallel):** the A2A server must honour the
   `oidcDiscoveryUrl` override — fetch discovery/JWKS from it while validating `iss` against
   `oidcIssuerUrl`. Tracked separately; NOT part of this devops PR.
3. **FuzeFront PR (backend-engineer):** extend M2M provisioning to attach the `a2a` scope mapping
   emitting `{"repo": <name>, "aud": "a2a"}` on A2A machine providers — mirror the existing
   `provisionM2MClients()` / `ensureScopeMapping()` (`backend/src/authentik/provision-m2m-clients.ts`,
   already does this shape for `fuzefront:apps`). Without it, a registered `FuzeAgent` gets tokens
   that FAIL A2A validation.
4. **In-cluster registration** of `FuzeAgent` (operator / one-shot Job in the fuzefront ns, where
   `AUTHENTIK_ADMIN_TOKEN` + `AUTHENTIK_BASE_URL=http://authentik-server:9000` already live) →
   returns `client_id`; seal the returned `client_secret` on the FuzeAgent side. Repeat per tenant.
5. **NetworkPolicy — FuzeFront chart (FuzeFront#373) — ALREADY ENABLED:** the cross-namespace
   `fuzeagent → authentik-server:9000` JWKS path is admitted by FuzeFront's own chart
   (`networkPolicy.enabled: true` in `fuzefront` prod values, `fuzeagentNamespace: fuzeagent`).
   It lives in FuzeFront's chart (not FuzeInfra) because a NetworkPolicy's `podSelector` only matches
   its own namespace and the `fuzeinfra` AppProject can't target `fuzefront`. The rule is authored
   ALONGSIDE Authentik's existing ingress allowances so it does NOT flip `authentik-server` to
   deny-all (which would break Traefik→Authentik login). **Operator: nothing to do here — verify only.**
6. **FuzeAgent #93 finalize (this devops PR):** `oidcDiscoveryUrl` is set in `values-prod.yaml`; the
   hardened secret set is referenced. Before merge, **decode one real minted token** to confirm the
   exact `iss`/`aud`/`repo` strings and the `fuzefront` app slug, then seal the §2 secrets and merge
   with a CLEAN squash message (§4). This PR does NOT create the secrets or decode the token — those
   are operator steps.

## 2. SealedSecrets that must exist in namespace `fuzeagent` before Argo sync

This is the **hardened (Option B) bring-up** — mTLS + card-signing stay ON. Seal each with `kubeseal`
against the **prod cluster's** sealed-secrets controller cert. Names/keys must match `values-prod.yaml`
exactly. **Exactly these 4 SealedSecrets are required for the FuzeAgent-first rollout:**

| SealedSecret `name` | key | Purpose | Required? |
|---|---|---|---|
| `a2a-provider-anthropic` | `api-key` | Anthropic API key the server's provider uses (also exported as `ANTHROPIC_API_KEY` for session provisioning) | **Yes** |
| `ghcr-pull` | `.dockerconfigjson` | Pull the private `fuzeagent-a2a` image from GHCR (`kubernetes.io/dockerconfigjson` type) | **Yes** |
| `a2a-mtls-ca` | `ca.crt` | In-cluster mTLS CA (defence-in-depth) — `a2a.auth.mtls.enabled: true` | **Yes (Option B)** |
| `a2a-card-signing` | `jws.key` | JWS key to sign Agent Cards — `a2a.cardSigning` kept | **Yes (Option B)** |

> **`a2a-repos-git` is NOT needed for this bring-up.** The only tenant (`izzywdev/FuzeAgent`) is a
> PUBLIC repo, so the repo-sync init container clones anonymously and `deploy.reposGitTokenSecretRef`
> is `null`. Seal an `a2a-repos-git` (`token`) and repoint that ref ONLY when a PRIVATE tenant repo is
> onboarded.
>
> Lighter (non-hardened) alternative: set `a2a.auth.mtls.enabled: false` and comment out the
> `a2a.cardSigning` block to drop `a2a-mtls-ca` + `a2a-card-signing` (down to 2 secrets). Option B
> keeps them for defence-in-depth.

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

1. Config §1 is already filled (`oidcIssuerUrl`, `oidcDiscoveryUrl`, `audience`, `callerClaim`,
   `entryRole`). Seal the 4 SealedSecrets in §2; confirm §3 for the first tenant.
2. **Decode a real minted token** (§1b step 6) and confirm the `iss` == `oidcIssuerUrl`,
   `aud` == `a2a`, and the `repo` claim carries the exact repo name (`FuzeAgent`), and that the
   Authentik app slug in the discovery URL is `fuzefront`. Only proceed if they match.
3. Merge the rollout PR with a **CLEAN squash message (no `[skip ci]`)** — see §4.
4. `release.yml` builds the image + bumps `tag`; Argo syncs the `a2a-shared` Application.
5. Verify: pod healthy (`GET /healthz`), card resolves at the well-known path, and the
   `a2a-acceptance.yml` gate run against the live URL is green.

## Rollout order (this PR = step 1 only)

**FuzeAgent** (this PR) → **exec tier** (`Exec-cto/ceo/cfo/ciso` cards, per FuzeSDLC#54) →
**spine** (`FuzePlan` next — unblocks the real cross-product ticket scenario — then the other spine
services as they expose agents) → **leaves**. Each step: add the tenant + backfill that repo's
`providesTo` in one PR, merge clean, let Argo sync.
