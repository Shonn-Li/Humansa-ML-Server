-- Final cleanup: Remove only truly unused tables from test database

BEGIN;

-- Remove subscription_v1 as it's not used by ML server
DROP TABLE IF EXISTS subscription_v1 CASCADE;

-- List final tables that should remain
SELECT table_name, 
       obj_description(pgc.oid, 'pg_class') as comment
FROM information_schema.tables t
JOIN pg_class pgc ON pgc.relname = t.table_name
WHERE t.table_schema = 'public' 
AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;

COMMIT;

-- Update comments to reflect actual usage
COMMENT ON TABLE image_v1 IS 'Essential: Stores images associated with note parts, used for embedding generation';
COMMENT ON TABLE part_v1 IS 'Essential: Stores note parts, used for multi-part note embedding';