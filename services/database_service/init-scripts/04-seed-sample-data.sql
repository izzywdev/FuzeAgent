-- Seed sample data for first-time initialization
-- This script is idempotent using ON CONFLICT DO NOTHING where applicable.

-- Sample organization
INSERT INTO organizations (id, name, description, settings)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Seeded Organization',
    'Preloaded organization created by init script',
    '{}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- Sample team
INSERT INTO teams (id, organization_id, name, description, team_type, settings)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Seeded Team',
    'Preloaded team created by init script',
    'general',
    '{}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- Sample agent
INSERT INTO agents (id, team_id, name, role, type, status, config)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '22222222-2222-2222-2222-222222222222',
    'Seeded Agent',
    'Demo Agent',
    'general',
    'active',
    '{}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- Sample task (optional)
INSERT INTO tasks (id, title, description, status, priority, assigned_to, result, metadata)
VALUES (
    '44444444-4444-4444-4444-444444444444',
    'Seeded Task',
    'Preloaded task created by init script',
    'pending',
    'medium',
    '33333333-3333-3333-3333-333333333333',
    '{}'::jsonb,
    '{}'::jsonb
)
ON CONFLICT (id) DO NOTHING;


