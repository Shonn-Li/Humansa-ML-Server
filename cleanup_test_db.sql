-- Cleanup test database to only keep ML-server relevant tables
-- This removes tables that are not used by the ML server

BEGIN;

-- Drop tables that ML server doesn't use
DROP TABLE IF EXISTS auth_v1 CASCADE;
DROP TABLE IF EXISTS file_v1 CASCADE;
DROP TABLE IF EXISTS job_v1 CASCADE;
DROP TABLE IF EXISTS network_log_v1 CASCADE;
DROP TABLE IF EXISTS prompt_v1 CASCADE;
DROP TABLE IF EXISTS migrations CASCADE;

-- Keep only the essential tables for ML server:
-- ✓ note_v1 - for RAG search
-- ✓ folder_v1 - for folder-based note filtering
-- ✓ conversation_v1 - for conversation search
-- ✓ user_v1 - for user validation
-- ✓ embedding_v1 - for vector search
-- ✓ web_search_cache - for caching web search results

-- List remaining tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;

COMMIT;

-- Add a comment to document what tables are needed
COMMENT ON TABLE note_v1 IS 'Essential: Stores user notes for RAG search';
COMMENT ON TABLE folder_v1 IS 'Essential: Used for folder-based note filtering';
COMMENT ON TABLE conversation_v1 IS 'Essential: Stores conversations for search';
COMMENT ON TABLE user_v1 IS 'Essential: User validation and ownership checks';
COMMENT ON TABLE embedding_v1 IS 'Essential: Vector embeddings for semantic search';
COMMENT ON TABLE web_search_cache IS 'Essential: Caches web search results for ML server';