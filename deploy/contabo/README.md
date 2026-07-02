# FuzeAgent — Contabo prod deploy assets

This directory holds the production (Contabo k3s) sealed secrets. Everything is
**GitOps**: the consumer commits manifests; ArgoCD (operated by FuzeInfra)
reconciles them. We never `kubectl apply` to prod.

## What lives here
- `sealed/` — Bitnami **SealedSecrets** (ciphertext only). Synced by the
  `fuzeagent-sealed` Argo application (`deploy/argocd/applications/fuzeagent-sealed.yaml`)
  into the `fuzeagent` namespace.
  - `fuzeagent-secrets.yaml` — app env: `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`,
    `JWT_SECRET`, `ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
    `GOOGLE_API_KEY`. Consumed via `secret.existingSecret: fuzeagent-secrets`.
  - `ghcr-pull.yaml` — GHCR image-pull secret (name **must** match
    `imagePullSecrets` in `values-prod.yaml` = `ghcr-pull`).

## How to produce them
Set repo Actions secrets first: `GHCR_PAT` (GHCR read), and optionally
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY`. Then run the
**Seal prod secrets** workflow (`.github/workflows/seal-secrets.yml`,
`workflow_dispatch`). It fetches the FuzeInfra public cert
(`https://sealed-secrets.prod.fuzefront.com/v1/cert.pem`), seals offline, and
commits the ciphertext here.

- Generated creds are sealed **once** (re-runs don't rotate a live DB password).
- API keys are **merged** on every run (add them later without disturbing creds).
- To rotate everything: delete `sealed/fuzeagent-secrets.yaml` and re-run.

The decrypt key lives only in the in-cluster sealed-secrets controller
(FuzeInfra shared infra, `kube-system`). No cluster access is needed to seal.
