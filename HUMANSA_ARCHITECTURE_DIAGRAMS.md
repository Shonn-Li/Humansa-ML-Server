# HUMANSA V2 Architecture Diagrams

## Level 1: Simple Overview
```mermaid
graph LR
    User[User] --> API[API] --> Agent[AI Agent] --> Response[Response]
```

## Level 2: Basic Flow
```mermaid
graph TD
    User[User Query] --> API[/v2/humansa/chat]
    API --> Orchestrator[Orchestrator]
    Orchestrator --> Agent[Medical Agent]
    Agent --> Database[(Database)]
    Database --> Agent
    Agent --> Orchestrator
    Orchestrator --> User
```

## Level 3: Sub-Agent Architecture
```mermaid
graph TD
    User[User: "我想预约心内科医生"] --> API[API Endpoint]
    API --> Orchestrator[Main Orchestrator]
    
    Orchestrator --> Product[Product Agent]
    Orchestrator --> Appointment[Appointment Agent]
    Orchestrator --> Clinical[Clinical Agent]
    Orchestrator --> Medication[Medication Agent]
    Orchestrator --> General[General Agent]
    
    Appointment --> DB[(PostgreSQL)]
    DB --> Appointment
    Appointment --> Orchestrator
    Orchestrator --> Response[Response Agent]
    Response --> User
```

## Level 4: Appointment Agent Tools
```mermaid
graph TD
    subgraph "Appointment Agent"
        Query[User Query] --> Agent[Appointment Agent]
        Agent --> Tools{Select Tool}
        
        Tools --> T1[search_slots]
        Tools --> T2[present_options]
        Tools --> T3[request_approval]
        Tools --> T4[process_approval]
        Tools --> T5[finalize_booking]
        Tools --> T6[reserve_slot]
        Tools --> T7[confirm_appointment]
        Tools --> T8[appointment_prep]
        
        T1 --> DB[(Database)]
        DB --> Result[Result]
    end
```

## Level 5: Complete Request Flow
```mermaid
flowchart TD
    User[User Input] --> API[API /v2/humansa/chat]
    API --> Auth[Authentication]
    Auth --> Context[Context Manager]
    Context --> Memory[Mem0 Memory]
    
    Memory --> Orchestrator[Sub-Agent Orchestrator]
    
    Orchestrator --> Router{Route Decision}
    Router -->|Product Query| ProductAgent[Product Agent]
    Router -->|Appointment| AppointmentAgent[Appointment Agent]
    Router -->|Clinical| ClinicalAgent[Clinical Agent]
    Router -->|Medication| MedicationAgent[Medication Agent]
    Router -->|General| GeneralAgent[General Agent]
    
    AppointmentAgent --> AgentWrapper[Agent Tool Wrapper]
    AgentWrapper --> BaseAgent[Base Humansa Agent]
    BaseAgent --> ReactAgent[ReAct Agent]
    ReactAgent --> Tools[8 Appointment Tools]
    Tools --> Database[(PostgreSQL DB)]
    
    Database --> Tools
    Tools --> ReactAgent
    ReactAgent --> BaseAgent
    BaseAgent --> AgentWrapper
    AgentWrapper --> Orchestrator
    
    Orchestrator --> ResponseAgent[Response Agent]
    ResponseAgent --> Format{Response Format}
    Format -->|Stream| SSE[Server-Sent Events]
    Format -->|Non-Stream| JSON[JSON Response]
    
    SSE --> User
    JSON --> User
```

## Level 6: Database Schema
```mermaid
erDiagram
    DOCTOR ||--o{ APPOINTMENT_SLOT : has
    CLINIC ||--o{ APPOINTMENT_SLOT : hosts
    APPOINTMENT_SLOT ||--o| APPOINTMENT : booked_as
    PATIENT ||--o{ APPOINTMENT : makes
    
    DOCTOR {
        string doctor_code PK
        string name
        string specialty
        decimal registration_fee
        string clinic_code FK
    }
    
    CLINIC {
        string clinic_code PK
        string name
        string address
        string phone
    }
    
    APPOINTMENT_SLOT {
        bigint slot_id PK
        string doctor_id FK
        string clinic_id FK
        date date
        time time
        string consultation_type
        decimal consultation_fee
        boolean is_available
        int duration_minutes
    }
    
    APPOINTMENT {
        bigint appointment_id PK
        bigint schedule_id FK
        string patient_name
        string patient_phone
        time appointment_time
        string status
        timestamp created_at
    }
    
    PATIENT {
        string patient_id PK
        string name
        string phone
        string email
    }
```

## Level 7: Tool Calling Sequence
```mermaid
sequenceDiagram
    participant U as User
    participant API as API Endpoint
    participant O as Orchestrator
    participant W as Agent Wrapper
    participant A as Appointment Agent
    participant T as Tool (search_slots)
    participant DB as Database
    
    U->>API: POST /v2/humansa/chat<br/>"我想预约心内科医生"
    API->>O: process_query()
    O->>O: Analyze query type
    O->>W: appointment_booking_agent(query)
    W->>A: process_query()
    A->>A: update_prompts(system_prompt)
    A->>T: search_slots(specialty="心内科")
    T->>DB: SELECT * FROM slots WHERE specialty LIKE '%心内科%'
    DB->>T: 20 appointment slots
    T->>A: List of available slots
    A->>A: present_options(slots)
    A->>W: Formatted response
    W->>O: Agent response
    O->>API: Final response
    API->>U: JSON with appointment options
```

## Level 8: Memory Integration
```mermaid
graph TD
    subgraph "Memory System"
        User[User: debug_test_001] --> API[API Request]
        API --> MemMgr[Mem0 Manager]
        
        MemMgr --> Load[Load User Context]
        Load --> VectorDB[(Vector Database)]
        VectorDB --> Context[User Context]
        
        Context --> Orchestrator[Orchestrator]
        Orchestrator --> Response[Generate Response]
        
        Response --> Store[Store Conversation]
        Store --> Embed[Create Embeddings]
        Embed --> VectorDB
        
        subgraph "Mem0 Tables"
            VectorDB --> Memories[mem0_humansa_prod_memories]
            Memories --> |Contains| UserMem[User Memories]
            Memories --> |Contains| ConvHist[Conversation History]
            Memories --> |Contains| Embeddings[Vector Embeddings]
        end
    end
```

## Level 9: Agent Tool Wrapper Detail
```mermaid
flowchart TD
    subgraph "Agent Tool Wrapper System"
        OrchestratorCall[Orchestrator Calls Tool] --> Wrapper[AgentToolWrapper]
        
        Wrapper --> AsyncCall[Async Agent Call]
        AsyncCall --> Agent[Sub-Agent<br/>e.g., AppointmentAgent]
        
        Agent --> ProcessQuery[process_query<br/>Async Generator]
        ProcessQuery --> Chunks{Chunk Types}
        
        Chunks -->|type='content'| ContentChunk[Collect Content]
        Chunks -->|type='error'| ErrorChunk[Handle Error]
        Chunks -->|'response' field| ResponseChunk[Direct Response]
        Chunks -->|string| StringChunk[Raw String]
        
        ContentChunk --> Accumulate[Accumulate Chunks]
        ResponseChunk --> Accumulate
        StringChunk --> Accumulate
        
        Accumulate --> FinalResponse[Join All Chunks]
        FinalResponse --> SyncReturn[Return Sync Result]
        SyncReturn --> OrchestratorCall
        
        ErrorChunk --> ErrorReturn[Return Error Message]
        ErrorReturn --> OrchestratorCall
    end
```

## Level 10: Complete System Architecture
```mermaid
graph TB
    subgraph "Client Layer"
        Web[Web Client]
        Mobile[Mobile App]
        API_Client[API Client]
    end
    
    subgraph "API Gateway"
        Gateway[Quart Server<br/>Port 6001/5001]
        Gateway --> Routes{Routes}
        Routes --> Chat[/v2/humansa/chat]
        Routes --> Appt[/v2/humansa/appointment/*]
        Routes --> Memory[/v2/humansa/memory/*]
        Routes --> Admin[/admin/*]
    end
    
    subgraph "Business Logic Layer"
        subgraph "Orchestration"
            MainOrch[Sub-Agent Orchestrator]
            ConsolOrch[Consolidated Orchestrator]
            TransOrch[Transparent Orchestrator]
        end
        
        subgraph "Sub-Agents"
            ProdAgent[Product Agent<br/>10 tools]
            ApptAgent[Appointment Agent<br/>8 tools]
            ClinAgent[Clinical Agent<br/>12 tools]
            MedAgent[Medication Agent<br/>6 tools]
            GenAgent[General Agent<br/>8 tools]
        end
        
        subgraph "Support Services"
            ContextMgr[Context Manager]
            MemoryMgr[Memory Manager]
            ResponseAgent[Response Agent]
            BrandProc[Brand Processor]
        end
    end
    
    subgraph "Data Layer"
        subgraph "PostgreSQL Databases"
            TestDB[(Test DB<br/>Port 5454)]
            ProdDB[(Prod DB<br/>Port 5432)]
            MemDB[(Memory DB)]
        end
        
        subgraph "External Services"
            Azure[Azure OpenAI<br/>GPT-4.1]
            OpenAI[OpenAI API<br/>GPT-4o-mini]
            WebSearch[Web Search API]
        end
    end
    
    subgraph "Infrastructure"
        Docker[Docker Containers]
        Logs[Logging System]
        Monitor[Monitoring]
        Config[Configuration<br/>DIGIT=2<br/>SUBAGENT=true]
    end
    
    %% Connections
    Web --> Gateway
    Mobile --> Gateway
    API_Client --> Gateway
    
    Chat --> MainOrch
    Appt --> ApptAgent
    Memory --> MemoryMgr
    
    MainOrch --> ProdAgent
    MainOrch --> ApptAgent
    MainOrch --> ClinAgent
    MainOrch --> MedAgent
    MainOrch --> GenAgent
    
    ApptAgent --> TestDB
    MemoryMgr --> MemDB
    
    MainOrch --> Azure
    MemoryMgr --> OpenAI
    
    ResponseAgent --> BrandProc
    BrandProc --> Gateway
```

## Level 11: Appointment Booking Flow State Machine
```mermaid
stateDiagram-v2
    [*] --> UserQuery: User asks about appointment
    
    UserQuery --> RouteToAgent: Orchestrator routes
    RouteToAgent --> SearchSlots: Agent calls search_slots
    
    SearchSlots --> DatabaseQuery: Query PostgreSQL
    DatabaseQuery --> SlotsFound: Return available slots
    DatabaseQuery --> NoSlots: No slots available
    
    SlotsFound --> PresentOptions: Format options
    NoSlots --> SuggestAlternative: Suggest other times
    
    PresentOptions --> UserSelection: User picks option
    UserSelection --> RequestApproval: Confirm booking details
    
    RequestApproval --> UserApproves: User confirms
    RequestApproval --> UserRejects: User cancels
    
    UserApproves --> FinalizeBooking: Create appointment
    UserRejects --> SearchAgain: Back to search
    
    FinalizeBooking --> BookingSuccess: Update database
    FinalizeBooking --> BookingFailed: Error occurred
    
    BookingSuccess --> SendConfirmation: Send details
    BookingFailed --> RetryBooking: Try again
    
    SendConfirmation --> [*]: Complete
    SuggestAlternative --> SearchAgain
    SearchAgain --> SearchSlots
    RetryBooking --> FinalizeBooking
```

## Level 12: Dynamic Data Population
```mermaid
graph TD
    subgraph "Data Population Process"
        Start[Environment Startup] --> Check{Check Database}
        Check -->|Empty| Populate[Run populate_realistic_appointment_data.sql]
        Check -->|Has Data| Skip[Skip Population]
        
        Populate --> Generate[Generate Dynamic Data]
        
        subgraph "Dynamic Generation"
            Generate --> Dates[Generate Dates<br/>CURRENT_DATE to +14 days]
            Generate --> Times[Generate Time Slots<br/>09:00 to 17:30]
            Generate --> Doctors[Assign to 7 Doctors]
            Generate --> Availability[Set Availability<br/>80% weekday, 60% Saturday, 30% Sunday]
        end
        
        Dates --> Insert[INSERT INTO appointment_slots]
        Times --> Insert
        Doctors --> Insert
        Availability --> Insert
        
        Insert --> Update[Update Special Cases]
        Update --> Cardio[Ensure 心内科 availability]
        Update --> Pediatric[Ensure 儿科 availability]
        Update --> Internal[Ensure 内科 availability]
        
        Cardio --> Sample[Create Sample Bookings]
        Pediatric --> Sample
        Internal --> Sample
        
        Sample --> Ready[Database Ready]
        Skip --> Ready
        Ready --> TestEnv[Test Environment Ready]
    end
```

## Level 13: Error Handling and Retry Logic
```mermaid
flowchart TD
    subgraph "Error Handling Flow"
        Request[User Request] --> Try{Try Operation}
        
        Try -->|Success| Process[Process Normally]
        Try -->|Error| Catch[Catch Error]
        
        Catch --> ErrorType{Error Type}
        
        ErrorType -->|Network| Retry1[Retry with Backoff]
        ErrorType -->|Database| Retry2[Retry Connection]
        ErrorType -->|API Limit| Wait[Wait and Retry]
        ErrorType -->|Logic Error| Log[Log and Return Error]
        
        Retry1 --> Count1{Retry Count}
        Retry2 --> Count2{Retry Count}
        Wait --> Count3{Wait Time}
        
        Count1 -->|< 3| Try
        Count1 -->|>= 3| Fallback1[Use Fallback Data]
        
        Count2 -->|< 5| Reconnect[Reconnect DB]
        Count2 -->|>= 5| Fallback2[Use Mock Data]
        
        Count3 -->|< 60s| Try
        Count3 -->|>= 60s| Fallback3[Return Cached]
        
        Reconnect --> Try
        
        Process --> Success[Return Success]
        Fallback1 --> Degraded[Return Degraded Response]
        Fallback2 --> Degraded
        Fallback3 --> Degraded
        Log --> UserError[Return User Error]
        
        Success --> End[Complete]
        Degraded --> End
        UserError --> End
    end
```

## Level 14: Performance Optimization
```mermaid
graph TD
    subgraph "Performance Layers"
        subgraph "Caching"
            Request[Request] --> Cache{Check Cache}
            Cache -->|Hit| CachedResp[Return Cached]
            Cache -->|Miss| Process[Process Request]
            Process --> Store[Store in Cache]
            Store --> Response[Return Response]
        end
        
        subgraph "Database Optimization"
            Query[SQL Query] --> Index{Use Indexes}
            Index --> Prepared[Prepared Statements]
            Prepared --> Pool[Connection Pool]
            Pool --> Batch[Batch Operations]
        end
        
        subgraph "Async Processing"
            Sync[Sync Request] --> Queue[Task Queue]
            Queue --> Workers[Async Workers]
            Workers --> Parallel[Parallel Processing]
            Parallel --> Aggregate[Aggregate Results]
        end
        
        subgraph "Resource Management"
            Memory[Memory Manager] --> GC[Garbage Collection]
            CPU[CPU Manager] --> Threads[Thread Pool]
            Network[Network Manager] --> Connections[Connection Reuse]
        end
    end
```

## Level 15: Security Architecture
```mermaid
graph TD
    subgraph "Security Layers"
        subgraph "Authentication"
            Client[Client Request] --> Auth{Authenticate}
            Auth -->|Valid| Token[Generate Token]
            Auth -->|Invalid| Reject[Reject 401]
            Token --> Validate[Validate Token]
        end
        
        subgraph "Authorization"
            Validate --> Authz{Authorize}
            Authz -->|Allowed| Proceed[Process Request]
            Authz -->|Denied| Forbid[Return 403]
        end
        
        subgraph "Data Protection"
            Proceed --> Encrypt[Encrypt Sensitive Data]
            Encrypt --> Sanitize[Sanitize Input]
            Sanitize --> Validate2[Validate Data]
            Validate2 --> Process[Process Safely]
        end
        
        subgraph "Audit & Monitoring"
            Process --> Log[Log Activity]
            Log --> Monitor[Monitor Anomalies]
            Monitor --> Alert[Alert on Issues]
            Alert --> Block[Block Threats]
        end
    end
```