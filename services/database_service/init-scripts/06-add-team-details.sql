-- Add defaults needed by UI in teams settings and seed initial colors

-- Ensure settings field exists (it does) and set a default color if missing
UPDATE teams
SET settings = jsonb_set(COALESCE(settings, '{}'::jsonb), '{color}', to_jsonb('#6b7280'::text))
WHERE (settings->>'color') IS NULL;

-- Ensure the seeded team has a nicer default color if present
UPDATE teams
SET settings = jsonb_set(COALESCE(settings, '{}'::jsonb), '{color}', to_jsonb('#2563eb'::text))
WHERE id = '22222222-2222-2222-2222-222222222222';


