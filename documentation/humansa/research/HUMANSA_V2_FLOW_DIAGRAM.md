# Humansa AI Agent V2 - Flow Diagram

## System Architecture

```mermaid
graph TD
    %% Client Request
    Client[Client Request] --> API["/v1-humansa/chat/completions<br/>API Endpoint"]
    
    %% Main Components
    API --> HCE[HumansaChatEndpoint]
    HCE --> |"1. Build System Prompt"| SP[System Prompt Builder]
    SP --> |"React Format + Context"| HAA[HumansaAgenticAgent]
    
    %% Agent Processing
    HAA --> |"2. Initialize"| RA[ReActAgent<br/>(LlamaIndex)]
    RA --> |"3. Process Query"| TP[Thought Process]
    
    %% Tool Management
    HAA --> |"Filter Tools"| TF[Tool Filter]
    TF --> |"Remove search_web"| TM[HumansaAgenticToolManager]
    
    %% Tool Execution Loop
    TP --> |"4. Decide Action"| TA{Tool Action?}
    TA -->|Yes| TE[Tool Execution]
    TA -->|No| FR[Final Response]
    
    %% Tool Types
    TE --> T1[find_doctor_info]
    TE --> T2[find_doctor_availability]
    TE --> T3[book_appointment]
    TE --> T4[place_call]
    TE --> T5[get_pricing]
    TE --> T6[search_clinics]
    
    %% Database Layer
    T1 --> DB[(PostgreSQL<br/>Database)]
    T2 --> DB
    T3 --> DB
    T4 --> ES[External Service]
    T5 --> DB
    T6 --> DB
    
    %% Database Tables
    DB --> DT1[humansa_doctor]
    DB --> DT2[humansa_clinic]
    DB --> DT3[humansa_schedule]
    DB --> DT4[humansa_medical_service]
    
    %% Tool Response Flow
    DB --> |"Query Result"| TO[Tool Output]
    ES --> |"Action Result"| TO
    TO --> |"5. Observation"| TP
    
    %% Response Generation
    FR --> |"6. Format Response"| RG[Response Generator]
    RG --> |"JSON Response"| Client
    
    %% Trace & Metadata
    TP -.->|"Agent Trace"| AT[Agent Trace]
    TE -.->|"Tool Calls"| TC[Tool Call Log]
    AT --> RG
    TC --> RG
    
    %% Environment Config
    ENV[.env Configuration] -.-> |"DB_USER<br/>DB_NAME<br/>DB_PORT"| DB
    ENV -.-> |"OPENAI_API_KEY"| RA
    
    %% Error Handling
    DB -->|"Connection Error"| EH[Error Handler]
    TE -->|"Tool Error"| EH
    EH --> RG

    %% Styling
    classDef endpoint fill:#f9f,stroke:#333,stroke-width:2px
    classDef agent fill:#bbf,stroke:#333,stroke-width:2px
    classDef tool fill:#bfb,stroke:#333,stroke-width:2px
    classDef database fill:#fbb,stroke:#333,stroke-width:2px
    classDef config fill:#ccc,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5
    
    class API,HCE endpoint
    class HAA,RA,TP agent
    class T1,T2,T3,T4,T5,T6,TM tool
    class DB,DT1,DT2,DT3,DT4 database
    class ENV config
```

## Key Components

### 1. **Entry Point**
- `/v1-humansa/chat/completions` - Main API endpoint
- Handles OpenAI-compatible chat requests

### 2. **HumansaChatEndpoint**
- Builds system prompt with medical context
- Manages conversation flow
- Handles streaming/non-streaming responses

### 3. **HumansaAgenticAgent**
- Wraps LlamaIndex ReActAgent
- Filters out `search_web` tool to prevent external searches
- Manages tool execution and reasoning

### 4. **Tool Manager**
- `HumansaAgenticToolManager` - Provides medical-specific tools
- Each tool connects to PostgreSQL database
- Returns structured data for agent reasoning

### 5. **Database Layer**
- PostgreSQL with medical data tables:
  - `humansa_doctor` - Doctor information
  - `humansa_clinic` - Clinic details
  - `humansa_schedule` - Availability slots
  - `humansa_medical_service` - Services and pricing

### 6. **ReAct Pattern Flow**
1. **Thought**: Agent analyzes user query
2. **Action**: Decides which tool to use
3. **Action Input**: Prepares tool parameters
4. **Observation**: Receives tool output
5. **Loop**: Repeats until answer found
6. **Answer**: Final response to user

### 7. **Configuration**
- Environment variables from `.env`:
  - `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
  - `DB_PORT` - Default 5432
  - `OPENAI_API_KEY` - LLM access

### 8. **Response Format**
```json
{
  "choices": [{
    "message": {
      "content": "Agent response with answer"
    }
  }],
  "agent_trace": "Full ReAct reasoning trace",
  "tool_calls_observed": ["list of tools used"]
}
```

## Recent Fixes
- ✅ Fixed `DB_USER` vs `DB_USERNAME` mismatch
- ✅ Changed from test DB (5454) to main DB (5432)
- ✅ Added test data for all tables
- ✅ Tools now return real data
- ✅ 100% test pass rate achieved