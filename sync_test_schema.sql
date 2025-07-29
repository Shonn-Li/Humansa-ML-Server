-- Synchronize test database schema with production
-- This script updates the test database to match production column names

-- IMPORTANT: This script should be run on the TEST database (port 5454)

BEGIN;

-- 1. First, let's rename columns in note_v1 to match production
ALTER TABLE note_v1 
  RENAME COLUMN createdate TO "createDate";

ALTER TABLE note_v1 
  RENAME COLUMN updatedate TO "updateDate";

ALTER TABLE note_v1 
  RENAME COLUMN deletedat TO "deletedAt";

ALTER TABLE note_v1 
  RENAME COLUMN promptcontent TO "promptContent";

ALTER TABLE note_v1 
  RENAME COLUMN quizcontent TO "quizContent";

ALTER TABLE note_v1 
  RENAME COLUMN notecontent TO "noteContent";

ALTER TABLE note_v1 
  RENAME COLUMN flashcardcontent TO "flashcardContent";

ALTER TABLE note_v1 
  RENAME COLUMN promptid TO "promptId";

ALTER TABLE note_v1 
  RENAME COLUMN notetype TO "noteType";

ALTER TABLE note_v1 
  RENAME COLUMN notesubscriptionusage TO "noteSubscriptionUsage";

-- 2. Rename columns in folder_v1
ALTER TABLE folder_v1 
  RENAME COLUMN createdate TO "createDate";

ALTER TABLE folder_v1 
  RENAME COLUMN updatedate TO "updateDate";

ALTER TABLE folder_v1 
  RENAME COLUMN deletedat TO "deletedAt";

-- 3. Rename columns in conversation_v1
ALTER TABLE conversation_v1 
  RENAME COLUMN createdate TO "createDate";

ALTER TABLE conversation_v1 
  RENAME COLUMN updatedate TO "updateDate";

ALTER TABLE conversation_v1 
  RENAME COLUMN deletedat TO "deletedAt";

ALTER TABLE conversation_v1 
  RENAME COLUMN assistantid TO "assistantId";

ALTER TABLE conversation_v1 
  RENAME COLUMN typeid TO "typeId";

ALTER TABLE conversation_v1 
  RENAME COLUMN messagessynced TO "messagesSynced";

-- 4. Rename columns in user_v1
ALTER TABLE user_v1 
  RENAME COLUMN createdate TO "createDate";

ALTER TABLE user_v1 
  RENAME COLUMN updatedate TO "updateDate";

ALTER TABLE user_v1 
  RENAME COLUMN deletedat TO "deletedAt";

ALTER TABLE user_v1 
  RENAME COLUMN isactive TO "isActive";

ALTER TABLE user_v1 
  RENAME COLUMN emailverified TO "emailVerified";

-- 5. Create missing tables from production (basic structure)
-- auth_v1 table (if doesn't exist)
CREATE TABLE IF NOT EXISTS auth_v1 (
    id SERIAL PRIMARY KEY,
    "userId" INTEGER,
    provider VARCHAR(255),
    "providerId" VARCHAR(255),
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "expiresAt" TIMESTAMP,
    "createDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updateDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- file_v1 table (if doesn't exist)
CREATE TABLE IF NOT EXISTS file_v1 (
    id SERIAL PRIMARY KEY,
    "userId" INTEGER,
    "fileName" VARCHAR(255),
    "fileSize" INTEGER,
    "fileType" VARCHAR(100),
    "fileUrl" TEXT,
    "createDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updateDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "deletedAt" TIMESTAMP
);

-- job_v1 table (if doesn't exist)
CREATE TABLE IF NOT EXISTS job_v1 (
    id SERIAL PRIMARY KEY,
    type VARCHAR(100),
    status VARCHAR(50),
    data JSONB,
    result JSONB,
    error TEXT,
    "createDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updateDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP
);

-- network_log_v1 table (if doesn't exist)
CREATE TABLE IF NOT EXISTS network_log_v1 (
    id SERIAL PRIMARY KEY,
    "userId" INTEGER,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    "statusCode" INTEGER,
    "responseTime" INTEGER,
    "requestBody" JSONB,
    "responseBody" JSONB,
    "createDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompt_v1 table (if doesn't exist)
CREATE TABLE IF NOT EXISTS prompt_v1 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    content TEXT,
    type VARCHAR(100),
    "isActive" BOOLEAN DEFAULT true,
    "createDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "updateDate" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- migrations table (if doesn't exist)
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    "executedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Note: embedding_v1 should remain in test database as it's needed for RAG
-- But let's ensure it has consistent naming
-- (No changes needed as it doesn't have date columns)

-- 7. Add index on commonly queried columns if not exists
CREATE INDEX IF NOT EXISTS idx_note_v1_owner_deleted ON note_v1("ownerId", "deletedAt");
CREATE INDEX IF NOT EXISTS idx_folder_v1_owner_deleted ON folder_v1("ownerId", "deletedAt");
CREATE INDEX IF NOT EXISTS idx_conversation_v1_owner_deleted ON conversation_v1("ownerId", "deletedAt");

COMMIT;

-- Verify the changes
SELECT 
    'note_v1' as table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'note_v1'
AND column_name IN ('createDate', 'updateDate', 'deletedAt')
ORDER BY column_name;