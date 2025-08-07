# Mem0 Architecture Overview - Global Memory Layer

## Executive Summary

Mem0 is a **global, shareable memory service** that can be used across multiple applications and services. It tracks memories by user ID, making it perfect for multi-service architectures where different services need to access the same user memories.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Global Mem0 Memory Layer"
        M[Mem0 Core]
        DB[(PostgreSQL + pgvector)]
        M --> DB
    end
    
    subgraph "Services Using Mem0"
        H[Humansa Medical AI<br/>user: humansa_prod_123]
        Y[YouWo Main App<br/>user: youwo_prod_123]
        F[Future Service<br/>user: future_prod_123]
    end
    
    subgraph "User Mapping"
        U1[User 123]
        U1 --> H
        U1 --> Y
        U1 --> F
    end
    
    H --> M
    Y --> M
    F --> M
    
    style M fill:#f9f,stroke:#333,stroke-width:4px
    style DB fill:#bbf,stroke:#333,stroke-width:2px
```

## User ID Strategy

```mermaid
graph LR
    subgraph "User ID Format"
        A[Service Prefix] --> B[Environment] --> C[User ID]
        
        A --> |humansa| D[humansa_prod_123]
        A --> |youwo| E[youwo_prod_123]
        A --> |chat| F[chat_prod_123]
    end
    
    subgraph "Same User, Different Contexts"
        U[User 123]
        U --> D
        U --> E
        U --> F
    end
    
    style U fill:#ffd,stroke:#333,stroke-width:2px
```

## Test Environment Architecture

```mermaid
graph TB
    subgraph "Test Environment Setup"
        TS[run_humansa_test_environment.sh]
        TS --> DC[Docker Compose<br/>Port 5456]
        TS --> SS[setup.sh]
        SS --> SM[setup_mem0.sh]
        
        subgraph "Database Setup"
            DC --> PG[(PostgreSQL Test DB)]
            SM --> SC[Create mem0_test schema]
            SM --> TD[Load Test Data<br/>Users: 10001, 10002, 10003]
        end
        
        subgraph "ML Server"
            ML[ML Server Start]
            ML --> MM[Mem0Manager.initialize]
            MM --> MT[Mem0 Creates Tables]
        end
        
        SS --> ML
        SC --> MT
    end
    
    style TS fill:#9f9,stroke:#333,stroke-width:2px
    style PG fill:#bbf,stroke:#333,stroke-width:2px
```

## Mem0 Initialization Flow

```mermaid
sequenceDiagram
    participant S as ML Server
    participant MM as Mem0Manager
    participant M as Mem0
    participant DB as PostgreSQL
    
    S->>MM: initialize()
    MM->>DB: CREATE SCHEMA IF NOT EXISTS
    MM->>DB: GRANT PRIVILEGES
    MM->>DB: CREATE EXTENSION vector
    MM->>M: Memory.from_config()
    M->>M: Initialize LLM provider
    M->>M: Initialize embedder
    M->>M: Initialize vector store
    Note over M,DB: Tables created on first use
    M-->>MM: Ready
    MM-->>S: Initialized ✓
```

## Memory Operations Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as ML Server API
    participant MM as Mem0Manager
    participant M as Mem0
    participant DB as Database
    
    C->>API: POST /v2/humansa/memory/add
    Note over C,API: user_id: 123<br/>messages: [...]
    
    API->>MM: add_conversation(123, messages)
    MM->>MM: get_memory_user_id(123)<br/>→ "humansa_prod_123"
    MM->>M: memory.add(messages, "humansa_prod_123")
    
    M->>M: Extract key information
    M->>M: Generate embeddings
    M->>DB: Store in memories table
    M->>DB: Store in embeddings table
    
    M-->>MM: Success
    MM-->>API: Success
    API-->>C: 200 OK
```

## Test Environment Detailed Flow

```mermaid
graph TB
    subgraph "1. Environment Setup"
        A[./run_humansa_test_environment.sh] --> B{Docker Running?}
        B -->|No| C[Start Docker]
        B -->|Yes| D[docker-compose up -d]
        D --> E[PostgreSQL on 5456]
    end
    
    subgraph "2. Database Preparation"
        E --> F[Wait for DB Ready]
        F --> G[Run setup_humansa_test_db.sql]
        G --> H[Run setup_mem0_test.sql]
        H --> I[Create Test Users<br/>10001, 10002, 10003]
    end
    
    subgraph "3. Mem0 Setup"
        I --> J[setup_mem0.sh]
        J --> K[CREATE SCHEMA mem0_test]
        J --> L[pip install mem0ai]
        K --> M[Schema Ready]
        L --> N[Package Installed]
    end
    
    subgraph "4. ML Server Start"
        M --> O[Start ML Server]
        N --> O
        O --> P[Mem0Manager.initialize()]
        P --> Q{First Run?}
        Q -->|Yes| R[Mem0 Creates Tables]
        Q -->|No| S[Use Existing Tables]
    end
    
    subgraph "5. Run Tests"
        R --> T[Run 10 Test Cases]
        S --> T
        T --> U[Test Results]
    end
    
    style A fill:#9f9,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style U fill:#f9f,stroke:#333,stroke-width:2px
```

## Test Cases Overview

```mermaid
graph TD
    subgraph "Memory Creation Tests 1-7"
        T1[Test 1: Basic Storage<br/>User 10001 - Clean slate]
        T2[Test 2: Medical Context<br/>User 10002 - Diabetes]
        T3[Test 3: Memory Updates<br/>Medication changes]
        T4[Test 4: Multi-Conversation<br/>Symptom progression]
        T5[Test 5: Preferences<br/>Appointment times]
        T6[Test 6: Complex History<br/>Multiple conditions]
        T7[Test 7: Context Retrieval<br/>Semantic search]
    end
    
    subgraph "Persistence Tests 8-10"
        T8[Test 8: Verify Persistence<br/>Check all users]
        T9[Test 9: Cross-Session Recall<br/>Specific info retrieval]
        T10[Test 10: Patient Summary<br/>Comprehensive profile]
    end
    
    T1 --> T8
    T2 --> T8
    T3 --> T8
    T4 --> T9
    T5 --> T9
    T6 --> T10
    T7 --> T10
    
    style T1 fill:#e7f3ff,stroke:#333
    style T8 fill:#fff3e7,stroke:#333
    style T10 fill:#f3e7ff,stroke:#333
```

## Test Data Flow

```mermaid
graph LR
    subgraph "Test Users"
        U1[User 10001<br/>No History]
        U2[User 10002<br/>Diabetes Patient]
        U3[User 10003<br/>Complex Case]
    end
    
    subgraph "Test Conversations"
        C1[Basic Preferences]
        C2[Medical History]
        C3[Symptom Evolution]
        C4[Appointments]
    end
    
    subgraph "Memory Storage"
        M1[mem0_test_memories]
        M2[mem0_test_embeddings]
    end
    
    U1 --> C1 --> M1
    U2 --> C2 --> M1
    U3 --> C3 --> M1
    U3 --> C4 --> M1
    
    M1 --> M2
    
    style U1 fill:#e7f3ff,stroke:#333
    style U2 fill:#fff3e7,stroke:#333
    style U3 fill:#f3e7ff,stroke:#333
```

## Production vs Test Environment

```mermaid
graph TB
    subgraph "Production Environment"
        P1[ML Server Starts]
        P2[Check Environment: prod]
        P3[Schema: mem0_humansa_prod]
        P4[Auto-create on first use]
        P5[Real Azure OpenAI]
        
        P1 --> P2 --> P3 --> P4 --> P5
    end
    
    subgraph "Test Environment"
        T1[run_humansa_test_environment.sh]
        T2[Check Environment: test]
        T3[Schema: mem0_test]
        T4[Pre-created with test data]
        T5[Mock or Test API Keys]
        
        T1 --> T2 --> T3 --> T4 --> T5
    end
    
    style P1 fill:#9f9,stroke:#333
    style T1 fill:#99f,stroke:#333
```

## Global Usage Pattern

```mermaid
graph TB
    subgraph "Current State"
        H1[Humansa Service]
        M1[Mem0 Global Layer]
        H1 -->|humansa_prod_123| M1
    end
    
    subgraph "Future State"
        H2[Humansa Service]
        Y2[YouWo Chat Service]
        N2[Notes Service]
        A2[Analytics Service]
        M2[Mem0 Global Layer]
        
        H2 -->|humansa_prod_123| M2
        Y2 -->|chat_prod_123| M2
        N2 -->|notes_prod_123| M2
        A2 -->|analytics_prod_123| M2
    end
    
    subgraph "Cross-Service Benefits"
        B1[Shared User Context]
        B2[Unified Memory Management]
        B3[Service-Specific Namespacing]
        B4[Global User Understanding]
    end
    
    M2 --> B1
    M2 --> B2
    M2 --> B3
    M2 --> B4
    
    style M1 fill:#f9f,stroke:#333,stroke-width:2px
    style M2 fill:#f9f,stroke:#333,stroke-width:2px
```

## Key Concepts

### 1. **Global Memory Service**
- One Mem0 instance serves all services
- Each service uses prefixed user IDs
- Memories are isolated by prefix but shareable if needed

### 2. **User ID Namespacing**
```
Format: {service}_{environment}_{user_id}

Examples:
- humansa_prod_123     (Humansa production)
- humansa_test_10001   (Humansa test)
- youwo_prod_123       (YouWo main app)
- chat_prod_123        (Chat service)
```

### 3. **Test Environment Isolation**
- Separate schema: `mem0_test`
- Test users: 10001, 10002, 10003
- Pre-loaded test scenarios
- No impact on production data

### 4. **Scalability**
- Add new services without modifying Mem0
- Each service manages its own namespace
- Optional cross-service memory sharing

## Benefits of This Architecture

1. **Service Independence**: Each service can evolve independently
2. **Memory Persistence**: User memories persist across sessions
3. **Cross-Service Intelligence**: Future capability to share insights
4. **Easy Testing**: Isolated test environment with realistic data
5. **Zero Migration Overhead**: Mem0 self-manages schema

## Example: Multi-Service User Journey

```mermaid
sequenceDiagram
    participant U as User 123
    participant H as Humansa
    participant Y as YouWo Chat
    participant M as Mem0
    
    U->>H: "I have diabetes"
    H->>M: Store: humansa_prod_123
    Note over M: "User has diabetes"
    
    U->>Y: "Set reminder for medication"
    Y->>M: Query: youwo_prod_123
    Note over Y: No medical context
    
    U->>Y: "Set health reminder"
    Y->>M: Store: youwo_prod_123
    Note over M: "User wants health reminders"
    
    Note over M: Future: Cross-service<br/>memory sharing possible
```

This architecture ensures that Mem0 serves as a true **global memory layer** that can grow with your platform while maintaining service isolation and user privacy.