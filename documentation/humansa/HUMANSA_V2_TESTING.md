# Humansa V2 Testing Documentation

## Overview

This document describes the two core test suites for Humansa V2 with Mem0 integration. These tests validate memory persistence, multi-agent workflows, and the complete user experience.

## Test Architecture

```mermaid
graph TB
    subgraph "Test Environment (Port 5456)"
        TDB[(Test PostgreSQL<br/>Database)]
        TDATA[Test Data<br/>Users: 10001-10003]
    end
    
    subgraph "Core Test Suites"
        T1[test_mem0_humansa_integration.py<br/>Memory Operations Test]
        T2[test_mem0_v2_integration.py<br/>API Integration Test]
    end
    
    subgraph "Test Coverage"
        MEM[Memory Storage<br/>& Retrieval]
        PERS[Memory<br/>Persistence]
        API[API Endpoint<br/>Testing]
        WORK[Workflow<br/>Integration]
    end
    
    T1 --> MEM
    T1 --> PERS
    T2 --> API
    T2 --> WORK
    
    T1 --> TDB
    T2 --> TDB
    TDB --> TDATA
    
    style T1 fill:#9f9,stroke:#333,stroke-width:2px
    style T2 fill:#bbf,stroke:#333,stroke-width:2px
```

## Test Suite 1: Mem0 Integration Tests

**File**: `test_mem0_humansa_integration.py`

### Purpose
Comprehensive testing of Mem0 memory operations including storage, retrieval, categorization, and persistence.

### Test Users
- **User 10001**: Clean slate user (no prior history)
- **User 10002**: Diabetes patient with medication history
- **User 10003**: Complex patient with multiple conditions

### Test Flow

```mermaid
graph TD
    subgraph "Setup Phase"
        S1[Initialize Test Environment]
        S2[Connect to Test DB<br/>Port 5456]
        S3[Initialize Mem0]
        S4[Clear Existing Memories]
    end
    
    subgraph "Memory Creation Tests (1-7)"
        T1[Test 1: Basic Memory Storage<br/>Store preferences]
        T2[Test 2: Medical Context<br/>Extract conditions]
        T3[Test 3: Memory Evolution<br/>Update medications]
        T4[Test 4: Multi-Conversation<br/>Track symptoms]
        T5[Test 5: Appointment Preferences<br/>Store scheduling]
        T6[Test 6: Complex History<br/>Multiple conditions]
        T7[Test 7: Contextual Retrieval<br/>Semantic search]
    end
    
    subgraph "Persistence Tests (8-10)"
        T8[Test 8: Verify Persistence<br/>Check all users]
        T9[Test 9: Cross-Session Recall<br/>Specific queries]
        T10[Test 10: Patient Summary<br/>Comprehensive profile]
    end
    
    S1 --> S2 --> S3 --> S4
    S4 --> T1 --> T2 --> T3 --> T4 --> T5 --> T6 --> T7
    T7 --> T8 --> T9 --> T10
    
    style S1 fill:#ffd,stroke:#333,stroke-width:2px
    style T1 fill:#9f9,stroke:#333,stroke-width:2px
    style T8 fill:#bbf,stroke:#333,stroke-width:2px
```

### Test Cases Detail

#### Test 1: Basic Memory Storage
```python
# Input
messages = [
    {"role": "user", "content": "I prefer morning appointments around 9 AM"},
    {"role": "assistant", "content": "I've noted your preference..."}
]

# Verification
- Memory is stored successfully
- Preference is retrievable
- User context includes the preference
```

#### Test 2: Medical Context Extraction
```python
# Input
"I have type 2 diabetes and take metformin daily"
"I'm also allergic to penicillin"

# Verification
- Condition: diabetes extracted
- Medication: metformin identified
- Allergy: penicillin recorded
```

#### Test 3: Memory Update and Evolution
```python
# Scenario
1. Initial: "Taking metformin"
2. Update: "Changed to insulin"

# Verification
- Both medications in history
- Current medication is insulin
- Historical context preserved
```

#### Test 4-7: Advanced Scenarios
- Multi-conversation tracking
- Appointment preferences
- Complex medical histories
- Semantic search capabilities

#### Test 8-10: Persistence Validation
- Memories persist across sessions
- Specific recall works correctly
- Comprehensive summaries generated

### Expected Output Structure
```json
{
  "timestamp": "20250725_120000",
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
      "memories_stored": 1
    }
  ]
}
```

## Test Suite 2: V2 API Integration Tests

**File**: `test_mem0_v2_integration.py`

### Purpose
Validate that Mem0 is properly integrated into the V2 API workflow and memory context influences responses.

### Test Flow

```mermaid
sequenceDiagram
    participant T as Test Script
    participant API as ML Server API
    participant MEM as Memory System
    participant ORCH as Orchestrator
    
    rect rgb(240, 240, 240)
        Note over T,ORCH: Test 1: Check Status
        T->>API: GET /v2/humansa/memory/status
        API->>MEM: Check initialization
        MEM-->>API: Status details
        API-->>T: {"initialized": true, ...}
    end
    
    rect rgb(240, 255, 240)
        Note over T,ORCH: Test 2: Add Memory
        T->>API: POST /v2/humansa/memory/add
        Note right of T: "Allergic to penicillin"
        API->>MEM: Store conversation
        MEM-->>API: Success
        API-->>T: {"status": "success"}
    end
    
    rect rgb(255, 240, 240)
        Note over T,ORCH: Test 3: Chat with Context
        T->>API: POST /v2/humansa/chat
        Note right of T: "What medications to avoid?"
        API->>ORCH: Process query
        ORCH->>MEM: Load user context
        MEM-->>ORCH: Allergy: penicillin
        ORCH->>ORCH: Generate response<br/>mentioning penicillin
        ORCH-->>API: Response
        API-->>T: "Avoid penicillin..."
    end
```

### API Tests Detail

#### 1. Memory Status Check
```bash
GET /v2/humansa/memory/status

Expected Response:
{
  "initialized": true,
  "environment": "mem0_test_memories",
  "connectivity": "healthy",
  "features": ["semantic_search", "memory_extraction", ...]
}
```

#### 2. Memory Addition
```bash
POST /v2/humansa/memory/add
{
  "user_id": 10001,
  "messages": [
    {"role": "user", "content": "I'm allergic to penicillin"},
    {"role": "assistant", "content": "Noted your penicillin allergy"}
  ]
}
```

#### 3. Context-Aware Chat
```bash
POST /v2/humansa/chat
{
  "user_id": 10001,
  "messages": [
    {"role": "user", "content": "What medications should I avoid?"}
  ]
}

Expected: Response mentions penicillin allergy
```

#### 4. Memory Search
```bash
POST /v2/humansa/memory/search
{
  "user_id": 10001,
  "query": "allergies medications"
}
```

#### 5. User Context Retrieval
```bash
GET /v2/humansa/memory/context/10001

Expected: Structured context with categorized memories
```

#### 6. Persistence Verification
Second chat to verify memories persist and influence responses.

## Running the Tests

### Option 1: Full Environment + Tests
```bash
# Starts environment and runs all tests automatically
./run_humansa_test_with_mem0.sh
```

### Option 2: Manual Test Execution
```bash
# 1. Start test environment
./run_humansa_test_environment.sh

# 2. Wait for services
sleep 10

# 3. Run memory tests
python test_mem0_humansa_integration.py

# 4. Run API tests
python test_mem0_v2_integration.py
```

### Option 3: Quick API Test
```bash
# Check if memory is working
curl -X POST http://localhost:5001/v2/humansa/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [
      {"role": "user", "content": "I have a peanut allergy"},
      {"role": "assistant", "content": "Noted your peanut allergy"}
    ]
  }'

# Test if context is used
curl -X POST http://localhost:5001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [
      {"role": "user", "content": "Can I eat this granola bar?"}
    ],
    "stream": false
  }'
```

## Test Data Structure

### Memory Categories
```mermaid
graph LR
    subgraph "Raw Memories"
        M1[Conversation 1]
        M2[Conversation 2]
        M3[Conversation N]
    end
    
    subgraph "Categorized Data"
        MED[Medications<br/>- Current<br/>- Historical]
        ALL[Allergies<br/>- Drugs<br/>- Foods]
        PREF[Preferences<br/>- Appointments<br/>- Doctors]
        HIST[Medical History<br/>- Conditions<br/>- Procedures]
    end
    
    M1 --> CAT{Categorization<br/>Engine}
    M2 --> CAT
    M3 --> CAT
    
    CAT --> MED
    CAT --> ALL
    CAT --> PREF
    CAT --> HIST
```

## Success Criteria

### Memory Tests (Suite 1)
- ✅ All 10 test cases pass
- ✅ Memories persist across test runs
- ✅ Semantic search returns relevant results
- ✅ Patient summaries are comprehensive

### API Tests (Suite 2)
- ✅ Mem0 status shows initialized
- ✅ Memories can be added via API
- ✅ Chat responses use memory context
- ✅ Search returns relevant memories
- ✅ Context includes categorized data

## Common Issues and Solutions

### Issue: Mem0 Not Initialized
```
Error: "Mem0 is not initialized"
```
**Solution**: 
- Check environment variables (OPENAI_API_KEY or AZURE_OPENAI_*)
- Verify database connection
- Restart ML server

### Issue: Memories Not Persisting
```
Symptom: Test 8 fails, no memories found
```
**Solution**:
- Check schema exists: `mem0_test`
- Verify pgvector extension enabled
- Check database permissions

### Issue: Context Not Used in Chat
```
Symptom: Chat doesn't mention stored information
```
**Solution**:
- Verify Mem0MemoryManagerAdapter is being used
- Check orchestrator loads context before processing
- Ensure user_id format is correct

## Test Outputs

### Console Output Example
```
=================================================
Humansa Test Environment with Mem0 Testing
=================================================

Step 1: Starting Humansa test environment...
✓ Test database running on port 5456

Step 2: Checking ML server health...
✓ ML Server is healthy

Step 3: Verifying database connectivity...
✓ Database is accessible

Step 4: Checking Mem0 schema...
✓ Mem0 test schema exists

Step 5: Setting up Python environment...
✓ Virtual environment activated

Step 6: Running Mem0 integration tests...
Test 1: Basic Memory Storage
✓ Test passed: Stored 1 memories

[... more tests ...]

TEST SUMMARY REPORT
==================
Total Tests: 10
Passed: 10
Failed: 0
Success Rate: 100.0%
```

### JSON Report Structure
```json
{
  "timestamp": "20250725_150000",
  "environment": {
    "db_port": 5456,
    "ml_server_port": 5001,
    "test_users": [10001, 10002, 10003]
  },
  "test_results": {
    "memory_tests": {
      "total": 10,
      "passed": 10,
      "failed": 0
    },
    "api_tests": {
      "total": 6,
      "passed": 6,
      "failed": 0
    }
  }
}
```

## Best Practices

1. **Always Clear Test Data**: Run clear_test_memories() before tests
2. **Use Test Users**: Stick to 10001-10003 for consistency
3. **Check Logs**: ML server logs show Mem0 initialization status
4. **Verify Environment**: Ensure test DB is on port 5456
5. **Mock for CI/CD**: Use MockMemory class when Azure keys unavailable