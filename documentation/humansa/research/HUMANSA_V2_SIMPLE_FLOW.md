# Humansa V2 Agent - Simplified Flow

## Abstract Architecture (< 10 Components)

```mermaid
graph TD
    %% User Input
    User[User Query] --> API[API Endpoint]
    
    %% Core Processing
    API --> Agent[Humansa Agent<br/>+<br/>ReAct Logic]
    
    %% Decision & Tools
    Agent --> Tools[Medical Tools]
    
    %% Data Layer
    Tools --> DB[(Database)]
    
    %% Response Flow
    DB --> Agent
    Agent --> Response[Response]
    Response --> User
    
    %% Configuration
    Config[.env Config] -.-> Agent
    Config -.-> DB

    %% Styling
    classDef userflow fill:#9cf,stroke:#333,stroke-width:2px
    classDef core fill:#f9f,stroke:#333,stroke-width:3px
    classDef data fill:#faa,stroke:#333,stroke-width:2px
    classDef config fill:#ddd,stroke:#666,stroke-width:1px,stroke-dasharray: 5 5
    
    class User,API,Response userflow
    class Agent,Tools core
    class DB data
    class Config config
```

## Key Components Explained

### 1. **User Query** 
- Natural language medical questions in Chinese/English
- Example: "我想找一个心脏科医生"

### 2. **API Endpoint**
- `/v1-humansa/chat/completions`
- OpenAI-compatible interface

### 3. **Humansa Agent**
- LlamaIndex ReAct Agent
- Thinks → Acts → Observes → Responds
- Filters out web search tools

### 4. **Medical Tools**
- `find_doctor_info` - Search doctors
- `book_appointment` - Schedule visits
- `get_pricing` - Check costs
- Other medical-specific tools

### 5. **Database**
- PostgreSQL with medical data
- Doctors, clinics, schedules, services

### 6. **Response**
- Structured JSON with:
  - Answer text
  - Agent reasoning trace
  - Tools used

### 7. **Config**
- Database credentials
- API keys
- Port settings

## Data Flow

1. **Input** → User asks medical question
2. **Process** → Agent thinks and selects tools
3. **Query** → Tools fetch data from database
4. **Reason** → Agent analyzes results
5. **Output** → Formatted response to user

## Recent Improvements

✅ Fixed database connections  
✅ Added test data  
✅ Tools return real results  
✅ 100% test success rate  
✅ Test output saved to markdown files