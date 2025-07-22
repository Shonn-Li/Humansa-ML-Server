# Test Environment Documentation

## Overview

The YouWoAI ML Server test environment provides an isolated environment for testing multi-agent functionality without affecting production data or services.

## Test Server Setup

### Starting the Test Server

```bash
# Activate virtual environment
source youwo-ml-venv/bin/activate

# Start test server on port 5002
python test_server.py
```

The test server will:
- Run on port 5002 (not 5001 which is production)
- Use test database at `postgresql://localhost:5454/youwoai_test`
- Load test fixtures automatically
- Provide isolated environment for testing

### Test Database

The test database includes pre-seeded data:
- Test user ID: 10001
- Sample notes with IDs 10001-10009
- Sample conversations
- Pre-computed embeddings for RAG testing

## Running Tests

### Comprehensive Test Suite

```bash
# With test server running on port 5002
python test_multi_agent_comprehensive.py
```

This runs 30+ test cases covering:
- Basic queries
- Context search (notes/conversations)
- File attachments
- Web search
- Code interpreter
- Multi-agent combinations
- Edge cases

### Quick Test Suite

```bash
# For faster validation
python test_multi_agent_quick.py
```

Runs 5 critical tests focusing on tool separation.

## Important Notes

### Tool Type Separation

As of the latest update, the system uses specific tool types:
- `context_search_call` - For searching user's notes and conversations
- `file_search_call` - For processing file attachments only
- `web_search_call` - For web searches
- `code_interpreter_call` - For code execution

### Common Issues

1. **Port Conflicts**: Ensure port 5002 is free before starting test server
2. **Database Connection**: Test database must be running on port 5454
3. **Environment Variables**: Test server sets all required env vars automatically

### Test Data

Test notes include:
- Note 10001: PARL (Predictability-Aware Reinforcement Learning)
- Note 10002: G1 and graph reasoning
- Note 10003: Multimodal reasoning challenges
- Note 10004: AI startup ideas
- Note 10009: Machine learning conversations

## Debugging

Enable verbose logging:
```python
# In test files
logging.getLogger("chat").setLevel(logging.DEBUG)
```

Check test server logs for:
- Agent routing decisions
- Tool selection
- Citation generation
- Error traces

## Best Practices

1. **Always use port 5002** for testing, never 5001 (production)
2. **Run test server** before executing test suites
3. **Check test fixtures** are loaded properly
4. **Validate tool types** match expected format
5. **Monitor memory usage** during long test runs