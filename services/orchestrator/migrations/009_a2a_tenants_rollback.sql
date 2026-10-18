-- Rollback for 009_a2a_tenants.sql

DROP TRIGGER IF EXISTS update_a2a_tenants_updated_at ON a2a_tenants;
DROP INDEX IF EXISTS idx_a2a_tenants_enabled;
DROP TABLE IF EXISTS a2a_tenants;
