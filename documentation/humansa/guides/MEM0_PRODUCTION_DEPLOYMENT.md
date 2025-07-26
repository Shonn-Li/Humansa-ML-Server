# Mem0 Production Deployment Guide

## Overview

This guide explains how Mem0 is deployed in both test and production environments for the Humansa system.

## Deployment Strategy

### Test Environment
- **Setup**: SQL script creates schema and test data
- **Database**: Isolated test database on port 5456
- **Initialization**: Automatic via `setup.sh`

### Production Environment
- **Setup**: Mem0 self-manages schema creation
- **Database**: Production database
- **Initialization**: Automatic on first run

## How It Works

### 1. **Test Environment Flow**

```bash
# When you run:
./run_humansa_test_environment.sh

# It does:
1. Starts test database (port 5456)
2. Runs setup.sh which:
   - Creates base schema
   - Runs setup_mem0.sh
   - Creates mem0_test schema
   - Installs mem0ai package
3. ML Server starts and:
   - Detects test environment
   - Connects to test database
   - Mem0 auto-creates tables in mem0_test schema
```

### 2. **Production Environment Flow**

```python
# When ML Server starts in production:

1. main.py executes
2. @app.before_serving runs
3. Mem0Manager.initialize() is called:
   - Checks if schema exists
   - Creates schema if needed (mem0_humansa_prod)
   - Mem0 auto-creates its tables
   - No manual migration needed!
```

## Key Differences

| Aspect | Test Environment | Production |
|--------|-----------------|------------|
| Schema Creation | SQL script | Mem0 auto-creates |
| Schema Name | mem0_test | mem0_humansa_prod |
| Port | 5456 | 5432 (default) |
| Initialization | setup_mem0.sh | Automatic on startup |
| Test Data | Pre-loaded | Empty initially |

## Production Configuration

### Environment Variables

```bash
# Production .env file
ENVIRONMENT=prod
DB_HOST=your-prod-host
DB_PORT=5432
DB_USER=your-user
DB_PASSWORD=your-password
DB_NAME=youwoai

# Azure OpenAI (or regular OpenAI)
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding-ada-002

# Mem0 will use schema: mem0_humansa_prod
```

### What Happens on First Run

1. **ML Server starts**
   ```
   python -m src.main
   ```

2. **Mem0Manager initializes**
   ```python
   # Automatically:
   - Creates schema "mem0_humansa_prod" if not exists
   - Grants permissions to DB user
   - Ensures pgvector extension is enabled
   ```

3. **Mem0 creates tables**
   ```sql
   -- Automatically created by Mem0:
   - mem0_humansa_prod.memories
   - mem0_humansa_prod.memory_embeddings
   - mem0_humansa_prod.memory_history
   ```

4. **Ready to use!**
   - No manual migration needed
   - No backend server changes required

## Backend Server Considerations

### No Migration Needed

The backend server (NestJS) does **NOT** need any migrations for Mem0 because:

1. Mem0 uses its own schema (mem0_humansa_prod)
2. Backend doesn't directly access Mem0 tables
3. All memory operations go through ML Server APIs

### Optional: Schema Creation Migration

If you want the backend to ensure the schema exists (optional):

```typescript
// Optional migration (not required)
export class CreateMem0Schema implements MigrationInterface {
    async up(queryRunner: QueryRunner): Promise<void> {
        // Just create schema - Mem0 handles tables
        await queryRunner.query(`
            CREATE SCHEMA IF NOT EXISTS mem0_humansa_prod
        `);
    }
}
```

But this is **NOT NECESSARY** - Mem0Manager handles it automatically.

## Monitoring

### Check Initialization

Watch ML Server logs for:
```
✅ Mem0 memory layer initialized for Humansa
```

Or warnings:
```
⚠️ Mem0 initialization failed - memory features disabled
⚠️ Mem0 not available: [error details]
```

### Verify Tables

```sql
-- Check if Mem0 tables exist
\dt mem0_humansa_prod.*

-- Should show:
-- mem0_humansa_prod.memories
-- mem0_humansa_prod.memory_embeddings
-- etc.
```

### Test Memory Operations

```python
# Quick test via API
curl -X POST http://localhost:5001/v2/humansa/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [
      {"role": "user", "content": "Test message"}
    ]
  }'
```

## Troubleshooting

### If Mem0 doesn't initialize:

1. **Check logs** for specific error
2. **Verify pgvector** is installed:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. **Check API keys** are set correctly
4. **Verify database permissions**

### If tables aren't created:

1. Mem0 creates tables on **first use**, not just initialization
2. Try adding a test memory to trigger table creation
3. Check schema permissions

## Summary

- **Test Environment**: Fully automated setup with `run_humansa_test_environment.sh`
- **Production**: Mem0 self-manages everything on first run
- **No backend changes needed**: ML Server handles all memory operations
- **No manual migrations**: Mem0 creates its own schema and tables

The system is designed for zero-friction deployment where Mem0 automatically sets up everything it needs when the ML Server starts.