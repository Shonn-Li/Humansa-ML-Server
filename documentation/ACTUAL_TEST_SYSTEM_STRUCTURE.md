# Actual Test System Structure

## ✅ Correct Test Environment Configuration

### Test Server
- **Port**: `6001` (NOT 5001!)
- **Startup**: `python3 -m src.main --port 6001`
- **Script**: `./run_HUMANSA_test_environment_v2_enhanced.sh`

### Test Database
- **Container**: `youwoai_test_db`
- **Port**: `5454`
- **Password**: `12931`
- **Database**: `test4`

### Environment Variables
```bash
export ENVIRONMENT=test
export ML_SERVER_PORT=6001
export DB_PORT=5454
export DB_PASSWORD=12931
export DB_NAME=test4
export HUMANSA_ENHANCED_LOGGING=true
export HUMANSA_USE_PATTERN2=true  # For Pattern 2 orchestrator
```

---

## 📁 Active Directory Structure

```
YouWoAI-ML-Server-1/
├── src/
│   ├── main.py                    # Main server entry (uses --port 6001)
│   ├── humansa/
│   │   ├── v2/
│   │   │   ├── api_responses.py   # Response API endpoints
│   │   │   ├── orchestrator_pattern2_fixed.py  # ✅ ACTIVE orchestrator
│   │   │   ├── forms/             # New form system
│   │   │   │   ├── form_tools.py
│   │   │   │   ├── form_service.py
│   │   │   │   └── models.py
│   │   │   └── workflows/         # (mostly deprecated)
│   │   └── tools/
│   │       └── humansa_tools.py   # Tool definitions
│
├── test_environment/
│   └── unified_test_config.py     # ✅ SINGLE SOURCE OF TRUTH
│
├── documentation/
│   ├── COMPREHENSIVE_TEST_SYSTEM_OVERVIEW.md
│   ├── MODULAR_TEST_FRAMEWORK_QUICKSTART.md
│   └── humansa/
│       ├── V2_CURRENT_STATE.md    # Updated with correct ports
│       └── agents/
│           └── appointment_agent.md
│
├── archive/old_tests/             # Archived legacy tests
│
└── Test Entry Scripts:
    ├── run_HUMANSA_test_environment_v2_enhanced.sh  # ✅ Main test runner
    ├── run_humansa_comprehensive_tests.py           # ✅ Modular framework
    └── humansa_test_framework.py                    # ✅ Core framework
```

---

## 🚀 Current Active Components

### 1. **Pattern 2 Orchestrator** (Currently Active)
- File: `src/humansa/v2/orchestrator_pattern2_fixed.py`
- Type: LlamaIndex FunctionAgent
- Features: Form tools, streaming reasoning
- Enable: `export HUMANSA_USE_PATTERN2=true`

### 2. **Form System** (New)
- Directory: `src/humansa/v2/forms/`
- Components:
  - Form models and service
  - Form filling agent
  - Form tools for Pattern 2
  - Mock booking system

### 3. **Test Framework** (Modular)
- Core: `humansa_test_framework.py`
- Features:
  - Parallel execution
  - Standardized test cases
  - Comprehensive reporting
  - YAML test definitions

---

## 🧹 Cleanup Results

### Deleted (40 files):
- Debug/temporary test files
- Duplicate orchestrators
- Old workflow tests
- Redundant form tests
- Deprecated subagent tests

### Archived (5 files):
- `test_HUMANSA_v2_70_cases_multiturn.py`
- `test_HUMANSA_v2_comprehensive_enhanced.py`
- `test_long_conversation_suite.py`
- `test_humansa_v2_with_reasoning.py`
- `test_reasoning_stream_comparison.py`

### To Consolidate (Future):
- Appointment tests → `test_appointment_forms_modular.py`
- Product tests → Create `test_product_modular.py`
- Pattern 2 tests → Keep as reference

---

## 📊 Test Organization

### Active Test Files:
```
Tests/
├── Modular Framework Tests:
│   ├── test_appointment_forms_modular.py    # ✅ Use this
│   ├── appointment_test_executor.py         # Enhanced executor
│   └── test_parallel_execution_demo.py      # Demo parallel execution
│
├── Pattern 2 Tests:
│   ├── test_pattern2_orchestrator.py
│   ├── test_pattern2_form_complete.py
│   └── test_pattern2_memory.py
│
├── Integration Tests:
│   ├── test_appointment_approval_flow.py
│   ├── test_appointment_realistic.py
│   └── test_form_appointment_flow.py
│
└── test_cases/                               # YAML test definitions
    ├── appointment/
    ├── medical_consultation/
    ├── emergency/
    └── multi_turn/
```

---

## 🔧 How to Run Tests

### 1. Start Test Environment
```bash
# Correct way:
./run_HUMANSA_test_environment_v2_enhanced.sh

# What it does:
- Sets ML_SERVER_PORT=6001
- Starts server with: python3 -m src.main --port 6001
- Enables Pattern 2 if HUMANSA_USE_PATTERN2=true
```

### 2. Run Modular Tests
```bash
# Run comprehensive test suite
python run_humansa_comprehensive_tests.py

# Run specific test module
python test_appointment_forms_modular.py

# Run with monitoring
python run_humansa_comprehensive_tests.py --monitor
```

### 3. API Endpoints
- **V2 Responses**: `http://localhost:6001/v2/humansa/responses/create`
- **V1 Humansa**: `http://localhost:6001/v1-humansa/chat/completions`
- **Health Check**: `http://localhost:6001/health`

---

## ⚠️ Common Mistakes to Avoid

1. **Wrong Port**: Don't use port 5001 - that's dev/production
2. **Wrong Startup**: Don't use `python -m src.main` without `--port 6001`
3. **Wrong Config**: Always use `test_environment/unified_test_config.py`
4. **Wrong Orchestrator**: We have 9, but only use `orchestrator_pattern2_fixed.py`

---

## 📈 Next Steps

1. **Complete Form System Integration**
   - Fix form submission flow
   - Add form persistence to database
   - Implement real appointment booking

2. **Standardize All Tests**
   - Convert remaining tests to modular framework
   - Create 1000 standardized test cases
   - Implement YAML-based test definitions

3. **Clean Architecture**
   - Remove remaining duplicate orchestrators
   - Consolidate similar test files
   - Document all active components