# Humansa V2 Implementation Architecture

## Overview

Humansa V2 is a multi-agent medical AI system with integrated memory capabilities using Mem0. This document provides a complete view from abstract architecture to concrete implementation details.

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Abstract System Design](#abstract-system-design)
3. [User ID Tracking](#user-id-tracking)
4. [Orchestrator Pattern](#orchestrator-pattern)
5. [Component Flow](#component-flow)
6. [Agent System](#agent-system)
7. [Memory Integration](#memory-integration)
8. [API Endpoints](#api-endpoints)
9. [Implementation Details](#implementation-details)

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Applications"
        WEB[Web App]
        MOB[Mobile App]
        API[API Client]
    end
    
    subgraph "ML Server (Port 5001)"
        MAIN[main.py<br/>Entry Point]
        
        subgraph "Humansa V2 System"
            BP[humansa_v2_bp<br/>Blueprint]
            ORCH[HumansaOrchestrator<br/>Workflow Engine]
            MEM[Mem0MemoryManagerAdapter]
            CTX[ContextManager]
        end
        
        subgraph "Agent Pool"
            GA[GeneralMedicalAgent]
            DA[DiagnosisAgent]
            MA[MedicationAgent]
            EA[EmergencyTriageAgent]
            AA[AppointmentAgent]
        end
        
        subgraph "Memory Layer"
            M0[Mem0Manager<br/>Singleton]
            M0DB[(PostgreSQL<br/>+ pgvector)]
        end
    end
    
    WEB --> MAIN
    MOB --> MAIN
    API --> MAIN
    
    MAIN --> BP
    BP --> ORCH
    ORCH --> MEM
    ORCH --> CTX
    ORCH --> GA
    ORCH --> DA
    ORCH --> MA
    ORCH --> EA
    ORCH --> AA
    
    MEM --> M0
    M0 --> M0DB
    
    style MAIN fill:#9f9,stroke:#333,stroke-width:2px
    style ORCH fill:#f9f,stroke:#333,stroke-width:2px
    style M0 fill:#bbf,stroke:#333,stroke-width:2px
```

## Abstract System Design

### Conceptual Overview

```mermaid
graph TB
    subgraph "External Interfaces"
        USER[User<br/>Query Input]
        KNOW[Medical<br/>Knowledge Base]
        HIST[Historical<br/>Patient Data]
    end
    
    subgraph "Humansa V2 Core"
        subgraph "Intelligence Layer"
            INTEL[Orchestrator<br/>Intelligence Engine]
            POOL[Expert Agent Pool]
            LEARN[Learning & Memory]
        end
        
        subgraph "Processing Pipeline"
            UNDER[Understanding<br/>Context & Intent]
            PLAN[Planning<br/>Agent Selection]
            EXEC[Execution<br/>Multi-Agent Work]
            EVAL[Evaluation<br/>Completeness Check]
            SYNTH[Synthesis<br/>Response Generation]
        end
    end
    
    USER -->|Natural Language| INTEL
    INTEL --> UNDER
    UNDER --> PLAN
    PLAN --> EXEC
    EXEC --> EVAL
    EVAL -->|Incomplete| PLAN
    EVAL -->|Complete| SYNTH
    SYNTH -->|Medical Advice| USER
    
    POOL <--> EXEC
    LEARN <--> INTEL
    HIST --> LEARN
    KNOW --> POOL
    
    style INTEL fill:#f9f,stroke:#333,stroke-width:4px
    style EVAL fill:#ff9,stroke:#333,stroke-width:3px
```

### Information Flow Architecture

```mermaid
graph LR
    subgraph "Input Processing"
        Q[Query] --> QA[Query Analysis]
        C[Context] --> CE[Context Enrichment]
        H[History] --> HE[History Extraction]
    end
    
    subgraph "Decision Making"
        QA --> DM[Decision Module]
        CE --> DM
        HE --> DM
        DM --> AP[Agent Planning]
    end
    
    subgraph "Execution Pipeline"
        AP --> AE[Agent Execution]
        AE --> RC[Result Collection]
        RC --> EC{Evaluation}
    end
    
    subgraph "Iteration Loop"
        EC -->|Needs More| RE[Refine Requirements]
        RE --> AP
        EC -->|Sufficient| SY[Synthesis]
    end
    
    subgraph "Output Generation"
        SY --> RG[Response Generation]
        RG --> MU[Memory Update]
        MU --> OUT[Final Output]
    end
    
    style EC fill:#ff9,stroke:#333,stroke-width:2px
    style DM fill:#9f9,stroke:#333,stroke-width:2px
```

## User ID Tracking

### User ID Flow Through the System

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API Endpoint
    participant CTX as ContextManager
    participant MEM as Memory Adapter
    participant M0 as Mem0Manager
    participant DB as Database
    
    C->>API: POST /v2/humansa/chat<br/>{"user_id": "123"}
    API->>CTX: create_context(user_id="123")
    CTX->>CTX: Store user_id in UnifiedContext
    
    API->>MEM: get_user_context(user_id=123)
    MEM->>M0: get_memory_user_id(123)
    M0->>M0: Format: "humansa_prod_123"
    M0->>DB: Query memories for<br/>"humansa_prod_123"
    DB-->>M0: Return memories
    M0-->>MEM: Memories
    MEM-->>API: User context with memories
    
    Note over M0: User ID Format:<br/>{service}_{environment}_{user_id}<br/>Examples:<br/>- humansa_prod_123<br/>- humansa_test_10001
```

### User ID Components

1. **Client User ID**: Integer or string from client application
2. **Memory User ID**: Formatted string for Mem0 storage
3. **Format**: `{service}_{environment}_{user_id}`
   - `service`: Always "humansa" for medical system
   - `environment`: "prod", "test", or custom
   - `user_id`: Original user identifier

## Orchestrator Pattern

### Current Implementation (Simplified)

**Note**: The current implementation uses a basic single-pass workflow, not a true iterative orchestrator pattern.

```mermaid
graph TD
    subgraph "Current Reality"
        START[User Query] --> LOAD[Load Memory]
        LOAD --> KEYWORD[Keyword Matching<br/>diagnosis → DiagnosisAgent<br/>treatment → TreatmentAgent]
        KEYWORD --> EXEC[Execute Single Agent]
        EXEC --> RESP[Return Response]
    end
    
    style KEYWORD fill:#fcc,stroke:#333,stroke-width:2px
```

### Ideal Orchestrator Pattern

```mermaid
stateDiagram-v2
    [*] --> AnalyzeQuery: User Input
    
    AnalyzeQuery --> LoadContext: Parse Intent
    LoadContext --> PlanExecution: Memory Loaded
    PlanExecution --> SelectAgents: Strategy Ready
    
    SelectAgents --> ExecuteAgents: Agents Chosen
    ExecuteAgents --> CollectResults: Work Complete
    CollectResults --> EvaluateCompleteness: Results Ready
    
    state EvaluateCompleteness <<choice>>
    EvaluateCompleteness --> IdentifyGaps: Insufficient
    EvaluateCompleteness --> SynthesizeResponse: Sufficient
    
    IdentifyGaps --> SelectAgents: Need More Info
    
    SynthesizeResponse --> UpdateMemory: Final Answer
    UpdateMemory --> [*]: Complete
    
    note right of EvaluateCompleteness
        Key Decision:
        - Is information complete?
        - Any contradictions?
        - Need specialist input?
    end note
```

For detailed orchestrator analysis, see [HUMANSA_V2_ORCHESTRATOR_FLOW.md](./HUMANSA_V2_ORCHESTRATOR_FLOW.md)

## Component Flow

### Request Processing Flow

```mermaid
graph TD
    subgraph "1. Request Entry"
        REQ[HTTP Request<br/>with user_id] --> VAL{Validate<br/>Request}
        VAL -->|Valid| CTX1[Create Context]
        VAL -->|Invalid| ERR[Return Error]
    end
    
    subgraph "2. Context Building"
        CTX1 --> LOAD[Load User Memory]
        LOAD --> HIST[Add Conversation<br/>History]
        HIST --> CTX2[Complete Context]
    end
    
    subgraph "3. Agent Selection"
        CTX2 --> ROUTE[Route to Agents]
        ROUTE --> SCORE[Score Agent<br/>Relevance]
        SCORE --> SELECT[Select Agents]
    end
    
    subgraph "4. Agent Processing"
        SELECT --> PROC[Process Query<br/>with Agents]
        PROC --> SYNTH[Synthesize<br/>Responses]
    end
    
    subgraph "5. Memory Update"
        SYNTH --> UPDATE[Update Memory]
        UPDATE --> RESP[Return Response]
    end
    
    style REQ fill:#9f9,stroke:#333,stroke-width:2px
    style CTX2 fill:#bbf,stroke:#333,stroke-width:2px
    style RESP fill:#f9f,stroke:#333,stroke-width:2px
```

## Agent System

### Agent Architecture

```mermaid
classDiagram
    class BaseHumansaAgent {
        <<abstract>>
        +agent_id: str
        +description: str
        +llm: LLM
        +should_handle_query(query, context): float
        +process_query(query, context, stream): AsyncIterator
    }
    
    class GeneralMedicalAgent {
        +agent_id: "general_medical"
        +handle_general_queries()
    }
    
    class DiagnosisAgent {
        +agent_id: "diagnosis"
        +analyze_symptoms()
        +suggest_conditions()
    }
    
    class MedicationAgent {
        +agent_id: "medication"
        +check_interactions()
        +suggest_medications()
    }
    
    class EmergencyTriageAgent {
        +agent_id: "emergency_triage"
        +assess_urgency()
        +recommend_action()
    }
    
    class AppointmentAgent {
        +agent_id: "appointment"
        +search_slots()
        +book_appointment()
    }
    
    BaseHumansaAgent <|-- GeneralMedicalAgent
    BaseHumansaAgent <|-- DiagnosisAgent
    BaseHumansaAgent <|-- MedicationAgent
    BaseHumansaAgent <|-- EmergencyTriageAgent
    BaseHumansaAgent <|-- AppointmentAgent
```

### Agent Selection Logic

```mermaid
graph LR
    subgraph "Query Analysis"
        Q[User Query] --> KW[Keyword<br/>Extraction]
        Q --> CTX[Context<br/>Analysis]
    end
    
    subgraph "Agent Scoring"
        KW --> S1[Score Agent 1]
        KW --> S2[Score Agent 2]
        KW --> S3[Score Agent N]
        CTX --> S1
        CTX --> S2
        CTX --> S3
    end
    
    subgraph "Selection"
        S1 --> TH{Score > 0.5?}
        S2 --> TH
        S3 --> TH
        TH -->|Yes| SEL[Selected Agents]
        TH -->|No| DEF[Default: GeneralMedical]
    end
```

## Memory Integration

### Mem0 Integration Architecture

```mermaid
graph TB
    subgraph "Humansa V2 Layer"
        API[API Endpoints]
        ORCH[Orchestrator]
        OLDMEM[Original MemoryManager<br/>Interface]
    end
    
    subgraph "Adapter Layer"
        ADAPT[Mem0MemoryManagerAdapter]
        ADAPT -->|Implements| OLDMEM
    end
    
    subgraph "Mem0 Layer"
        M0MGR[Mem0Manager<br/>Singleton]
        M0[Mem0 Core]
        
        subgraph "Storage"
            PG[(PostgreSQL)]
            VEC[(pgvector)]
        end
    end
    
    ORCH --> OLDMEM
    OLDMEM --> ADAPT
    ADAPT --> M0MGR
    M0MGR --> M0
    M0 --> PG
    M0 --> VEC
    
    style ADAPT fill:#ffd,stroke:#333,stroke-width:2px
    style M0MGR fill:#bbf,stroke:#333,stroke-width:2px
```

### Memory Operations

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant A as Adapter
    participant M as Mem0Manager
    participant DB as Database
    
    rect rgb(240, 240, 240)
        Note over O,DB: Before Query Processing
        O->>A: get_patient_memory(user_id=123)
        A->>M: get_memory_user_id(123)
        M-->>A: "humansa_prod_123"
        A->>M: search all memories
        M->>DB: SELECT from memories
        DB-->>M: Raw memories
        M-->>A: Memories list
        A->>A: Categorize memories:<br/>- medications<br/>- allergies<br/>- preferences
        A-->>O: Structured patient memory
    end
    
    rect rgb(240, 255, 240)
        Note over O,DB: After Query Processing
        O->>A: update_conversation(user_id, query, response)
        A->>A: Format as messages
        A->>M: add_conversation(messages)
        M->>M: Extract key information
        M->>DB: INSERT into memories
        DB-->>M: Success
        M-->>A: True
        A-->>O: Update complete
    end
```

## API Endpoints

### Endpoint Hierarchy

```mermaid
graph TD
    subgraph "Main Routes"
        ROOT[/]
        V2[/v2/humansa]
    end
    
    subgraph "Chat Endpoints"
        CHAT[/chat<br/>Main conversation endpoint]
    end
    
    subgraph "Memory Endpoints"
        MEM[/memory]
        ADD[/add<br/>POST: Add conversation]
        SEARCH[/search<br/>POST: Search memories]
        CTX[/context/{user_id}<br/>GET: Get user context]
        STATUS[/status<br/>GET: Mem0 status]
        CLEAR[/clear/{user_id}<br/>DELETE: Clear memories]
    end
    
    subgraph "Other Endpoints"
        APPT[/appointment]
        APPTS[/search<br/>POST: Search slots]
        APPTB[/book<br/>POST: Book slot]
        
        PROF[/patient/profile<br/>GET/PUT: Profile ops]
        HIST[/conversation/history<br/>GET: Get history]
    end
    
    ROOT --> V2
    V2 --> CHAT
    V2 --> MEM
    MEM --> ADD
    MEM --> SEARCH
    MEM --> CTX
    MEM --> STATUS
    MEM --> CLEAR
    
    V2 --> APPT
    APPT --> APPTS
    APPT --> APPTB
    
    V2 --> PROF
    V2 --> HIST
```

## Implementation Details

### File Structure

```
src/
├── main.py                          # Entry point, registers blueprints
├── humansa/
│   ├── v2/
│   │   ├── __init__.py             # Exports blueprints
│   │   ├── api.py                  # V2 API endpoints
│   │   ├── context_manager.py      # UnifiedContext management
│   │   ├── memory/
│   │   │   ├── memory_manager.py   # Original interface
│   │   │   └── mem0_integration.py # Mem0 adapter
│   │   ├── workflows/
│   │   │   └── orchestrator.py     # Main workflow engine
│   │   └── agents/
│   │       ├── base_agent.py       # BaseHumansaAgent
│   │       ├── general_medical.py  # General queries
│   │       ├── diagnosis.py        # Symptom analysis
│   │       ├── medication.py       # Drug management
│   │       ├── emergency_triage.py # Urgency assessment
│   │       └── appointment.py      # Scheduling
│   └── memory/
│       ├── __init__.py
│       ├── mem0_manager.py         # Mem0 singleton
│       └── api.py                  # Memory API endpoints
```

### Initialization Sequence

```mermaid
sequenceDiagram
    participant M as main.py
    participant APP as Quart App
    participant V2 as V2 System
    participant MEM as Mem0Manager
    
    M->>APP: create_app()
    M->>APP: register_humansa_endpoints()
    
    APP->>APP: @app.before_serving
    APP->>MEM: Mem0Manager.get_instance()
    MEM->>MEM: Load config from env
    MEM->>MEM: Build Azure/OpenAI config
    
    APP->>MEM: initialize()
    MEM->>MEM: _ensure_schema_exists()
    MEM->>MEM: Create schema if needed
    MEM->>MEM: Memory.from_config()
    MEM-->>APP: Initialized ✓
    
    APP->>V2: initialize_v2_system(db_pool)
    V2->>V2: Check if Mem0 available
    alt Mem0 Available
        V2->>V2: Use Mem0MemoryManagerAdapter
    else Mem0 Not Available
        V2->>V2: Use basic MemoryManager
    end
    V2-->>APP: V2 System Ready
    
    M->>M: app.run(port=5001)
```

### Key Classes and Methods

1. **Mem0Manager** (`/src/humansa/memory/mem0_manager.py`)
   - `get_memory_user_id(user_id)`: Formats user ID for storage
   - `add_conversation(user_id, messages)`: Stores conversations
   - `search_memories(user_id, query)`: Semantic search
   - `get_user_context(user_id)`: Retrieves all user data

2. **Mem0MemoryManagerAdapter** (`/src/humansa/v2/memory/mem0_integration.py`)
   - Implements original MemoryManager interface
   - Bridges V2 system with Mem0
   - Categorizes memories into medical contexts

3. **HumansaOrchestrator** (`/src/humansa/v2/workflows/orchestrator.py`)
   - Routes queries to appropriate agents
   - Manages agent execution flow
   - Updates memory after processing

4. **UnifiedContext** (`/src/humansa/v2/context_manager.py`)
   - Carries user_id throughout workflow
   - Maintains conversation state
   - Holds agent results

## Testing

See [HUMANSA_V2_TESTING.md](./HUMANSA_V2_TESTING.md) for detailed test documentation.

## OpenAI Responses API Integration

### Overview

HUMANSA V2 now implements the OpenAI Responses API format, providing full transparency into the AI's reasoning process and tool usage. This ensures users can see exactly how the AI arrives at its conclusions.

### Response API Architecture

```mermaid
graph TB
    subgraph "Response API Layer"
        RBP[responses_bp<br/>Blueprint]
        RM[ResponseManager<br/>State Management]
        RF[ResponseFormatter<br/>Format Conversion]
        
        subgraph "Transparent Orchestrator"
            TO[TransparentOrchestrator]
            TC[ToolCallCapture<br/>Callback Handler]
        end
    end
    
    subgraph "Output Format"
        OA[Output Array]
        TEXT[Text Items<br/>Reasoning/Response]
        TOOL[Tool Use Items<br/>Invocations]
        RESULT[Tool Result Items<br/>Outputs]
    end
    
    RBP --> RM
    RBP --> TO
    TO --> TC
    TC --> RF
    RF --> OA
    OA --> TEXT
    OA --> TOOL
    OA --> RESULT
    
    style TO fill:#9f9,stroke:#333,stroke-width:2px
    style OA fill:#bbf,stroke:#333,stroke-width:2px
```

### Response Format

Each response contains a complete reasoning chain in the `output` array:

```json
{
  "id": "resp_abc123",
  "object": "response", 
  "created": 1234567890,
  "model": "gpt-4-turbo",
  "output": [
    {
      "type": "text",
      "text": "Let me search for neurology doctors..."
    },
    {
      "type": "tool_use",
      "tool_use": {
        "id": "tool_0",
        "name": "unified_search",
        "input": {"query": "神经内科医生"}
      }
    },
    {
      "type": "tool_result",
      "tool_result": {
        "tool_use_id": "tool_0",
        "output": "Found Dr. Zhang Wei..."
      }
    },
    {
      "type": "text",
      "text": "Based on my search, Dr. Zhang Wei is..."
    }
  ],
  "usage": {
    "total_tokens": 350,
    "reasoning_tokens": 150,
    "tool_tokens": 100
  }
}
```

### Event-Based Streaming

When streaming is enabled, responses use OpenAI's event format:

- `response.created` - Signals response start
- `response.output_item.delta` - Streams text chunks  
- `response.output_item.done` - Completes each output item
- `response.done` - Final event with complete response

### API Endpoints

```mermaid
graph TD
    subgraph "Response API Endpoints"
        CREATE[/v2/humansa/responses/create<br/>POST: Create response]
        STREAM[/v2/humansa/responses/stream<br/>POST: Stream response]
        GET[/v2/humansa/responses/{id}<br/>GET: Get response]
        TREE[/v2/humansa/responses/conversations/{id}/tree<br/>GET: Get conversation tree]
    end
    
    subgraph "Features"
        FORK[Response Forking<br/>Explore alternatives]
        CHAIN[Response Chaining<br/>Continue conversations]
        TRANS[Full Transparency<br/>Tool visibility]
    end
    
    CREATE --> FORK
    CREATE --> CHAIN
    CREATE --> TRANS
    STREAM --> TRANS
```

For detailed Response API documentation, see [RESPONSES_API_FORMAT.md](./RESPONSES_API_FORMAT.md)