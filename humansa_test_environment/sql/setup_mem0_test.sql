-- Setup script for Mem0 in Humansa test environment
-- This script prepares the database for Mem0 integration testing

-- Enable pgvector extension (required for Mem0)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create separate schema for Mem0 test data
CREATE SCHEMA IF NOT EXISTS mem0_test;

-- Grant all privileges to the test user
GRANT ALL PRIVILEGES ON SCHEMA mem0_test TO youwo;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mem0_test TO youwo;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mem0_test TO youwo;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA mem0_test
GRANT ALL PRIVILEGES ON TABLES TO youwo;

ALTER DEFAULT PRIVILEGES IN SCHEMA mem0_test
GRANT ALL PRIVILEGES ON SEQUENCES TO youwo;

-- Create test users for memory testing
-- These will be used in the test cases
INSERT INTO user_v1 (id, email, name, "createdAt", "updatedAt")
VALUES 
    (10001, 'mem0_test_user1@humansa.test', 'Test User 1 - No Memory', NOW(), NOW()),
    (10002, 'mem0_test_user2@humansa.test', 'Test User 2 - With Diabetes', NOW(), NOW()),
    (10003, 'mem0_test_user3@humansa.test', 'Test User 3 - Complex History', NOW(), NOW())
ON CONFLICT (id) DO UPDATE 
SET email = EXCLUDED.email, 
    name = EXCLUDED.name,
    "updatedAt" = NOW();

-- Create test conversations for these users
-- User 1: No prior conversations (clean slate)
-- User 2: Has some medical history
INSERT INTO conversation_v1 (id, "ownerId", type, title, "createdAt", "updatedAt")
VALUES 
    (20001, 10002, 'humansa', 'Diabetes Consultation', NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (20002, 10002, 'humansa', 'Follow-up Appointment', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (20003, 10003, 'humansa', 'Initial Consultation', NOW() - INTERVAL '14 days', NOW() - INTERVAL '14 days')
ON CONFLICT (id) DO UPDATE 
SET title = EXCLUDED.title,
    "updatedAt" = NOW();

-- Log setup completion
DO $$
BEGIN
    RAISE NOTICE 'Mem0 test environment setup completed successfully';
    RAISE NOTICE '- pgvector extension enabled';
    RAISE NOTICE '- mem0_test schema created';
    RAISE NOTICE '- Test users created (IDs: 10001, 10002, 10003)';
    RAISE NOTICE '- Test conversations created';
END $$;