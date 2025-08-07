# Humansa V2 Current State Documentation

## Overview
This document describes the current state of the Humansa V2 implementation with OpenAI Responses API integration, including the transparent orchestrator and enhanced tool visibility.

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
│  • Port: 6001 (ML Server Test Instance)                     │
│  • DB Port: 5454 (PostgreSQL Test DB)                       │
│  • DB Name: test4                                           │
│  • Environment: test                                        │
│  • Enhanced Logging: true                                   │
│  • Pattern 2: true (when enabled)                           │
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
│  python3 -m src.main --port 6001                            │
│  • Initializes Humansa V2 system                           │
│  • Loads V1 and V2 endpoints                               │
│  • Initializes memory managers                              │
│  • Pattern 2 orchestrator (when HUMANSA_USE_PATTERN2=true) │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   V2 System Components                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Response API Layer                      │   │
│  │  • ResponseManager (state management)               │   │
│  │  • ResponseFormatter (format conversion)            │   │
│  │  • TransparentOrchestrator (tool visibility)        │   │
│  │  • Event-based streaming support                    │   │
│  │  • Endpoints:                                       │   │
│  │    - /v2/humansa/responses/create                  │   │
│  │    - /v2/humansa/responses/stream                  │   │
│  │    - /v2/humansa/responses/<id>                    │   │
│  │    - /v2/humansa/responses/conversations/<id>/tree │   │
│  └─────────────────────────────────────────────────────┘   │
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
│  │              Orchestrator Agents                     │   │
│  │  • HumansaOrchestratorAgentTransparent             │   │
│  │    - Captures all tool calls and reasoning         │   │
│  │    - Returns full output array                     │   │
│  │  • HumansaOrchestratorAgentConsolidated            │   │
│  │    - 7 core tools with dynamic loading             │   │
│  │  • Uses Azure OpenAI (GPT-4.1)                     │   │
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
│  2. Send response request: POST /v2/humansa/responses/create│
│     • model: "gpt-4-turbo"                                 │
│     • input: "user query"                                  │
│     • user_id: "test_user_X"                               │
│     • previous_response_id: "resp_xyz" (if continuing)     │
│  3. Process response with full output array:               │
│     • Text items (reasoning/response)                      │
│     • Tool use items (invocations)                         │
│     • Tool result items (outputs)                          │
│  4. For streaming: POST /v2/humansa/responses/stream       │
│     • Events: response.created, output_item.delta, etc.    │
│  5. Log results with tool transparency                     │
└─────────────────────────────────────────────────────────────┘
```

## Current Features

### 1. OpenAI Responses API Integration ✅
- **Status**: ✅ Implemented
- **Features**:
  - Full reasoning chain visibility in output array
  - Tool use and tool result items exposed
  - Event-based streaming format
  - Response forking and chaining support
  - Token usage breakdown (reasoning vs tool tokens)

### 2. Transparent Orchestrator ✅
- **Status**: ✅ Working
- **Components**:
  - HumansaOrchestratorAgentTransparent with ToolCallCapture
  - Captures all LlamaIndex agent reasoning steps
  - Converts to proper OpenAI format

### 3. Consolidated Tools ✅
- **Status**: ✅ Implemented
- **Tools**: 7 core functions with dynamic loading
  - unified_search, appointment_manager, medical_advisor
  - product_recommender, information_lookup, emergency_handler
  - conversation_memory

### 4. Response Management ✅
- **Status**: ✅ Working
- **Features**:
  - Stateful conversation management
  - Response chaining with previous_response_id
  - Conversation forking for parallel exploration
  - Context compression for long conversations

## Response API Format

Each response includes:

```json
{
  "id": "resp_abc123",
  "output": [
    {"type": "text", "text": "Let me search..."},
    {"type": "tool_use", "tool_use": {...}},
    {"type": "tool_result", "tool_result": {...}},
    {"type": "text", "text": "Based on results..."}
  ],
  "usage": {
    "total_tokens": 350,
    "reasoning_tokens": 150,
    "tool_tokens": 100
  }
}
```

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
ML_SERVER_PORT=6001  # Test environment always uses 6001
HUMANSA_ENHANCED_LOGGING=true
HUMANSA_USE_PATTERN2=true  # Enable Pattern 2 orchestrator (optional)
```

## Key Files

### Response API Layer
1. **Response API**: `src/humansa/v2/api_responses.py`
2. **Response Manager**: `src/humansa/v2/response_manager.py`
3. **Response Formatter**: `src/humansa/v2/response_formatter.py`
4. **Transparent Orchestrator**: `src/humansa/v2/orchestrator_agent_transparent.py`
5. **Consolidated Tools**: `src/humansa/tools/consolidated_tools.py`

### Core V2 System
1. **Test Script**: `run_humansa_v2_test_40_cases_enhanced.sh`
2. **V2 API**: `src/humansa/v2/api.py`
3. **Memory Manager**: `src/humansa/memory/mem0_manager.py`
4. **Conversation Manager**: `src/humansa/v2/conversation_manager.py`
5. **Context Compressor**: `src/humansa/v2/context_compressor.py`

## How to Run

1. Ensure PostgreSQL test database is running on port 5454
2. Run: `./run_humansa_v2_test_40_cases_enhanced.sh`
3. Results saved to: `test_results_v2_40cases_enhanced/`

## Next Steps

1. Update test scripts to use Response API endpoints
2. Migrate existing tests to validate output array format
3. Add tests for response forking scenarios
4. Implement multi-turn conversation tests with Response API
5. Document streaming event format for client implementations
6. Performance optimization for tool-heavy queries