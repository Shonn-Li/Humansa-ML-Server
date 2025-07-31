# HUMANSA V2 Test Environment Guide

## Overview

This guide provides comprehensive documentation for setting up and running tests for the HUMANSA V2 system.

## Test Environment Configuration

### Database Configuration

⚠️ **CRITICAL**: The test environment uses specific configurations that differ from docker-compose.yml:

```bash
# ACTUAL Test Environment Settings
Container Name: youwoai_test_db (NOT humansa_test_postgres)
ML Server Port: 6001 (test instance)
PostgreSQL Port: 5454 (Docker container)
Database Name: test4 (primary), youwoai_test (secondary)
Password: 12931 (NOT 031203 from docker-compose.yml!)
User: postgres
```

### Verifying Test Database

```bash
# Check if test database is running
docker ps | grep youwoai_test_db

# Test database connection
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1;"

# Check tables
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "\dt humansa_*;"
```

## Test Categories

### 1. Core Functionality Tests (30 tests)

**File**: `test_HUMANSA_v2_comprehensive_enhanced.py`

**Categories**:
- Identity Recognition (20 tests)
- Memory System (10 tests)

**Run**:
```bash
source youwo-ml-venv/bin/activate
python test_HUMANSA_v2_comprehensive_enhanced.py
```

### 2. Comprehensive Test Suite (70 tests)

**File**: `test_HUMANSA_v2_70_cases_multiturn.py`

**Features**:
- Multi-turn conversations
- Complex medical scenarios
- Memory persistence
- Tool integration

**Run**:
```bash
./run_HUMANSA_v2_test_40_cases_enhanced.sh
# or
python test_HUMANSA_v2_70_cases_multiturn.py
```

### 3. Response Agent Tests

**File**: `test_response_agent_fix.py`

**Tests**:
- Identity enforcement
- Template application
- Error beautification
- Brand consistency

**Run**:
```bash
python test_response_agent_fix.py
```

### 4. Key Improvements Tests

**File**: `test_key_improvements.py`

**Focus Areas**:
- Critical functionality (100% pass rate required)
- Emergency handling
- Tool selection
- Response processing

**Run**:
```bash
python test_key_improvements.py
```

## Test Data Setup

### 1. Database Schema

```sql
-- Create test tables
CREATE TABLE IF NOT EXISTS humansa_clinics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    city VARCHAR(100),
    address TEXT,
    phone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS humansa_doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    title VARCHAR(100),
    specialty VARCHAR(100),
    clinic_id INTEGER REFERENCES humansa_clinics(id)
);

CREATE TABLE IF NOT EXISTS humansa_appointments (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    doctor_id INTEGER,
    appointment_time TIMESTAMP,
    status VARCHAR(50)
);
```

### 2. Sample Test Data

```sql
-- Insert test clinics
INSERT INTO humansa_clinics (name, city, address, phone) VALUES
('北京诊所', '北京', '北京市朝阳区国贸CBD中心', '010-10000000'),
('深圳诊所', '深圳', '深圳市南山区科技园', '0755-20000000'),
('上海诊所', '上海', '上海市浦东新区陆家嘴', '021-30000000');

-- Insert test doctors
INSERT INTO humansa_doctors (name, title, specialty, clinic_id) VALUES
('Dr. 张伟', '主任医师', '心脏科', 1),
('Dr. 李丽', '副主任医师', '妇科', 2),
('Dr. 王强', '主任医师', '骨科', 3);
```

## Running Tests with Enhanced Logging

### Enable Enhanced Logging

```bash
# Environment variable
export HUMANSA_ENHANCED_LOGGING=true

# Or in test request
{
  "debug": true,
  "stream": true
}
```

### Enhanced Logging Output

```
🤔 正在思考...
💭 **思考**: User wants to book appointment
🔧 **行动**: appointment_manager
📊 **观察结果**: Available slots found
✅ **最终回答**: Dr. Li has appointments available...
```

## Test Scripts

### 1. Full Test Suite Runner

```bash
#!/bin/bash
# run_all_tests.sh

# Activate environment
source youwo-ml-venv/bin/activate

# Run tests in sequence
echo "Running Core Tests..."
python test_HUMANSA_v2_comprehensive_enhanced.py

echo "Running Response Agent Tests..."
python test_response_agent_fix.py

echo "Running Key Improvements Tests..."
python test_key_improvements.py

echo "Running Tool Selection Tests..."
python test_tool_selection.py
```

### 2. Quick Smoke Test

```python
#!/usr/bin/env python3
# smoke_test.py

import asyncio
import aiohttp

async def smoke_test():
    async with aiohttp.ClientSession() as session:
        # Health check
        async with session.get("http://localhost:6001/v2/humansa/health") as resp:
            if resp.status == 200:
                print("✅ Health check passed")
            else:
                print("❌ Health check failed")
                return
        
        # Identity test
        data = {
            "model": "gpt-4-turbo",
            "input": "你是谁？",
            "user_id": "smoke_test"
        }
        async with session.post(
            "http://localhost:6001/v2/humansa/responses/create",
            json=data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                text = result.get("output", [{}])[0].get("text", "")
                if "诺亚新舟" in text and "小诺" in text:
                    print("✅ Identity test passed")
                else:
                    print("❌ Identity test failed")
            else:
                print("❌ API call failed")

if __name__ == "__main__":
    asyncio.run(smoke_test())
```

## Performance Testing

### Load Testing Script

```python
#!/usr/bin/env python3
# load_test.py

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

QUERIES = [
    "我想预约明天的医生",
    "我头疼怎么办",
    "诊所的营业时间",
    "我想买保健品",
    "你是谁？"
]

async def single_request(session, query, user_id):
    start = time.time()
    data = {
        "model": "gpt-4-turbo",
        "input": query,
        "user_id": f"load_test_{user_id}"
    }
    
    try:
        async with session.post(
            "http://localhost:6001/v2/humansa/responses/create",
            json=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                await resp.json()
                return time.time() - start
            else:
                return None
    except:
        return None

async def load_test(concurrent_users=5, requests_per_user=10):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for user in range(concurrent_users):
            for req in range(requests_per_user):
                query = QUERIES[req % len(QUERIES)]
                tasks.append(single_request(session, query, user))
        
        results = await asyncio.gather(*tasks)
        successful = [r for r in results if r is not None]
        
        print(f"\nLoad Test Results:")
        print(f"Total Requests: {len(tasks)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(tasks) - len(successful)}")
        if successful:
            print(f"Avg Response Time: {sum(successful)/len(successful):.2f}s")
            print(f"Min Response Time: {min(successful):.2f}s")
            print(f"Max Response Time: {max(successful):.2f}s")

if __name__ == "__main__":
    asyncio.run(load_test())
```

## Debugging Tests

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Inspect Tool Calls

```python
# In test file
response = await test_query(session, "我想找心脏科医生")
print("Tools called:", response.get("metadata", {}).get("tools_used", []))
print("Response type:", response.get("metadata", {}).get("response_type"))
```

### 3. Memory Debugging

```bash
# Check memory entries
curl http://localhost:6001/v2/humansa/memory/context/test_user_001 | jq .

# Clear memory for clean test
curl -X POST http://localhost:6001/v2/humansa/memory/clear/test_user_001
```

## Common Test Issues

### 1. Database Connection Issues

```bash
# Reset database
docker-compose down
docker-compose up -d db
sleep 5
python scripts/setup_database.py
```

### 2. Memory Test Failures

- Ensure Mem0 is initialized
- Check user_id format (must be string)
- Verify memory not cleared between tests

### 3. Tool Selection Issues

- Review keyword matching in `consolidated_tools.py`
- Check max_tools limit (default 5)
- Verify tool initialization

## Test Metrics

### Expected Pass Rates

- **Identity Tests**: 100%
- **Emergency Tests**: 100%
- **Tool Selection**: 80%+
- **Memory Recall**: 85%+
- **Overall**: 82%+

### Performance Benchmarks

- Average Response Time: < 4 seconds
- Streaming First Token: < 1 second
- Memory Operations: < 100ms
- Tool Execution: < 2 seconds

## CI/CD Integration

### GitHub Actions Example

```yaml
name: HUMANSA V2 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: 12931
          POSTGRES_DB: test4
        ports:
          - 5454:5432
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        DB_PASSWORD: 12931
      run: |
        python test_key_improvements.py
        python test_response_agent_fix.py
```

## Test Reports

### Generating Test Reports

```python
# test_report_generator.py
import json
from datetime import datetime

def generate_report(test_results):
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": len(test_results),
            "passed": sum(1 for r in test_results if r["passed"]),
            "failed": sum(1 for r in test_results if not r["passed"])
        },
        "details": test_results
    }
    
    with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return report
```

## Best Practices

1. **Always use virtual environment**
2. **Check server health before tests**
3. **Use unique user_ids for parallel tests**
4. **Clean up test data after runs**
5. **Monitor response times**
6. **Test with enhanced logging for debugging**
7. **Run smoke tests before full suite**