# Deploying the handoff MCP server (Contabo prod, GitOps + Cloudflare)

The handoff MCP server is what lets the FuzeOne agents delegate to each other. It creates
Managed-Agents sessions with our `ANTHROPIC_API_KEY`, so it is **bearer-gated** and exposed
to Anthropic's cloud at **`https://mcp-handoff.prod.fuzefront.com/mcp`** through the Cloudflare
tunnel, behind a CF Access **bypass** app (machine endpoint — no email-OTP; the app bearer is
the gate). **Prod is GitOps — never `kubectl apply` by hand; land everything via PRs → Argo/CD syncs.**

## What's already in the repo (this change)
- **App bearer**: `server.py` rejects any request without `Authorization: Bearer $HANDOFF_MCP_TOKEN` (Starlette middleware; `uvicorn`/`starlette` in requirements). Rebuilt into `ghcr.io/izzywdev/fuzeinfra/agent-handoff:latest` by `agent-images.yml` on merge.
- **Workload**: `helm/fuzeinfra/templates/handoff-mcp.yaml` (Deployment + Service + Ingress `mcp-handoff.<domain>` + `handoff-state` ConfigMap), gated `handoffMcp.enabled` (default **off**).
- **CF Access bypass**: `terraform/contabo/cloudflare.tf` `handoff_mcp` app + `handoff_mcp_bypass` policy, gated `var.handoff_mcp_access_enabled` (default **off**).
- **Agent auth**: `vaults/fuzeinfra.json` carries a `static_bearer` cred keyed to `${HANDOFF_MCP_URL}` with `${HANDOFF_MCP_TOKEN}`; `provision.yml` passes `HANDOFF_MCP_TOKEN`.

## Go-live steps (human-gated)

1. **Pick a token**: `HANDOFF_MCP_TOKEN=$(openssl rand -hex 32)`.

2. **Seal the secret** (needs `kubeseal`; fetches the cert from the CF-bypassed cert endpoint — no cluster access):
   ```bash
   printf '%s' "$ANTHROPIC_API_KEY" > /tmp/ak && printf '%s' "$HANDOFF_MCP_TOKEN" > /tmp/tok
   scripts/seal-secret.sh fuzeinfra/handoff-mcp-secret \
     ANTHROPIC_API_KEY=@/tmp/ak HANDOFF_MCP_TOKEN=@/tmp/tok \
     --out deploy/sealed-secrets/handoff-mcp-secret.yaml
   ```
   (Synced by the existing `fuzeinfra-sealed-secrets` Argo app.)

3. **Populate the id-state** and **flip the gate** — in the SAME PR as the sealed secret:
   - download the `managed-agents-state-anthropic` artifact from the latest **Provision Managed Agents** / **Sync Managed Agents on merge** run (or run `providers/provision.py` locally) → commit its `*.json` into `helm/fuzeinfra/files/handoff-state/`.
   - set `handoffMcp.enabled: true` in `helm/fuzeinfra/values-contabo.yaml`.
   - **verify GHCR visibility**: make `ghcr.io/izzywdev/fuzeinfra/agent-handoff` public, or set `handoffMcp.imagePullSecrets` + add a ghcr pull secret to `fuzeinfra` (see `argocd/cluster-config/ghcr-pull-secret-*.yaml`).
   Merge → Argo syncs the Deployment/Service/Ingress/ConfigMap.

4. **Enable the CF Access bypass**: set `handoff_mcp_access_enabled = true` in the Contabo `terraform.tfvars`, merge → the Terraform CD applies the more-specific Access app (machine calls skip the `*.prod` OTP wildcard).

5. **Point the agents at the public URL + give them the bearer**: set repo secrets
   `HANDOFF_MCP_URL = https://mcp-handoff.prod.fuzefront.com/mcp` and `HANDOFF_MCP_TOKEN = <the token>`,
   then run **Provision Managed Agents**. Every role's `handoff` MCP server url updates to the public URL,
   and the vault gains the `static_bearer` cred so Anthropic injects `Authorization: Bearer` on connect.

## Verify
```bash
# without the token → 401 (bearer gate works)
curl -s -o /dev/null -w '%{http_code}\n' https://mcp-handoff.prod.fuzefront.com/mcp        # 401
# with the token → MCP responds (not 401/OTP redirect)
curl -s -H "Authorization: Bearer $HANDOFF_MCP_TOKEN" https://mcp-handoff.prod.fuzefront.com/mcp | head
```
Then launch a session that delegates (e.g. the SDLC coordinator `ask_agent`) and confirm it reaches a sub-agent instead of erroring on the handoff tool.

> The raw manifest `handoff-mcp.yaml` in this dir is the original standalone reference; the **Helm template is the deployed source of truth**. Rotate the bearer by re-sealing the secret (step 2) + updating the `HANDOFF_MCP_TOKEN` secret + re-provision (step 5); no image change needed.
