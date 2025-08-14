# YouWoAI Test Environment Status

## ✅ Test Environment is INTACT

The YouWoAI test environment and database remain fully functional after Humansa removal.

## Database Configuration

### Connection Details
- **Host**: localhost
- **Port**: 5454
- **Database**: youwoai_test (or test4)
- **Username**: postgres
- **Password**: 12931
- **Container**: youwoai_test_db

### Test Data Available

#### Core YouWoAI Tables (INTACT)
- ✅ `user_v1` - Test users with configurations
- ✅ `folder_v1` - Test folders (June-ML, Startup)
- ✅ `note_v1` - 9+ test notes (YouTube, PDFs, audio, documents)
- ✅ `conversation_v1` - Test conversations with proper titles
- ✅ `part_v1` - Conversation parts/messages
- ✅ `image_v1` - Image attachments
- ✅ `subscription_v1` - Subscription data

#### Embeddings & Vectors
- ✅ 190 real embeddings from production
- ✅ pgvector extension enabled
- ✅ Embedding search capabilities

#### Test Features
- ✅ Multi-language support (Chinese and English)
- ✅ Various conversation depths (4-6 messages each)
- ✅ Technical Q&A on research papers
- ✅ Startup and business discussions

## Test Dashboard

### Configuration (`test_dashboard/backend/dashboard_settings.json`)
```json
{
  "multi_instance": {
    "enabled": true,
    "default_instances": 4,
    "auto_start": true,
    "max_workers_per_job": 4
  },
  "ml_server_port": 6001,
  "ml_server_digit": 1,
  "enable_enhanced_logging": true,
  "auto_discover_tests": true
}
```

## SQL Files Structure

### Core YouWoAI Setup (INTACT)
- `02_create_tables.sql` - Core YouWoAI schema
- `03_test_data.sql` - YouWoAI test data
- `05_test_conversations.sql` - Conversation test data
- `10_test_management_schema.sql` - Test management tables

### Mixed Content Files
Some SQL files contain both YouWoAI and Humansa tables:
- `create_missing_tables.sql`
- `fix_schema_and_add_test_data.sql`
- `insert_comprehensive_test_data.sql`

**Note**: These mixed files can be cleaned up if needed, but the core YouWoAI tables remain unaffected.

## Quick Start

### 1. Start Test Database
```bash
cd test_environment
docker-compose up -d
```

### 2. Verify Database
```bash
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test -c "\dt"
```

### 3. Load Test Data (if needed)
```bash
cd test_environment/sql
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test < 02_create_tables.sql
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test < 03_test_data.sql
```

### 4. Run Tests
```bash
cd test_dashboard
./launch_dashboard.sh
```

## Status Summary

✅ **YouWoAI Test Environment**: Fully functional
✅ **Test Database**: Intact with all YouWoAI tables
✅ **Test Data**: Complete dataset available
✅ **Test Dashboard**: Operational
⚠️ **Minor Issue**: Some SQL files contain mixed Humansa references (can be cleaned if needed)

The test environment is ready for YouWoAI testing and development!