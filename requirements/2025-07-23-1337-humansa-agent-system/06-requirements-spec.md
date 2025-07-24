# Requirements Specification - Humansa Agent System v2

## Executive Summary

This document specifies the requirements for building Humansa Agent System v2, a multi-agent medical consultation platform with appointment booking, advanced RAG processing, and persistent user memory management. The system will use LlamaIndex's AgentWorkflow pattern for orchestration while maintaining compatibility with existing infrastructure.

## Problem Statement

The current Humansa system lacks:
1. Persistent user memory across medical consultations
2. Advanced multi-agent orchestration for complex medical workflows
3. Sophisticated document routing for diverse medical content types
4. Proper test infrastructure for iterative development
5. Comprehensive appointment booking workflow with real integration capabilities

## Solution Overview

Build a multi-agent medical system featuring:
- **LlamaIndex AgentWorkflow** orchestration with dynamic agent spawning
- **Persistent patient profiles** with medical history tracking
- **Advanced RAG processor** using LlamaIndex routers for medical documents
- **Mock API infrastructure** for appointment booking testing
- **Unified context window** management across all conversation types

## Functional Requirements

### 1. User Memory System
Based on Answer Q1 (YES - Persist conversation history):
- **FR1.1**: Store patient conversation history in existing `conversation_v1` table
- **FR1.2**: Create new `humansa_patient_profile` table for medical-specific data:
  - Medical history
  - Allergies
  - Medications
  - Preferences
  - Previous consultations
- **FR1.3**: Link patient profiles to user_id from conversation_v1
- **FR1.4**: Auto-populate context from patient history in new conversations

### 2. Appointment Booking System
Based on Answer Q2 (YES - Real-time availability with mock APIs):
- **FR2.1**: Create mock appointment API endpoints mimicking production structure
- **FR2.2**: Generate realistic test data for:
  - Doctor schedules
  - Appointment slots
  - Clinic availability
- **FR2.3**: Implement booking workflow:
  - Check availability
  - Reserve slot
  - Confirm booking
  - Handle cancellations/rescheduling
- **FR2.4**: Use existing `humansa_schedule` table schema for consistency

### 3. Multi-Document RAG Processor
Based on Answer Q3 (YES - Support multiple document types):
- **FR3.1**: Create new RAG processor (copy/modify existing) supporting:
  - PDFs (medical reports, lab results)
  - Unstructured doctor notes
  - Medical images with OCR
  - Structured lab data (JSON/XML)
- **FR3.2**: Implement LlamaIndex document routers for type-specific processing
- **FR3.3**: Remove note-related RAG functionality (Humansa-specific)
- **FR3.4**: Add medical relevance scoring and filtering

### 4. Dynamic Agent Orchestration
Based on Answer Q4 (YES - Dynamic agent spawning):
- **FR4.1**: Implement LlamaIndex AgentWorkflow as orchestrator
- **FR4.2**: Create specialized medical agents:
  - DiagnosisAgent
  - MedicationAgent
  - AppointmentAgent
  - ProductRecommendationAgent
  - EmergencyTriageAgent
- **FR4.3**: Dynamic agent instantiation based on context
- **FR4.4**: Agent handoff mechanisms with state preservation
- **FR4.5**: Parallel agent execution for independent tasks

### 5. Unified Context Management
Based on Answer Q5 (NO - Single context window):
- **FR5.1**: Implement unified context window for all conversation types
- **FR5.2**: Context size management with sliding window
- **FR5.3**: Priority-based context retention (medical info > product info)
- **FR5.4**: Context serialization for persistence between sessions

## Technical Requirements

### 1. Infrastructure Setup
Based on Expert Answer Q5 (Separate PostgreSQL instance):
- **TR1.1**: Deploy separate PostgreSQL instance on port 5003
- **TR1.2**: Initialize with schema migration system
- **TR1.3**: Create test data seeding scripts
- **TR1.4**: Implement connection pooling and failover

### 2. Agent Implementation
Based on Expert Answer Q1 (Use ReActAgent with multi-agent workflow):
- **TR2.1**: Extend existing ReActAgent pattern for all agents
- **TR2.2**: Implement AgentWorkflow orchestration layer
- **TR2.3**: Create agent communication protocols
- **TR2.4**: Add comprehensive logging and observability
- **TR2.5**: Support streaming responses throughout

### 3. Database Design
Based on Expert Answers Q2 & Q3 (Use existing schemas):
- **TR3.1**: Extend `conversation_v1` with medical context fields
- **TR3.2**: Create `humansa_patient_profile` table:
  ```sql
  CREATE TABLE humansa_patient_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    medical_history JSONB,
    allergies TEXT[],
    current_medications JSONB,
    preferences JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  ```
- **TR3.3**: Use existing Humansa tables for mock data
- **TR3.4**: Add indexes for performance optimization

### 4. RAG System Enhancement
Based on Expert Answer Q4 (Copy and modify RAGProcessor):
- **TR4.1**: Fork existing RAGProcessor as `MedicalRAGProcessor`
- **TR4.2**: Integrate LlamaIndex document parsers:
  - PDFParser for medical reports
  - UnstructuredParser for doctor notes
  - ImageParser with OCR for scans
- **TR4.3**: Implement medical-specific embeddings
- **TR4.4**: Add document type routing logic

### 5. API Design
- **TR5.1**: Create `/v2/humansa/` endpoints:
  - `/v2/humansa/chat` - Main orchestrator endpoint
  - `/v2/humansa/appointments/*` - Booking endpoints
  - `/v2/humansa/patient/*` - Patient profile endpoints
  - `/v2/humansa/documents/*` - Document upload/processing
- **TR5.2**: Maintain OpenAI-compatible response format
- **TR5.3**: Support both streaming and non-streaming modes
- **TR5.4**: Implement comprehensive error handling

## Implementation Plan

### Phase 1: Test Environment Setup (Week 1)
1. Set up PostgreSQL instance on port 5003
2. Create database schemas and migrations
3. Implement mock data generation scripts
4. Create basic API endpoints for testing

### Phase 2: Multi-Agent Framework (Week 2)
1. Implement AgentWorkflow orchestrator
2. Create base medical agent classes
3. Build agent communication system
4. Add streaming and observability

### Phase 3: RAG Enhancement (Week 3)
1. Fork and modify RAGProcessor
2. Integrate LlamaIndex document parsers
3. Implement medical relevance scoring
4. Test with sample medical documents

### Phase 4: Integration & Testing (Week 4)
1. Connect all components
2. Implement end-to-end workflows
3. Performance optimization
4. Comprehensive testing suite

## File Structure

```
YouWoAI-ML-Server/
├── src/
│   ├── agents/
│   │   ├── humansa_v2/
│   │   │   ├── orchestrator.py         # AgentWorkflow implementation
│   │   │   ├── diagnosis_agent.py      # Medical diagnosis agent
│   │   │   ├── appointment_agent.py    # Booking specialist
│   │   │   ├── medication_agent.py     # Drug information
│   │   │   └── triage_agent.py        # Emergency assessment
│   │   └── humansa_agentic_agent.py   # Existing (reference)
│   ├── core/
│   │   └── rag/
│   │       ├── medical_processor.py    # New RAG processor
│   │       └── document_routers.py     # LlamaIndex routers
│   ├── database/
│   │   ├── humansa_v2_tables.py       # New table definitions
│   │   └── mock_data_generator.py      # Test data creation
│   └── api/
│       └── v2/
│           └── humansa_endpoints.py    # V2 API endpoints
└── test/
    └── humansa_v2/
        ├── test_server.py              # Port 5003 test server
        ├── test_orchestrator.py        # Multi-agent tests
        └── fixtures/                   # Mock medical documents
```

## Acceptance Criteria

### 1. User Memory
- [ ] Patient profiles persist across sessions
- [ ] Historical context automatically loaded
- [ ] Medical history affects agent responses
- [ ] Privacy controls implemented

### 2. Appointment System
- [ ] Mock APIs return realistic data
- [ ] Full booking workflow functional
- [ ] Availability checking accurate
- [ ] Rescheduling/cancellation works

### 3. Document Processing
- [ ] All medical document types parsed
- [ ] Relevant information extracted
- [ ] Router correctly categorizes documents
- [ ] Performance meets <2s requirement

### 4. Multi-Agent System
- [ ] Orchestrator correctly routes requests
- [ ] Agents spawn dynamically as needed
- [ ] State preserved across handoffs
- [ ] Streaming works end-to-end

### 5. Integration
- [ ] All components work together
- [ ] Error handling comprehensive
- [ ] Logging provides full observability
- [ ] Performance meets requirements

## Success Metrics

1. **Response Time**: <2 seconds for non-streaming responses
2. **Document Processing**: 95%+ accuracy on medical information extraction
3. **Agent Routing**: 90%+ correct agent selection by orchestrator
4. **Availability**: 99.9% uptime for test environment
5. **Memory Usage**: <500MB per concurrent user session

## Risk Mitigation

1. **Complexity Risk**: Start with minimal agent set, expand iteratively
2. **Performance Risk**: Implement caching and connection pooling early
3. **Integration Risk**: Use existing patterns from current system
4. **Data Privacy Risk**: Implement encryption and access controls from start

## Next Steps

1. Review and approve requirements specification
2. Set up development environment
3. Create project timeline with milestones
4. Begin Phase 1 implementation
5. Schedule weekly progress reviews