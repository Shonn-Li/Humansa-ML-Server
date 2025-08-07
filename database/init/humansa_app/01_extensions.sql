-- PostgreSQL Extensions for Humansa Application
-- Required for vector search and other features

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create vector similarity search functions if needed
DO $$ 
BEGIN
    -- Check if vector extension is properly loaded
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE 'Vector extension is installed';
    ELSE
        RAISE WARNING 'Vector extension not found - some features may not work';
    END IF;
END $$;