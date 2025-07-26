# Humansa V2 Orchestrator Flow Documentation

## Executive Summary

The Humansa V2 system uses a workflow orchestrator pattern, but the current implementation is **simplified** and does not implement a true iterative orchestrator pattern. This document shows:
1. The current actual flow (basic single-pass)
2. What a proper orchestrator pattern should be
3. High-level conceptual architecture

## High-Level Conceptual Architecture

### Abstract System Overview

```mermaid
graph TB
    subgraph "External World"
        USER[User<br/>Medical Query]
        MED[Medical<br/>Knowledge]
        HIST[Historical<br/>Context]
    end
    
    subgraph "Humansa V2 System Boundary"
        subgraph "Intelligence Layer"
            ORCH[Orchestrator<br/>Decision Engine]
            AGENTS[Agent Pool<br/>Specialized Experts]
            MEM[Memory Layer<br/>Context & History]
        end
        
        subgraph "Capability Layer"
            DIAG[Diagnostic<br/>Reasoning]
            TREAT[Treatment<br/>Planning]
            EMRG[Emergency<br/>Assessment]
            SCHED[Appointment<br/>Management]
        end
    end
    
    USER -->|Query| ORCH
    ORCH <-->|Coordinates| AGENTS
    ORCH <-->|Context| MEM
    AGENTS --> DIAG
    AGENTS --> TREAT
    AGENTS --> EMRG
    AGENTS --> SCHED
    
    MED -.->|Informs| AGENTS
    HIST -.->|Retrieved by| MEM
    
    ORCH -->|Response| USER
    
    style ORCH fill:#f9f,stroke:#333,stroke-width:4px
    style MEM fill:#bbf,stroke:#333,stroke-width:2px
    style AGENTS fill:#9f9,stroke:#333,stroke-width:2px
```

## Current Implementation Flow (Actual)

### What Actually Happens Now

```mermaid
sequenceDiagram
    participant U as User
    participant API as API Layer
    participant O as Orchestrator
    participant M as Memory
    participant A as Agents
    
    U->>API: Medical Query
    API->>O: run(query, user_id)
    
    rect rgb(255, 240, 240)
        Note over O: SINGLE PASS EXECUTION
        O->>M: Load user context
        M-->>O: Historical data
        
        O->>O: Simple keyword matching<br/>"diagnosis" → DiagnosisAgent<br/>"treatment" → TreatmentAgent
        
        O->>A: Execute selected agents<br/>(usually just one)
        A-->>O: Agent response
        
        O->>O: Basic synthesis<br/>(often just returns single response)
    end
    
    O->>M: Update memory
    O-->>API: Final response
    API-->>U: Answer
```

### Current Code Reality

```python
# What the code actually does:
async def _select_agents(self, query: str, context: Dict[str, Any]) -> List[str]:
    # TODO: Implement proper LLM-based agent selection
    # For now, return a simple selection based on keywords
    selected = []
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["diagnose", "diagnosis", "symptoms"]):
        selected.append("DiagnosisAgent")
    if any(word in query_lower for word in ["treatment", "medication", "therapy"]):
        selected.append("TreatmentAgent")
    
    return selected or ["GeneralMedicalAgent"]
```

**Current Limitations:**
- ❌ No iterative refinement
- ❌ No LLM-based agent selection
- ❌ No evaluation of completeness
- ❌ No re-routing based on agent results
- ❌ Simple keyword-based routing

## Proper Orchestrator Pattern (Ideal)

### How It Should Work

```mermaid
stateDiagram-v2
    [*] --> LoadContext: User Query
    
    LoadContext --> AnalyzeQuery: Memory Loaded
    
    AnalyzeQuery --> SelectAgents: Understand Intent
    
    SelectAgents --> ExecuteAgents: Agents Chosen
    
    ExecuteAgents --> EvaluateResults: Responses Received
    
    EvaluateResults --> Sufficient: Evaluate Completeness
    
    state Sufficient <<choice>>
    Sufficient --> SelectMoreAgents: Insufficient Info
    Sufficient --> SynthesizeResponse: Complete Info
    
    SelectMoreAgents --> ExecuteAgents: Additional Agents
    
    SynthesizeResponse --> UpdateMemory: Final Answer
    
    UpdateMemory --> [*]: Return Response
    
    note right of EvaluateResults
        Key Decision Point:
        - Do we have enough info?
        - Are there contradictions?
        - Need specialist input?
    end note
```

### Ideal Orchestrator Flow

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant LLM as Router LLM
    participant A1 as Agent 1
    participant A2 as Agent 2
    participant A3 as Final Agent
    participant M as Memory
    
    U->>O: "I have chest pain when exercising"
    
    O->>M: Load patient history
    M-->>O: Previous cardiac issues, medications
    
    rect rgb(240, 255, 240)
        Note over O,A3: ITERATION 1
        O->>LLM: Analyze query + context
        LLM-->>O: Need: EmergencyTriage + Diagnosis
        
        par Parallel Execution
            O->>A1: EmergencyTriageAgent
            A1-->>O: "Non-emergency but concerning"
        and
            O->>A2: DiagnosisAgent  
            A2-->>O: "Possible angina, need more info"
        end
        
        O->>LLM: Evaluate completeness
        LLM-->>O: "Need medication history check"
    end
    
    rect rgb(240, 240, 255)
        Note over O,A3: ITERATION 2
        O->>A3: MedicationAgent
        A3-->>O: "Patient on beta-blockers"
        
        O->>LLM: Evaluate completeness
        LLM-->>O: "Sufficient information"
    end
    
    rect rgb(255, 255, 240)
        Note over O: SYNTHESIS
        O->>LLM: Synthesize all findings
        LLM-->>O: Comprehensive response
    end
    
    O->>M: Update with new info
    O-->>U: "Based on your symptoms and current medications..."
```

## Conceptual Flow Diagram

### Multi-Level Decision Making

```mermaid
graph TD
    subgraph "Query Analysis Layer"
        Q[User Query] --> QA[Query Analyzer]
        QA --> INT[Intent<br/>Classification]
        QA --> URG[Urgency<br/>Assessment]
        QA --> COMP[Complexity<br/>Evaluation]
    end
    
    subgraph "Orchestration Layer"
        INT --> ROUTE[Dynamic Router]
        URG --> ROUTE
        COMP --> ROUTE
        
        ROUTE --> DEC{Decision<br/>Engine}
        
        DEC -->|Simple| SINGLE[Single Agent]
        DEC -->|Complex| MULTI[Multi-Agent]
        DEC -->|Critical| PRIORITY[Priority Path]
    end
    
    subgraph "Execution Layer"
        SINGLE --> EXEC[Execute]
        MULTI --> PARA[Parallel<br/>Execution]
        PRIORITY --> SEQ[Sequential<br/>Execution]
        
        EXEC --> EVAL{Evaluate<br/>Completeness}
        PARA --> EVAL
        SEQ --> EVAL
    end
    
    subgraph "Iteration Control"
        EVAL -->|Incomplete| REFINE[Refine<br/>Requirements]
        REFINE --> ROUTE
        
        EVAL -->|Complete| SYNTH[Synthesize]
        EVAL -->|Contradictory| RESOLVE[Resolve<br/>Conflicts]
        RESOLVE --> ROUTE
    end
    
    SYNTH --> RESP[Final Response]
    
    style DEC fill:#f9f,stroke:#333,stroke-width:2px
    style EVAL fill:#ff9,stroke:#333,stroke-width:2px
    style ROUTE fill:#9f9,stroke:#333,stroke-width:2px
```

## Information Flow Architecture

### How Information Should Flow Through the System

```mermaid
graph LR
    subgraph "Information Sources"
        CTX[User Context<br/>From Memory]
        QUERY[Current Query]
        HIST[Conversation<br/>History]
    end
    
    subgraph "Processing Pipeline"
        subgraph "Stage 1: Understanding"
            PARSE[Parse Intent]
            ENRICH[Enrich Context]
        end
        
        subgraph "Stage 2: Planning"
            PLAN[Execution Plan]
            SELECT[Agent Selection]
        end
        
        subgraph "Stage 3: Execution"
            EXEC[Agent Execution]
            COLLECT[Result Collection]
        end
        
        subgraph "Stage 4: Evaluation"
            CHECK[Completeness Check]
            VERIFY[Verification]
        end
        
        subgraph "Stage 5: Response"
            SYNTH[Synthesis]
            FORMAT[Formatting]
        end
    end
    
    CTX --> ENRICH
    QUERY --> PARSE
    HIST --> ENRICH
    
    PARSE --> PLAN
    ENRICH --> PLAN
    
    PLAN --> SELECT
    SELECT --> EXEC
    EXEC --> COLLECT
    
    COLLECT --> CHECK
    CHECK -->|Needs More| SELECT
    CHECK -->|Complete| VERIFY
    
    VERIFY --> SYNTH
    SYNTH --> FORMAT
    
    style CHECK fill:#ff9,stroke:#333,stroke-width:2px
```

## Comparison: Current vs Ideal

### Current Implementation Issues

| Aspect | Current Implementation | Ideal Implementation |
|--------|----------------------|---------------------|
| **Agent Selection** | Keyword matching | LLM-based reasoning |
| **Iteration** | Single pass | Multiple iterations until complete |
| **Completeness Check** | None | Evaluates if sufficient info gathered |
| **Conflict Resolution** | None | Handles contradictory information |
| **Learning** | Basic memory storage | Learns from outcomes |
| **Parallelization** | Sequential only | True parallel execution |
| **Context Awareness** | Basic memory load | Dynamic context enrichment |

### Workflow Comparison

```mermaid
graph TB
    subgraph "Current: Linear Flow"
        C1[Query] --> C2[Keyword Match]
        C2 --> C3[Run Agent]
        C3 --> C4[Return Response]
    end
    
    subgraph "Ideal: Iterative Flow"
        I1[Query] --> I2[Analyze Need]
        I2 --> I3[Select Agents]
        I3 --> I4[Execute]
        I4 --> I5{Complete?}
        I5 -->|No| I6[Identify Gaps]
        I6 --> I3
        I5 -->|Yes| I7[Synthesize]
        I7 --> I8[Response]
    end
    
    style C2 fill:#fcc,stroke:#333
    style I5 fill:#cfc,stroke:#333
```

## Testing the Current Implementation

### Test Case 1: Simple Query
```bash
curl -X POST http://localhost:5001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [{"role": "user", "content": "What are symptoms of diabetes?"}],
    "stream": false
  }'

# Expected: Single agent (DiagnosisAgent or GeneralMedical)
# Actual: Likely fails due to orchestrator initialization issues
```

### Test Case 2: Complex Query (Should Use Multiple Agents)
```bash
curl -X POST http://localhost:5001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [{"role": "user", "content": "I have diabetes symptoms and need treatment options plus appointment scheduling"}],
    "stream": false
  }'

# Expected in ideal: DiagnosisAgent → MedicationAgent → AppointmentAgent
# Actual: Probably only triggers one agent based on first keyword match
```

### Test Case 3: Iterative Refinement (Not Supported)
```bash
# This SHOULD trigger multiple rounds but won't in current implementation
curl -X POST http://localhost:5001/v2/humansa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "messages": [{"role": "user", "content": "I have vague symptoms - tired, thirsty, blurry vision sometimes"}],
    "stream": false
  }'

# Ideal: GeneralAgent → "Need more info" → DiagnosisAgent → "Possible diabetes" → Further tests
# Actual: Single agent response without follow-up
```

## Recommendations for True Orchestrator Pattern

### 1. Implement Iterative Loop
```python
async def orchestrate(self, query: str, user_id: str, max_iterations: int = 5):
    context = await self.load_context(user_id)
    results = []
    
    for iteration in range(max_iterations):
        # Analyze what we know and what we need
        analysis = await self.analyze_completeness(query, context, results)
        
        if analysis.is_complete:
            break
            
        # Select agents based on gaps
        agents = await self.select_agents_for_gaps(analysis.gaps)
        
        # Execute and collect results
        new_results = await self.execute_agents(agents, context)
        results.extend(new_results)
        
        # Update context with findings
        context = self.update_context(context, new_results)
    
    # Synthesize all results
    return await self.synthesize_response(results, context)
```

### 2. Add Completeness Evaluation
```python
async def analyze_completeness(self, query, context, results):
    prompt = f"""
    Query: {query}
    Context: {context}
    Results so far: {results}
    
    Evaluate:
    1. Do we have enough information to answer the query?
    2. What critical information is missing?
    3. Are there any contradictions to resolve?
    4. What additional agents could provide missing info?
    """
    
    return await self.llm.analyze(prompt)
```

### 3. Implement Dynamic Agent Selection
```python
async def select_agents_for_gaps(self, gaps):
    # Use LLM to map information gaps to specific agents
    # Consider agent capabilities and dependencies
    # Return ordered list of agents to execute
```

## Conclusion

The current Humansa V2 "orchestrator" is more of a simple router than a true orchestrator. It lacks:
- Iterative refinement
- Completeness evaluation  
- Dynamic agent selection
- Conflict resolution
- True parallel execution

To achieve the intended orchestrator pattern, significant refactoring is needed to implement the iterative loop, evaluation logic, and dynamic routing capabilities shown in the ideal flow diagrams above.