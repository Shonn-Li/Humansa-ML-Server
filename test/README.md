# YouWoAI ML Server Test Suite

## Directory Structure

```
test/
├── core/                    # Core test infrastructure
│   ├── validate.py         # Quick validation tests (used by test.sh)
│   ├── test_comprehensive_detailed.py  # Full test suite
│   └── test_server.py      # Test server (runs on port 5002)
│
├── multi_agent/            # Multi-agent specific tests
│   ├── test_multi_agent_comprehensive.py  # 30+ comprehensive tests
│   ├── test_multi_agent_quick.py         # Quick critical tests
│   └── test_multi_agent.py               # Additional multi-agent tests
│
├── integration/            # Integration tests
│   ├── test_context_search.py
│   ├── test_direct_endpoint.py
│   ├── test_environment_validation.py
│   └── test_environment_working.py
│
├── unit/                   # Unit tests (to be organized)
│
└── utilities/              # Test utilities and helpers

tests/                      # Legacy test directory (to be cleaned up)
test_backup/               # Backup of old tests (to be reviewed)
```

## Running Tests

### Quick Tests (Default)
```bash
./test.sh           # Runs validate.py
./test.sh quick     # Same as above
```

### Full Test Suite
```bash
./test.sh full      # Runs test_comprehensive_detailed.py
```

### With Test Server
```bash
# Terminal 1: Start test server
python test/core/test_server.py

# Terminal 2: Run tests
python test/multi_agent/test_multi_agent_comprehensive.py
python test/multi_agent/test_multi_agent_quick.py
```

## Test Environment

- Test Server Port: **5002** (NOT 5001)
- Test Database: PostgreSQL on port 5454
- Test User ID: 10001
- Pre-seeded test data with embeddings

## Important Notes

1. **Always use port 5002** for testing, never port 5001
2. **Activate virtual environment** before running tests:
   ```bash
   source youwo-ml-venv/bin/activate
   ```
3. Tests use isolated test database to avoid impacting production data