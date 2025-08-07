# Humansa AI Medical Assistant Documentation

## Overview

Humansa is a multi-agent medical AI system with integrated memory capabilities powered by Mem0. The system provides personalized, context-aware medical consultations through intelligent agent orchestration.

## Architecture

### V1 (Enhanced with Multi-Agent Orchestrator)
- **Endpoint**: `/v1-humansa/chat/completions`
- **Features**: Tool-calling interface with multi-agent analysis
- **Agent**: HumansaAgent with integrated multi-agent orchestrator
- **Memory**: Optional Mem0 integration

### V2 (LlamaIndex Orchestrator Pattern)
- **Endpoint**: `/v2/humansa/chat`
- **Features**: Pattern 2 orchestrator with sub-agents as tools
- **Agents**: 5 specialized medical agents coordinated by orchestrator
- **Memory**: Full Mem0 integration with context persistence

### V2 Responses API (OpenAI Format)
- **Endpoints**: `/v2/humansa/responses/*`
- **Features**: Full reasoning chain transparency with tool visibility
- **Format**: OpenAI Responses API with output array
- **Streaming**: Event-based format (response.created, output_item.delta, etc.)
- **Capabilities**: Response forking, chaining, and conversation trees

## Test Environment

⚠️ **CRITICAL**: All Humansa tests use a COMPLETELY ISOLATED test environment. See [HUMANSA_TEST_ENVIRONMENT.md](./HUMANSA_TEST_ENVIRONMENT.md) for details.

Key points:
- ML Server: Port **6001** (NOT 5001!)
- PostgreSQL: Port **5454** (isolated Docker container)
- Database: **test4** with password **12931**
- Completely independent from production

## Core Documentation

### 📘 [HUMANSA_V2_IMPLEMENTATION.md](./HUMANSA_V2_IMPLEMENTATION.md)
Complete implementation guide covering:
- High-level architecture with visual diagrams
- Abstract system design and information flow
- User ID tracking and flow
- Component interactions from abstract to concrete
- Agent system design and selection logic
- Memory integration with Mem0
- API endpoint specifications
- Detailed file structure and initialization sequence

### 📗 [HUMANSA_V2_TESTING.md](./HUMANSA_V2_TESTING.md)
Comprehensive testing documentation including:
- Two core test suites overview
- Memory persistence testing (10 test cases)
- API integration testing
- Test data structure and flow
- Running tests in different modes
- Common issues and solutions

### 📙 [HUMANSA_V2_ORCHESTRATOR_FLOW.md](./HUMANSA_V2_ORCHESTRATOR_FLOW.md)
Detailed orchestrator pattern analysis:
- Current implementation reality (simple routing)
- Ideal orchestrator pattern with iterative refinement
- High-level conceptual architecture
- Comparison of current vs ideal implementation
- Recommendations for true orchestrator pattern

### 📕 [RESPONSES_API_FORMAT.md](./RESPONSES_API_FORMAT.md)
OpenAI Responses API implementation:
- Output array structure with reasoning chain
- Tool use and tool result transparency
- Event-based streaming format
- Response forking and chaining
- API endpoint specifications

## Quick Start

### Test Environment
```bash
# V1 Testing (20 test cases)
./run_humansa_test_environment.sh

# V2 Testing (30 test cases including Mem0)
./run_humansa_test_environment_v2.sh
```

### Manual Testing
```bash
# Test V1 endpoint
curl -X POST http://localhost:6001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你是谁？"}],
    "stream": false
  }'

# Test V2 endpoint with memory
curl -X POST http://localhost:6001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [{"role": "user", "content": "I have diabetes"}],
    "stream": false
  }'

# Test V2 Responses API (with tool transparency)
curl -X POST http://localhost:6001/v2/humansa/responses/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "input": "找一个神经内科医生",
    "user_id": "test_user_123"
  }'
```

## Key Features

### Current Implementation ✅
- **Multi-Agent System**: 5 specialized medical agents + transparent orchestrator
- **Memory Layer**: Mem0 integration for persistent user context
- **Smart Orchestration**: Automatic agent selection based on query
- **User ID Tracking**: Namespaced format for multi-service support
- **API Endpoints**: RESTful API with streaming support
- **Response API**: OpenAI format with full reasoning transparency
- **Tool Visibility**: Complete tool call and result exposure
- **Consolidated Tools**: 7 core functions with dynamic loading
- **Response Management**: Stateful conversations with forking support
- **Test Coverage**: Comprehensive test suites with mock support

### Architecture Highlights
- **LlamaIndex Workflows**: Event-driven agent orchestration
- **PostgreSQL + pgvector**: Semantic memory storage
- **Adapter Pattern**: Seamless Mem0 integration
- **Singleton Pattern**: Efficient memory manager
- **Context Management**: Unified context throughout workflow

## System Components

```
Humansa V2
├── API Layer (Quart blueprints)
│   ├── V2 Chat API
│   └── V2 Responses API
├── Orchestrators
│   ├── HumansaOrchestratorAgent
│   ├── HumansaOrchestratorAgentEnhanced
│   ├── HumansaOrchestratorAgentConsolidated
│   └── HumansaOrchestratorAgentTransparent
├── Response Layer
│   ├── ResponseManager (state management)
│   ├── ResponseFormatter (format conversion)
│   └── ConversationManager (context window)
├── Agent Pool
│   ├── GeneralMedicalAgent
│   ├── DiagnosisAgent
│   ├── MedicationAgent
│   ├── EmergencyTriageAgent
│   └── AppointmentAgent
├── Memory System
│   ├── Mem0Manager (Singleton)
│   └── Mem0MemoryManagerAdapter
├── Tools
│   ├── Consolidated Tools (7 core functions)
│   └── Dynamic Tool Loader
└── Context Manager
```

## User ID Strategy

Format: `{service}_{environment}_{user_id}`

Examples:
- `humansa_prod_123` - Production user 123
- `humansa_test_10001` - Test user 10001

This enables future cross-service memory sharing while maintaining isolation.

## Additional Resources

### Research & Design
- `research/` - Memory system comparisons and evaluations
- `implementations/` - Implementation fixes and improvements
- `guides/` - Operational guides and test results

### External APIs
- `external-apis/` - HIS AI integration documentation

### Test Results
- `test-results/` - Historical test execution results

## Testing

### Identity Test Cases (Core 20)
1. Basic identity queries in Chinese/English
2. Company background and services
3. Emergency response protocols
4. Appointment booking flows
5. Medical consultation capabilities
6. And more...

### Mem0 Test Cases (Additional 10)
1. Memory persistence across sessions
2. Context recall in responses
3. Medical history tracking
4. Preference learning
5. Cross-agent memory sharing
6. And more...

## Environment Variables

Required:
- `OPENAI_API_KEY`
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

Optional:
- `MEM0_API_KEY` (for cloud Mem0)
- `ENVIRONMENT` (test/production)

## Version History

- **V1**: Original tool-calling agent with multi-agent enhancement
- **V2**: LlamaIndex orchestrator pattern with full Mem0 integration
- **V2 Responses API**: OpenAI-compatible format with transparent tool usage and response management