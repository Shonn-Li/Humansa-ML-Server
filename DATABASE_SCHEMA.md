# YouWoAI Database Schema Documentation

Generated from actual database schema to prevent column name issues.

## Tables and Columns


### conversation_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('conversation_v1_id_seq'::regclass) |
| ownerId | integer | YES |  |
| type | USER-DEFINED | NO | 'user'::conversation_type_enum |
| threadId | character varying | YES |  |
| assistantid | character varying | NO | ''::character varying |
| messages | jsonb | NO | '[]'::jsonb |
| messagessynced | boolean | NO | false |
| typeid | integer | YES |  |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| title | character varying | YES |  |
| skipembedding | boolean | NO | false |

### embedding_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| section_id | integer | NO |  |
| last_updated | timestamp with time zone | NO | now() |
| embedding | USER-DEFINED | YES |  |
| chunk_text | text | YES |  |
| source | character varying | YES |  |
| chunk_tsv | tsvector | YES |  |
| type_id | integer | NO |  |
| type | character varying | NO |  |
| url | text | YES |  |
| metadata | jsonb | YES |  |

### folder_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('folder_v1_id_seq'::regclass) |
| ownerId | integer | NO |  |
| folderTitle | character varying | NO |  |
| conversationId | integer | YES |  |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| sharesettings | jsonb | YES | '{"isPublic": false, "trackViews": false, "allo... |
| globaltemplatesettings | jsonb | YES |  |

### image_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('image_v1_id_seq'::regclass) |
| partId | integer | YES |  |
| noteId | integer | NO |  |
| imageURL | character varying | YES |  |
| imageText | character varying | YES |  |
| latex | boolean | NO |  |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| clientId | uuid | YES |  |
| partClientId | uuid | YES |  |

### note_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('note_v1_id_seq'::regclass) |
| ownerId | integer | YES |  |
| folderId | integer | YES |  |
| noteTitle | character varying | NO |  |
| completed | boolean | NO | false |
| audioURL | character varying | YES |  |
| timeFrom | time without time zone | YES |  |
| timeTo | time without time zone | YES |  |
| promptid | integer | YES |  |
| promptcontent | jsonb | NO | '{"promptContent": null, "promptContentHistory"... |
| conversationId | integer | YES |  |
| deviceType | character varying | YES |  |
| language | character varying | NO |  |
| notesubscriptionusage | jsonb | NO | '{"chatBotUsage": 0, "imageToTextUsage": 0, "pr... |
| quizcontent | jsonb | YES |  |
| flashcardcontent | jsonb | YES |  |
| aiNoteContent | character varying | YES |  |
| notetype | character varying | NO | 'audio'::character varying |
| linkURL | character varying | YES |  |
| noteTranscriptionServiceUsed | character varying | YES |  |
| notecontent | jsonb | YES |  |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| fileURL | character varying | YES |  |
| skipembedding | boolean | NO | false |
| sharesettings | jsonb | YES | '{"isPublic": false, "trackViews": false, "allo... |

### part_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('part_v1_id_seq'::regclass) |
| noteId | integer | NO |  |
| order | integer | NO |  |
| timeFrom | time without time zone | YES |  |
| timeTo | time without time zone | YES |  |
| text | character varying | NO |  |
| words | jsonb | YES |  |
| translations | jsonb | YES |  |
| completed | boolean | NO | false |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| clientId | uuid | YES |  |

### subscription_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('subscription_v1_id_seq'::regclass) |
| name | character varying | NO | 'free'::character varying |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |

### user_v1

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('user_v1_id_seq'::regclass) |
| email | character varying | YES |  |
| username | character varying | NO |  |
| discriminator | character varying | NO | '0001'::character varying |
| phoneNumber | character varying | YES |  |
| isactive | boolean | NO | true |
| emailverified | boolean | NO | false |
| settings | jsonb | NO | '{"AIType": "gpt-4", "fontSize": "16", "hideGma... |
| conversationId | integer | YES |  |
| role | character varying | NO | 'user'::character varying |
| subscriptionId | integer | YES | 1 |
| profileURL | character varying | YES |  |
| mode | character varying | NO | 'personal'::character varying |
| createdate | timestamp with time zone | NO | now() |
| updatedate | timestamp with time zone | NO | now() |
| deletedat | timestamp with time zone | YES |  |
| devices | jsonb | NO | '[]'::jsonb |
| stripeCustomerId | character varying | YES |  |

### web_search_cache

| Column Name | Data Type | Nullable | Default |
|-------------|-----------|----------|---------|
| id | integer | NO | nextval('web_search_cache_id_seq'::regclass) |
| query_hash | character varying | NO |  |
| original_query | text | NO |  |
| results | jsonb | NO |  |
| created_at | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| expires_at | timestamp without time zone | NO |  |