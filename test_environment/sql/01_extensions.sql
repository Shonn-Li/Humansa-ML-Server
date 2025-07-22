-- Enable required PostgreSQL extensions for YouWoAI
-- This must be run first before creating any tables

-- Enable pgvector for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for trigram-based text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable uuid generation (useful for some operations)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions are installed
SELECT 
    extname AS extension_name,
    extversion AS version
FROM pg_extension 
WHERE extname IN ('vector', 'pg_trgm', 'uuid-ossp')
ORDER BY extname;