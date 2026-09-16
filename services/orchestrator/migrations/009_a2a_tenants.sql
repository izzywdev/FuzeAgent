-- Migration: A2A Runtime Tenant Registry
-- Frozen contract: agent-templates/contracts/a2a/v1/schema/tenant-registration.schema.json
-- ($defs.RegisteredTenant) — see izzywdev/FuzeAgent#203.
--
-- This table is the canonical, columnar form of RegisteredTenant: the row a
-- consumer PUSHes via POST /a2a/tenants/register (Slice 2) and the row the
-- stateless A2A server reads via GET /a2a/tenants (Slice 3). The `tenant`
-- slug IS the registry key (client-assigned natural id, no separate uuid —
-- see the contract's x-client-assigned-id note); there is exactly one row
-- per tenant and registration is an idempotent upsert keyed on it.

-- Tenant Registry — one row per self-registered A2A tenant
CREATE TABLE IF NOT EXISTS a2a_tenants (
    -- The tenant routing key AND unique registry key. Must equal the
    -- projected card's supportedInterfaces[].tenant (card-projection.md §2).
    tenant VARCHAR(255) PRIMARY KEY,

    -- owner/name of the repo the card was projected from. For the
    -- self-registration security rule this MUST match the authenticated
    -- caller identity (tenant-registration.md §3) — enforced in Slice 2/3
    -- app code, not here.
    repo TEXT NOT NULL,

    -- Git ref the manifest/roles were read at when the card was projected.
    -- Provenance only; the orchestrator does not clone it.
    ref TEXT NOT NULL DEFAULT 'main',

    -- The role that serves a SendMessage naming no skill (mirrors
    -- values-interface tenant.entryRole / manifest.a2a.entryRole).
    entry_role TEXT NOT NULL,

    -- The roles projected into card `skills`, kept explicitly so an adapter
    -- can resolve an incoming skill id back to a role. Non-empty JSON array
    -- of role keys.
    serving_roles JSONB NOT NULL,

    -- Published through the Cloudflare tunnel with an https interface URL.
    external BOOLEAN NOT NULL DEFAULT false,

    -- Managed-Agents runtime binding for this tenant's sessions (the
    -- contract's Provider object). Nullable — secret material is by
    -- reference only (secretRef), never inline, and never projected onto
    -- the card.
    provider JSONB,

    -- The consumer's PROJECTED Agent Card, pushed as data. Structurally an
    -- agent-card.schema.json card that additionally satisfies
    -- fuze-profile.schema.json; both are validated by app code (Slice 2)
    -- before a row is written here.
    card JSONB NOT NULL,

    -- Whether the A2A server should serve this tenant. The read path
    -- (GET /a2a/tenants?enabled=true) filters on this column.
    enabled BOOLEAN NOT NULL DEFAULT true,

    -- Server-set. Set once on first registration, unchanged by later
    -- upserts (maps to contract `createdAt`).
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Server-set. Advanced on every upsert (maps to contract `updatedAt`).
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT a2a_tenants_tenant_format CHECK (tenant ~ '^[A-Za-z0-9_-]+$'),
    CONSTRAINT a2a_tenants_repo_format CHECK (repo ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
    CONSTRAINT a2a_tenants_entry_role_format CHECK (entry_role ~ '^[a-z0-9_-]+$'),
    CONSTRAINT a2a_tenants_serving_roles_nonempty_array CHECK (
        jsonb_typeof(serving_roles) = 'array'
        AND jsonb_array_length(serving_roles) > 0
    )
);

-- Read path: GET /a2a/tenants?enabled=true filters on this column.
CREATE INDEX IF NOT EXISTS idx_a2a_tenants_enabled ON a2a_tenants(enabled);

-- updated_at trigger — self-contained per this repo's migration convention
-- (007/008 also (re)define this function idempotently rather than assume a
-- prior migration ran it). Ensures updated_at always advances on any UPDATE
-- regardless of what the app-level upsert sets.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_a2a_tenants_updated_at ON a2a_tenants;
CREATE TRIGGER update_a2a_tenants_updated_at BEFORE UPDATE ON a2a_tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
