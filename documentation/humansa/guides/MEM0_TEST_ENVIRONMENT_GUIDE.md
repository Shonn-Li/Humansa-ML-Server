# Mem0 Test Environment Guide for Humansa

## Overview

This guide explains how to set up and run the Mem0 integration tests within the existing Humansa test environment. The tests validate memory storage, retrieval, and persistence functionality.

## Test Environment Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Humansa Test Environment                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PostgreSQL (Port 5456)                                  │
│  ├── youwoai database                                   │
│  ├── pgvector extension enabled                         │
│  ├── mem0_test schema (auto-created)                    │
│  └── Test users (10001, 10002, 10003)                  │
│                                                          │
│  Mem0 Memory Layer                                      │
│  ├── Uses existing PostgreSQL                           │
│  ├── Stores memories in mem0_test schema               │
│  └── Can run with mock or real Azure OpenAI            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start the Test Environment

```bash
cd humansa_test_environment
./run_mem0_tests.sh
```

This script will:
- Start the Humansa test database (if not running)
- Set up the Mem0 schema and test data
- Install required Python packages
- Run all 10 test cases
- Generate a test report

### 2. Manual Setup (Alternative)

If you prefer to run steps manually:

```bash
# 1. Start database
cd humansa_test_environment/docker
docker-compose up -d

# 2. Setup Mem0 schema
cd ..
PGPASSWORD=youwo123 psql -h localhost -p 5456 -U youwo -d youwoai < sql/setup_mem0_test.sql

# 3. Install dependencies
pip install mem0ai asyncpg pytest

# 4. Run tests
cd ..
python test_mem0_humansa_integration.py
```

## Test Cases Overview

The test suite includes 10 comprehensive test cases:

### Memory Creation Tests (1-7)
1. **Basic Memory Storage** - Tests simple conversation storage
2. **Medical Context Extraction** - Extracts conditions, medications, allergies
3. **Memory Update and Evolution** - Tests how memories change over time
4. **Multi-Conversation Memory** - Memories across multiple conversations
5. **Appointment Preference Memory** - Stores user preferences
6. **Complex Medical History** - Multiple conditions and medications
7. **Contextual Memory Retrieval** - Semantic search capabilities

### Memory Persistence Tests (8-10)
8. **Memory Persistence Check** - Verifies memories persist
9. **Cross-Session Memory Recall** - Recalls specific information
10. **Comprehensive Patient Summary** - Generates full patient profile

## Configuration

### Environment Variables

```bash
# Database (uses existing Humansa test DB)
DB_HOST=localhost
DB_PORT=5456
DB_USER=youwo
DB_PASSWORD=youwo123
DB_NAME=youwoai

# Azure OpenAI (optional - uses mock if not set)
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
```

### Test Users

The test suite uses three pre-configured users:

| User ID | Description | Test Purpose |
|---------|-------------|--------------|
| 10001 | Test User 1 - No Memory | Clean slate testing |
| 10002 | Test User 2 - With Diabetes | Medical history testing |
| 10003 | Test User 3 - Complex History | Comprehensive testing |

## Running Tests

### Run All Tests
```bash
./run_mem0_tests.sh
```

### Run Specific Test
```python
# In Python
test_suite = Mem0HumansaTestSuite()
await test_suite.setup()
await test_suite.test_01_basic_memory_storage()  # Run specific test
await test_suite.teardown()
```

### Test with Mock Memory (No Azure Required)
The tests automatically fall back to a mock memory implementation if Azure credentials are not provided. This is useful for:
- Local development
- CI/CD pipelines
- Testing without API costs

## Interpreting Results

### Success Output
```
✓ Test passed: Stored 2 memories
✓ Test passed: Found 3 diabetes and 2 allergy memories
✓ Test passed: Memory evolution tracked with 4 medication memories
...
TEST SUMMARY REPORT
Total Tests: 10
Passed: 10
Failed: 0
Success Rate: 100.0%
```

### Test Results File
Results are saved to `mem0_test_results_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "20240125_143022",
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "success_rate": "100.0%"
  },
  "results": [
    {
      "test": "Basic Memory Storage",
      "status": "PASSED",
      "memories_stored": 2
    },
    ...
  ]
}
```

## Database Inspection

### Connect to Test Database
```bash
PGPASSWORD=youwo123 psql -h localhost -p 5456 -U youwo -d youwoai
```

### View Mem0 Tables
```sql
-- Switch to mem0 schema
SET search_path TO mem0_test;

-- List all tables
\dt

-- View stored memories
SELECT * FROM mem0_test_memories WHERE user_id = 'humansa_test_10001';

-- View embeddings
SELECT memory_id, created_at FROM mem0_test_memory_embeddings;
```

### Clean Up Test Data
```sql
-- Remove all test memories
DELETE FROM mem0_test_memories WHERE user_id LIKE 'humansa_test_%';
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if container is running
   docker ps | grep humansa_test_postgres
   
   # Check logs
   docker logs humansa_test_postgres
   ```

2. **pgvector Extension Not Found**
   ```sql
   -- Manually create extension
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Azure API Key Issues**
   - Tests will use mock memory if Azure key is not provided
   - Set `AZURE_OPENAI_API_KEY` for real API testing

4. **Import Errors**
   ```bash
   # Ensure mem0 is installed
   pip install mem0ai --upgrade
   ```

## Integration with ML Server

To integrate Mem0 into your ML server:

1. **Add to requirements.txt**
   ```
   mem0ai>=0.1.0
   asyncpg>=0.27.0
   ```

2. **Initialize in main.py**
   ```python
   from src.humansa.memory.mem0_service import HumansaMemoryService
   
   @app.before_serving
   async def startup():
       app.memory_service = HumansaMemoryService(config)
   ```

3. **Use in Humansa Agent**
   ```python
   # Store conversation
   await app.memory_service.add_conversation(user_id, messages)
   
   # Retrieve context
   context = await app.memory_service.get_user_context(user_id)
   ```

## Next Steps

1. **Run the test suite** to verify Mem0 works in your environment
2. **Review test results** to understand memory capabilities
3. **Implement memory service** in your ML server
4. **Add memory context** to Humansa agent responses

## Summary

The Mem0 test environment provides a comprehensive testing framework for validating memory functionality before production deployment. The 10 test cases cover:
- Basic memory operations
- Medical context extraction
- Memory persistence
- Cross-session recall
- Patient profile building

This ensures the memory system is robust and ready for integration with the Humansa medical AI agent.