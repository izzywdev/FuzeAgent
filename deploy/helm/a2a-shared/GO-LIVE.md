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

### 1b. Machine-identity integration with FuzeFront (BLOCKER — auth model needs reconciliation)

**Derived from FuzeFront `backend/security/src/services/machine-identity.ts` (FuzeFront#364 — the
@claude handler no-op'd, so these are read from the code, to be confirmed by FuzeFront):**

FuzeFront's machine identity is **introspection-based, not JWT/JWKS**:
- Machines register as **`client_credentials`** OAuth2 apps (`registerMachineClient(name)` →
  `{clientId, clientSecret}`; app slug = the machine name; `meta_description: "Machine identity for
  <name>"`). `issuer_mode: global`, **`sub_mode: hashed_user_id`**.
- Tokens are validated by **introspection** (`introspectMachineToken` → POST the Authentik
  introspection endpoint with the *validator's own* `AUTHENTIK_CLIENT_ID/SECRET`, fail-closed), NOT
  by local JWT signature/JWKS verification.

**Consequences for the A2A auth block (the current `oidcIssuerUrl`/`audience`/`callerClaim` shape is
WRONG for this model):**
1. **`callerClaim: sub` is wrong** — `sub` is a *hashed user id*, not the repo name. The caller must
   be resolved by **introspecting** the token and mapping the returned `client_id` → the registered
   machine name (= repo name). This is A2A-server work (backend-engineer), and it **diverges from the
   frozen contract's assumption** (authz.md §2: identity = the token's validated `sub`/claim). Either
   the A2A server gains an introspection path + `client_id`→repo map, **or** FuzeFront issues these
   agents JWTs carrying a repo-name claim. **This is a CTO-level contract/identity design decision.**
2. **No single `audience`** — each machine has its own `client_id`; there is no one `aud` to check.
   The introspection response's `active` + `client_id` is the check.
3. **No JWKS needed** — introspection is a server-to-server call; drop the JWKS/issuer-fetch concern.
   The A2A server instead needs its OWN registered machine identity (an
   `AUTHENTIK_CLIENT_ID/SECRET`) to call introspection, plus the Authentik introspection URL
   (reachable in-cluster).

**Still owner/FuzeFront actions:** (a) register `FuzeAgent` (then each tenant) as a machine identity
in **prod** Authentik — seal each `client_secret`; (b) provide the A2A server's own introspection
credential + endpoint; (c) confirm the `client_id`→repo-name mapping source. Because the @claude
handler stubbed, this is re-nudged on FuzeFront#364 with the specific finding; if it stays unengaged,
escalate to the CTO (it is a cross-product identity-architecture decision).

> The `auth:` block in `values-prod.yaml` is left as-is with a pointer here — **do not merge #93
> until the introspection-vs-JWT decision is made**, since the current OIDC-JWT config would not
> authenticate a FuzeFront machine token.

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
