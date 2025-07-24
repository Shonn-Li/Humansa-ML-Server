# Humansa v2 Multi-Agent System

## Overview

The Humansa v2 system is a sophisticated multi-agent medical consultation platform built with LlamaIndex. It provides intelligent medical assistance through specialized agents that work together to handle complex healthcare queries.

## Architecture

### Core Components

1. **Base Agent Framework** (`agents/base_agent.py`)
   - Abstract base class for all medical agents
   - Built on LlamaIndex ReActAgent
   - Provides tool management and streaming capabilities

2. **Specialized Agents**
   - **GeneralMedicalAgent**: Initial consultation and doctor search
   - **DiagnosisAgent**: Symptom analysis and diagnostic guidance
   - **MedicationAgent**: Medication information and interaction checking
   - **EmergencyTriageAgent**: Emergency assessment and triage
   - **AppointmentAgent**: Appointment booking and scheduling

3. **Orchestration System** (`workflows/orchestrator.py`)
   - LlamaIndex Workflow-based orchestration
   - Intelligent agent routing based on query analysis
   - Response synthesis from multiple agents
   - Event-driven architecture

4. **Memory Management** (`memory/memory_manager.py`)
   - Persistent patient profiles
   - Conversation history tracking
   - Medical history management
   - PostgreSQL-based storage

5. **Context Management** (`context_manager.py`)
   - Unified context passing between agents
   - Patient information aggregation
   - Conversation state management

## API Endpoints

### Chat Endpoints
- `POST /v2/humansa/chat` - Main multi-agent chat interface
  - Supports streaming responses
  - Automatic agent selection
  - Context-aware responses

### Appointment Management
- `POST /v2/humansa/appointment/search` - Search available slots
- `POST /v2/humansa/appointment/book` - Book appointments

### Patient Management
- `GET /v2/humansa/patient/profile` - Retrieve patient profile
- `PUT /v2/humansa/patient/profile` - Update patient profile
- `GET /v2/humansa/conversation/history` - Get conversation history

### System
- `GET /v2/humansa/health` - Health check endpoint

## Key Features

### 1. Multi-Agent Collaboration
Agents work together to provide comprehensive medical consultation:
- Router determines which agents should handle a query
- Multiple agents can process the same query in parallel
- Responses are synthesized into coherent advice

### 2. Persistent Memory
- Patient profiles stored in PostgreSQL
- Conversation history maintained across sessions
- Medical history and preferences tracked

### 3. Intelligent Routing
- Confidence-based agent selection
- Context-aware routing decisions
- Automatic escalation for emergencies

### 4. Streaming Support
- Real-time streaming responses
- Progress indicators for tool calls
- Citation support for medical information

## Database Schema

### humansa_patient_profile
```sql
- user_id (PRIMARY KEY)
- profile_data (JSONB)
- medical_history (JSONB)
- preferences (JSONB)
- created_at
- updated_at
```

### humansa_conversation_history
```sql
- id (SERIAL PRIMARY KEY)
- user_id (FOREIGN KEY)
- conversation_id
- role
- content
- metadata (JSONB)
- created_at
```

## Usage Example

```python
# Initialize the system
await initialize_v2_system(db_pool, openai_api_key)

# Chat request
response = await fetch('/v2/humansa/chat', {
    method: 'POST',
    body: JSON.stringify({
        user_id: 'user123',
        messages: [
            {role: 'user', content: 'I have severe headaches'}
        ],
        stream: true
    })
})
```

## Configuration

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key for LLM
- Database connection parameters

## Future Enhancements

1. **Medical Document Processing**
   - PDF report analysis
   - Lab result interpretation
   - Medical image OCR

2. **Advanced Agent Capabilities**
   - Prescription management agent
   - Insurance verification agent
   - Follow-up care agent

3. **Integration Features**
   - EHR system integration
   - Telemedicine platform connection
   - Payment processing

## Testing

Run the test suite:
```bash
python test_humansa_v2.py
```

This tests:
- All API endpoints
- Agent routing logic
- Memory persistence
- Streaming functionality