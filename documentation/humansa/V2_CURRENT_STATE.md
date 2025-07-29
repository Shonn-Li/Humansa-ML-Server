# Humansa V2 Current State Documentation

## Overview
This document describes the current state of the Humansa V2 implementation and test environment as of the latest fixes.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Script Entry                         │
│         run_humansa_v2_test_40_cases_enhanced.sh            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                Test Environment Setup                        │
│  • Port: 5001 (ML Server)                                   │
│  • DB Port: 5454 (PostgreSQL Test DB)                       │
│  • DB Name: test4                                           │
│  • Environment: test                                        │
│  • Enhanced Logging: true                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               Database Initialization                        │
│  Runs SQL scripts in order:                                 │
│  • 01_extensions.sql                                        │
│  • 02_create_tables.sql                                     │
│  • 03_test_data.sql                                         │
│  • 04_embeddings.sql                                        │
│  • 05_test_conversations.sql                                │
│  • 06_humansa_test_data.sql                                 │
│  • 07_humansa_his_alignment.sql                            │
│  • 08_appointment_management.sql                            │
│  • create_missing_tables.sql                                │
│  • fix_schema_and_add_test_data.sql                        │
│  • humansa_test_doctors.sql                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  ML Server Startup                           │
│  python -m src.main                                          │
│  • Initializes Humansa V2 system                           │
│  • Loads V1 and V2 endpoints                               │
│  • Initializes memory managers                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   V2 System Components                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Memory Manager                         │   │
│  │  • Mem0Manager (if available)                       │   │
│  │  • Falls back to MemoryManager                      │   │
│  │  • Endpoints:                                       │   │
│  │    - /v2/humansa/memory/context/<user_id>          │   │
│  │    - /v2/humansa/memory/add                         │   │
│  │    - /v2/humansa/memory/search                      │   │
│  │    - /v2/humansa/memory/clear/<user_id>            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Orchestrator Agent                      │   │
│  │  • HumansaOrchestratorAgent                        │   │
│  │  • Uses Azure OpenAI (GPT-4.1)                     │   │
│  │  • Pattern 2: Sub-agents as tools                  │   │
│  │  • Real database tools enabled                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Tools                               │   │
│  │  From V1 HumansaAgenticToolManager:                 │   │
│  │  • find_doctor_info                                 │   │
│  │  • find_doctor_availability                         │   │
│  │  • search_clinics                                   │   │
│  │  • search_services                                  │   │
│  │  • get_pricing                                      │   │
│  │  • prepare_booking_confirmation                     │   │
│  │  • book_appointment_confirmation                    │   │
│  │  • book_appointment                                 │   │
│  │  • place_call                                       │   │
│  │  • recommend_product                                │   │
│  │  • search_web                                       │   │
│  │  Plus appointment management tools:                 │   │
│  │  • collect_appointment_info                         │   │
│  │  • confirm_appointment_booking                      │   │
│  │  • get_appointment_history                          │   │
│  │  • reschedule_appointment                           │   │
│  │  • cancel_appointment                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Test Flow                                 │
│                                                              │
│  For each test case:                                         │
│  1. Check memory context: GET /v2/humansa/memory/context    │
│  2. Send chat request: POST /v2/humansa/chat               │
│     • user_id: "test_user_X"                               │
│     • messages: [{"role": "user", "content": "..."}]       │
│     • stream: true                                          │
│     • debug: true                                           │
│  3. Process streaming response                              │
│  4. Log results                                             │
└─────────────────────────────────────────────────────────────┘
```

## Current Issues

### 1. Memory Context (FIXED)
- **Previous Issue**: Memory endpoints expected integer user_ids but tests use strings
- **Fix Applied**: Changed routes from `<int:user_id>` to `<user_id>`
- **Status**: ✅ Fixed, needs server restart

### 2. Database Schema
- **Status**: ✅ Working
- **Tables**: 
  - Core tables: humansa_clinic, humansa_patient, humansa_medical_service
  - Duplicate tables exist (humansa_clinic vs humansa_clinics)
  - Test data loaded with doctors, clinics, schedules

### 3. V2 Orchestrator
- **Status**: ⚠️ Partially Working
- **Issue**: Sometimes returns None, causing streaming errors
- **Uses**: Real database tools from V1 implementation

### 4. Test Cases Status
Based on the output shown:
- Test #1 (你好): ✅ Working - Basic greeting
- Test #2 (你是谁？): Needs identity system prompt
- Test #12 (Appointment): Needs multi-step conversation support

## Database Tables

```sql
-- Core tables in test4 database:
humansa_appointment      -- Appointment records
humansa_appointments     -- Duplicate?
humansa_clinic          -- Clinic information
humansa_clinics         -- Duplicate?
humansa_department      -- Medical departments
humansa_doctor          -- Doctor information (created by our migration)
humansa_schedule        -- Doctor schedules (created by our migration)
humansa_appointment_history -- Appointment history (created by our migration)
humansa_medical_service -- Medical services
humansa_patient         -- Patient records
humansa_service         -- Services
```

## Test Environment Variables

```bash
ENVIRONMENT=test
DB_HOST=localhost
DB_PORT=5454
DB_USER=postgres
DB_PASSWORD=12931
DB_NAME=test4
ML_SERVER_PORT=5001
HUMANSA_ENHANCED_LOGGING=true
```

## Key Files

1. **Test Script**: `run_humansa_v2_test_40_cases_enhanced.sh`
2. **V2 API**: `src/humansa/v2/api.py`
3. **V2 Orchestrator**: `src/humansa/v2/orchestrator_agent.py`
4. **Memory Manager**: `src/humansa/memory/mem0_manager.py`
5. **V1 Tools**: `src/humansa/tools/humansa_tools.py`
6. **Appointment Tools**: `src/humansa/tools/appointment_management_tools.py`

## How to Run

1. Ensure PostgreSQL test database is running on port 5454
2. Run: `./run_humansa_v2_test_40_cases_enhanced.sh`
3. Results saved to: `test_results_v2_40cases_enhanced/`

## Next Steps

1. Apply memory endpoint fixes (restart required)
2. Add Humansa identity to system prompt
3. Ensure V2 orchestrator initialization is stable
4. Clean up duplicate tables
5. Test appointment flow (Test #12)