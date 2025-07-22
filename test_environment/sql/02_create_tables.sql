-- YouWoAI Test Database Schema
-- Generated at: 2025-07-19T14:28:09.438293
-- Tables required by ML server

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create sequences first
CREATE SEQUENCE IF NOT EXISTS user_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS folder_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS conversation_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS note_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS part_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS image_v1_id_seq;
CREATE SEQUENCE IF NOT EXISTS subscription_v1_id_seq;

-- subscription_v1 (simplified for test - referenced by user_v1)
CREATE TABLE IF NOT EXISTS subscription_v1 (
  id INTEGER NOT NULL DEFAULT nextval('subscription_v1_id_seq'::regclass),
  name CHARACTER VARYING NOT NULL DEFAULT 'free',
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY ("id")
);

-- user_v1 (without circular foreign key to conversation)
CREATE TABLE IF NOT EXISTS user_v1 (
  id INTEGER NOT NULL DEFAULT nextval('user_v1_id_seq'::regclass),
  email CHARACTER VARYING,
  username CHARACTER VARYING NOT NULL,
  discriminator CHARACTER VARYING NOT NULL DEFAULT '0001'::character varying,
  "phoneNumber" CHARACTER VARYING,
  isActive BOOLEAN NOT NULL DEFAULT true,
  emailVerified BOOLEAN NOT NULL DEFAULT false,
  settings JSONB NOT NULL DEFAULT '{"AIType": "gpt-4", "fontSize": "16", "hideGmailBar": false, "speechService": "MSSR", "hidePaymentBar": false, "speechLanguage": "en-US", "defaultFolderId": null, "defaultPromptId": null, "editModeSupported": true}'::jsonb,
  "conversationId" INTEGER,
  role CHARACTER VARYING NOT NULL DEFAULT 'user'::character varying,
  "subscriptionId" INTEGER DEFAULT 1,
  "profileURL" CHARACTER VARYING,
  mode CHARACTER VARYING NOT NULL DEFAULT 'personal'::character varying,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  devices JSONB NOT NULL DEFAULT '[]'::jsonb,
  "stripeCustomerId" CHARACTER VARYING,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("subscriptionId") REFERENCES subscription_v1(id)
);

-- Indexes
CREATE UNIQUE INDEX "PK_cace4a159ff9f2512dd42373760_v1" ON public.user_v1 USING btree (id);
CREATE UNIQUE INDEX "REL_defc8529466a975f7342accd06_v1" ON public.user_v1 USING btree ("conversationId");
CREATE UNIQUE INDEX "UQ_e12875dfb3b1d92d7d7c5377e22_v1" ON public.user_v1 USING btree (email);
CREATE UNIQUE INDEX "UQ_f1d3ffb910b5c1a9052df7c1833_v1" ON public.user_v1 USING btree ("subscriptionId");
CREATE UNIQUE INDEX "UQ_f2578043e491921209f5dadd080_v1" ON public.user_v1 USING btree ("phoneNumber");
CREATE UNIQUE INDEX "UQ_f8d434def737538ef9c561591ef" ON public.user_v1 USING btree (username, discriminator);

-- folder_v1
CREATE TABLE IF NOT EXISTS folder_v1 (
  id INTEGER NOT NULL DEFAULT nextval('folder_v1_id_seq'::regclass),
  "ownerId" INTEGER NOT NULL,
  "folderTitle" CHARACTER VARYING NOT NULL,
  "conversationId" INTEGER,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  shareSettings JSONB DEFAULT '{"isPublic": false, "trackViews": false, "allowComments": false, "allowDownload": false, "requiresPayment": false}'::jsonb,
  globalTemplateSettings JSONB,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("ownerId") REFERENCES user_v1(id)
);

-- Indexes
CREATE UNIQUE INDEX "PK_6278a41a706740c94c02e288df8_v1" ON public.folder_v1 USING btree (id);
CREATE UNIQUE INDEX "REL_3c4f97ff0aa56f831ddecc8350_v1" ON public.folder_v1 USING btree ("conversationId");

-- Create conversation type enum
-- Create conversation type enum
DO $$ BEGIN
    CREATE TYPE conversation_type_enum AS ENUM ('user', 'folder', 'note');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- conversation_v1
CREATE TABLE IF NOT EXISTS conversation_v1 (
  id INTEGER NOT NULL DEFAULT nextval('conversation_v1_id_seq'::regclass),
  "ownerId" INTEGER,
  type conversation_type_enum NOT NULL DEFAULT 'user'::conversation_type_enum,
  "threadId" CHARACTER VARYING,
  assistantId CHARACTER VARYING NOT NULL DEFAULT ''::character varying,
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  messagesSynced BOOLEAN NOT NULL DEFAULT false,
  typeId INTEGER,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  title CHARACTER VARYING,
  skipEmbedding BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("ownerId") REFERENCES user_v1(id)
);

-- Add foreign key from user to conversation after conversation table is created
ALTER TABLE user_v1 ADD CONSTRAINT fk_user_conversation 
  FOREIGN KEY ("conversationId") REFERENCES conversation_v1(id);
  
-- Add foreign key from folder to conversation
ALTER TABLE folder_v1 ADD CONSTRAINT fk_folder_conversation 
  FOREIGN KEY ("conversationId") REFERENCES conversation_v1(id);

-- Indexes
CREATE UNIQUE INDEX "PK_864528ec4274360a40f66c29845_v1" ON public.conversation_v1 USING btree (id);

-- note_v1
CREATE TABLE IF NOT EXISTS note_v1 (
  id INTEGER NOT NULL DEFAULT nextval('note_v1_id_seq'::regclass),
  "ownerId" INTEGER,
  "folderId" INTEGER,
  "noteTitle" CHARACTER VARYING NOT NULL,
  completed BOOLEAN NOT NULL DEFAULT false,
  "audioURL" CHARACTER VARYING,
  "timeFrom" TIME WITHOUT TIME ZONE,
  "timeTo" TIME WITHOUT TIME ZONE,
  promptId INTEGER,
  promptContent JSONB NOT NULL DEFAULT '{"promptContent": null, "promptContentHistory": []}'::jsonb,
  "conversationId" INTEGER,
  "deviceType" CHARACTER VARYING,
  language CHARACTER VARYING NOT NULL,
  noteSubscriptionUsage JSONB NOT NULL DEFAULT '{"chatBotUsage": 0, "imageToTextUsage": 0, "promptUsageCount": 0, "imageToLatexUsage": 0}'::jsonb,
  quizContent JSONB,
  flashcardContent JSONB,
  "aiNoteContent" CHARACTER VARYING,
  noteType CHARACTER VARYING NOT NULL DEFAULT 'audio'::character varying,
  "linkURL" CHARACTER VARYING,
  "noteTranscriptionServiceUsed" CHARACTER VARYING,
  noteContent JSONB,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  "fileURL" CHARACTER VARYING,
  skipEmbedding BOOLEAN NOT NULL DEFAULT false,
  shareSettings JSONB DEFAULT '{"isPublic": false, "trackViews": false, "allowComments": false, "allowDownload": false, "requiresPayment": false}'::jsonb,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("conversationId") REFERENCES conversation_v1(id),
  FOREIGN KEY ("ownerId") REFERENCES user_v1(id),
  FOREIGN KEY ("folderId") REFERENCES folder_v1(id)
);

-- Indexes
CREATE UNIQUE INDEX "PK_96d0c172a4fba276b1bbed43058_v1" ON public.note_v1 USING btree (id);
CREATE UNIQUE INDEX "REL_b3fb65ba1699b180abc139eb0a_v1" ON public.note_v1 USING btree ("conversationId");

-- part_v1
CREATE TABLE IF NOT EXISTS part_v1 (
  id INTEGER NOT NULL DEFAULT nextval('part_v1_id_seq'::regclass),
  "noteId" INTEGER NOT NULL,
  "order" INTEGER NOT NULL,
  "timeFrom" TIME WITHOUT TIME ZONE,
  "timeTo" TIME WITHOUT TIME ZONE,
  text CHARACTER VARYING NOT NULL,
  words JSONB,
  translations JSONB,
  completed BOOLEAN NOT NULL DEFAULT false,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  "clientId" UUID,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("noteId") REFERENCES note_v1(id)
);

-- Indexes
CREATE UNIQUE INDEX "PK_58888debdf048d2dfe459aa59da_v1" ON public.part_v1 USING btree (id);

-- image_v1
CREATE TABLE IF NOT EXISTS image_v1 (
  id INTEGER NOT NULL DEFAULT nextval('image_v1_id_seq'::regclass),
  "partId" INTEGER,
  "noteId" INTEGER NOT NULL,
  "imageURL" CHARACTER VARYING,
  "imageText" CHARACTER VARYING,
  latex BOOLEAN NOT NULL,
  createDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  updateDate TIMESTAMPTZ NOT NULL DEFAULT now(),
  deletedAt TIMESTAMPTZ,
  "clientId" UUID,
  "partClientId" UUID,
  PRIMARY KEY ("id"),
  FOREIGN KEY ("partId") REFERENCES part_v1(id),
  FOREIGN KEY ("noteId") REFERENCES note_v1(id)
);

-- Indexes
CREATE UNIQUE INDEX "PK_d6db1ab4ee9ad9dbe86c64e4cc3_v1" ON public.image_v1 USING btree (id);

-- embedding_v1
CREATE TABLE IF NOT EXISTS embedding_v1 (
  section_id INTEGER NOT NULL,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
  embedding VECTOR(1536),
  chunk_text TEXT,
  source VARCHAR(50),
  chunk_tsv TSVECTOR,
  type_id INTEGER NOT NULL,
  type VARCHAR(50) NOT NULL,
  url TEXT,
  metadata JSONB
);

-- Indexes
CREATE INDEX embedding_v1_cosine_idx ON public.embedding_v1 USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');
CREATE INDEX embedding_v1_chunk_tsv_idx ON public.embedding_v1 USING gin (chunk_tsv);
CREATE INDEX embedding_v1_chunk_text_idx ON public.embedding_v1 USING gin (chunk_text gin_trgm_ops);
CREATE INDEX embedding_v1_source_idx ON public.embedding_v1 USING btree (source);
CREATE INDEX "IDX_embedding_v1_type_id" ON public.embedding_v1 USING btree (type_id);
CREATE INDEX "IDX_embedding_v1_type" ON public.embedding_v1 USING btree (type);
CREATE INDEX "IDX_embedding_v1_url" ON public.embedding_v1 USING btree (url);
CREATE INDEX "IDX_embedding_v1_type_type_id" ON public.embedding_v1 USING btree (type, type_id);
CREATE INDEX "IDX_embedding_v1_metadata" ON public.embedding_v1 USING gin (metadata);

-- Add foreign key constraints that reference later tables
ALTER TABLE folder_v1 
  ADD CONSTRAINT "FK_folder_conversationId" 
  FOREIGN KEY ("conversationId") REFERENCES conversation_v1(id);

