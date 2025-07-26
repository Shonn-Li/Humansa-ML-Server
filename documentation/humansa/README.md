# Humansa V2 Documentation

## Overview

Humansa V2 is a multi-agent medical AI system with integrated memory capabilities powered by Mem0. This system provides personalized, context-aware medical consultations through intelligent agent orchestration.

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

## Quick Start

### 1. Start the System
```bash
# Start ML server (includes Humansa V2)
python -m src.main

# Or with test environment
./run_humansa_test_environment.sh
```

### 2. Test Memory Integration
```bash
# Run complete test suite with environment
./run_humansa_test_with_mem0.sh

# Or run tests individually
python test_mem0_humansa_integration.py
python test_mem0_v2_integration.py
```

### 3. Use the API
```bash
# Chat with memory context
curl -X POST http://localhost:5001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [{"role": "user", "content": "I have diabetes"}],
    "stream": false
  }'
```

## Key Features

### Current Implementation ✅
- **Multi-Agent System**: 5 specialized medical agents
- **Memory Layer**: Mem0 integration for persistent user context
- **Smart Orchestration**: Automatic agent selection based on query
- **User ID Tracking**: Namespaced format for multi-service support
- **API Endpoints**: RESTful API with streaming support
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
├── Orchestrator (Workflow engine)
├── Agent Pool
│   ├── GeneralMedicalAgent
│   ├── DiagnosisAgent
│   ├── MedicationAgent
│   ├── EmergencyTriageAgent
│   └── AppointmentAgent
├── Memory System
│   ├── Mem0Manager (Singleton)
│   └── Mem0MemoryManagerAdapter
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

## Contributing

When updating Humansa V2:
1. Update the implementation in `/src/humansa/v2/`
2. Document changes in `HUMANSA_V2_IMPLEMENTATION.md`
3. Add/update tests and document in `HUMANSA_V2_TESTING.md`
4. Keep this README focused on the two core documents

## Version

**Current**: V2 with Mem0 Integration
- Multi-agent medical consultation
- Persistent memory with Mem0
- Context-aware responses
- Comprehensive test coverage