# Timeout Configuration Recommendations

Based on testing, the multi-agent system requires longer timeouts for complex queries. Here are the recommended timeout settings:

## Observed Execution Times

- Simple queries (no agents): 2-5 seconds
- Single agent queries: 7-10 seconds  
- Context search queries: 20-30 seconds
- Multi-agent queries: 15-40 seconds
- Iterative refinement: Can add 10-20 seconds per iteration

## Recommended Timeout Settings

### 1. Test Configuration
```python
# For test files
import aiohttp

# Basic tests
timeout = aiohttp.ClientTimeout(total=60, connect=10)

# Complex tests (multi-agent, iterations)
timeout = aiohttp.ClientTimeout(total=180, connect=10)

# Stress tests
timeout = aiohttp.ClientTimeout(total=300, connect=10)
```

### 2. Server Configuration
Update Azure session manager timeout:
```python
# src/utils/azure_session_manager.py
session = aiohttp.ClientSession(
    connector=connector,
    timeout=aiohttp.ClientTimeout(total=180, connect=30)  # Increase from 120
)
```

### 3. Command Line Testing
When running tests via command line:
```bash
# Use longer timeout for comprehensive tests
python run_tests.py  # Should have 5-minute internal timeout

# For quick tests
python test_minimal.py  # 60-second timeout is sufficient
```

### 4. Production Recommendations

Consider implementing:
1. **Configurable timeouts** based on query complexity
2. **Progress indicators** for long-running queries
3. **Query complexity estimation** to set dynamic timeouts
4. **Timeout warnings** in responses when approaching limits

### 5. Client-Side Considerations

Clients calling the API should:
- Set timeouts to at least 60 seconds for basic queries
- Use 180+ seconds for complex multi-agent queries
- Implement retry logic for timeout errors
- Show progress indicators for long operations

## Why These Timeouts?

1. **LLM Response Times**: Each LLM call can take 5-15 seconds
2. **RAG Operations**: Embedding search and retrieval adds 5-10 seconds
3. **Multi-Agent Coordination**: Each agent adds cumulative time
4. **Iteration Overhead**: Quality checks and re-runs add significant time

## Testing Strategy

1. Run minimal tests first to verify basic functionality
2. Use extended timeouts only for comprehensive test suites
3. Monitor actual execution times to refine timeout settings
4. Consider parallel test execution for faster overall testing