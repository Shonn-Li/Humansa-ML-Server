# Test Database Schema for ML Server

## Essential Tables (Keep)

These tables are actively used by the ML server and must be present in the test database:

### 1. `note_v1`
- **Purpose**: Stores user notes for RAG search
- **Used by**: RAG processor, context search, agentic RAG
- **Key columns**: id, ownerId, noteTitle, noteContent, promptContent, createDate, deletedAt

### 2. `embedding_v1`
- **Purpose**: Stores vector embeddings for semantic search
- **Used by**: Vector search, hybrid search, RAG processor
- **Key columns**: type, type_id, embedding, chunk_text, section_id

### 3. `conversation_v1`
- **Purpose**: Stores conversations for search
- **Used by**: Conversation search, context retrieval
- **Key columns**: id, ownerId, title, messages, createDate, deletedAt

### 4. `user_v1`
- **Purpose**: User validation and ownership checks
- **Used by**: Authorization, data filtering
- **Key columns**: id, email, name

### 5. `folder_v1`
- **Purpose**: Folder-based note organization and filtering
- **Used by**: Note resolution when folder_ids are provided
- **Key columns**: id, ownerId, name, createDate, deletedAt

### 6. `web_search_cache`
- **Purpose**: Caches web search results to avoid repeated API calls
- **Used by**: Web search processor
- **Key columns**: query_hash, results, created_at, expires_at

## Tables NOT Needed (Can be removed)

These tables exist in production but are not used by the ML server:

### Already Removed:
- `auth_v1` - Authentication (handled by backend server)
- `file_v1` - File storage (handled by backend server)
- `job_v1` - Background jobs (handled by backend server)
- `network_log_v1` - API logging (handled by backend server)
- `prompt_v1` - Prompt templates (not used by ML server)
- `migrations` - Database migrations (backend concern)

### 7. `image_v1`
- **Purpose**: Stores images associated with note parts
- **Used by**: Note embedding generation (extracts text from images)
- **Key columns**: id, partId, imageText, url

### 8. `part_v1`
- **Purpose**: Stores note parts for multi-part notes
- **Used by**: Note embedding generation (processes multi-part content)
- **Key columns**: id, noteId, content, partOrder

## Tables Removed

### Not Used by ML Server:
- `subscription_v1` - Subscription management (handled entirely by backend server)

## Schema Synchronization Rules

1. **Column Names**: Must match production exactly (camelCase with quotes)
   - ✅ `"createDate"`, `"updateDate"`, `"deletedAt"`
   - ❌ `createdate`, `updatedate`, `deletedat`

2. **Minimal Schema**: Only include tables actually used by ML server
3. **Test Data**: Include representative test data for all key features

## Test Data Requirements

- At least one test user (ID: 10001)
- Sample notes with embeddings
- Sample conversations
- Various note types and content for testing different search scenarios