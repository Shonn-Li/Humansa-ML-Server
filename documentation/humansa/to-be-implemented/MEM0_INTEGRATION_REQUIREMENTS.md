# Mem0 Integration Requirements for Humansa Memory System

## Overview

This document outlines the requirements and implementation plan for integrating Mem0 as the memory layer for the Humansa medical AI system within the YouWoAI platform.

## System Requirements

### 1. Technology Stack Requirements

#### Core Dependencies
```bash
# Python environment
Python 3.8+
pip install mem0ai

# Database
PostgreSQL 14+ with pgvector extension
- CREATE EXTENSION vector;

# LLM Provider (Azure OpenAI)
- Azure OpenAI API access
- Deployments for:
  - GPT-4 (for memory extraction)
  - text-embedding-ada-002 (for embeddings)
```

#### Infrastructure Requirements
- PostgreSQL database (existing YouWoAI database can be used)
- Separate schema for Mem0 tables (recommended: `mem0_humansa`)
- Redis for caching (optional but recommended)

### 2. Architecture Design

#### Service Separation Strategy

```
┌────────────────────────────────────────────────────────────────┐
│                     Modular Architecture                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────────────┐         │
│  │  Backend API    │      │    ML Server            │         │
│  │  (NestJS)       │◄─────┤    (Python/Quart)       │         │
│  │                 │ REST │                         │         │
│  │  Responsibilities:     │  Responsibilities:      │         │
│  │  - User Auth    │      │  - Agent Orchestration  │         │
│  │  - OAuth        │      │  - Memory Management    │         │
│  │  - Conversations│      │  - RAG Operations       │         │
│  │  - Subscriptions│      │  - Medical Knowledge    │         │
│  └─────────────────┘      └─────────────────────────┘         │
│           │                            │                        │
│           │                            │                        │
│           ▼                            ▼                        │
│  ┌───────────────────────────────────────────────────┐        │
│  │              PostgreSQL Database                   │        │
│  ├───────────────────────────────────────────────────┤        │
│  │  public schema          │  mem0_humansa schema    │        │
│  │  - user_v1              │  - mem0_memories        │        │
│  │  - conversation_v1      │  - mem0_embeddings      │        │
│  │  - subscription_v1      │  - mem0_metadata        │        │
│  │  - embedding_v1         │  - mem0_history         │        │
│  └───────────────────────────────────────────────────┘        │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 3. Data Flow Requirements

#### Conversation Flow
1. User sends message → Backend API
2. Backend creates conversation record
3. Backend forwards to ML Server
4. ML Server processes with Humansa agent
5. ML Server stores memory in Mem0 (async)
6. Response sent back through Backend

#### Memory Operations
- **Async Processing**: Memory storage should not block response
- **Batch Support**: Handle multiple messages efficiently
- **Error Recovery**: Failed memory operations shouldn't crash system

### 4. User ID Mapping

#### Strategy: Prefixed User IDs
```python
# Format: {service}_{environment}_{user_id}
# Examples:
# - Production: humansa_prod_12345
# - Test: humansa_test_12345
# - Development: humansa_dev_12345

def get_memory_user_id(user_id: int, environment: str = "prod") -> str:
    return f"humansa_{environment}_{user_id}"
```

### 5. Configuration Requirements

#### Environment Variables
```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding-ada-002

# Database Configuration (existing)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=youwoai

# Mem0 Specific
MEM0_SCHEMA=mem0_humansa
MEM0_COLLECTION_NAME=humansa_memories
MEM0_ENABLE_CACHE=true
```

### 6. API Endpoints Requirements

#### Memory Management Endpoints
```
POST   /v2/humansa/memory/add         - Add conversation to memory
POST   /v2/humansa/memory/search      - Search user memories
GET    /v2/humansa/memory/context/:id - Get user context
DELETE /v2/humansa/memory/user/:id    - Delete user memories (GDPR)
GET    /v2/humansa/memory/export/:id  - Export user memories (GDPR)
```

#### Integration with Existing Endpoints
- Modify `/v1-humansa/chat/completions` to use memory context
- Update conversation endpoints to trigger memory storage

### 7. Database Schema Requirements

#### Mem0 Tables (Auto-created)
```sql
-- Schema: mem0_humansa

-- Main memory storage
CREATE TABLE mem0_humansa.memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory TEXT NOT NULL,
    hash VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embedding storage
CREATE TABLE mem0_humansa.memory_embeddings (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER REFERENCES mem0_humansa.memories(id),
    embedding vector(1536),
    model VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_mem0_user_id ON mem0_humansa.memories(user_id);
CREATE INDEX idx_mem0_embedding ON mem0_humansa.memory_embeddings 
    USING ivfflat (embedding vector_cosine_ops);
```

### 8. Integration Points

#### ML Server Integration
```python
# src/humansa/v2/memory_integration.py

from mem0 import Memory
from typing import Dict, List, Any

class HumansaMemoryIntegration:
    def __init__(self, app_config):
        self.memory = self._initialize_mem0(app_config)
        
    def _initialize_mem0(self, config):
        return Memory.from_config({
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "api_key": config['AZURE_OPENAI_API_KEY'],
                    "azure_endpoint": config['AZURE_OPENAI_ENDPOINT'],
                    "azure_deployment": config['AZURE_OPENAI_DEPLOYMENT_GPT4'],
                    "api_version": "2024-02-01"
                }
            },
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": config['DB_HOST'],
                    "port": config['DB_PORT'],
                    "user": config['DB_USER'],
                    "password": config['DB_PASSWORD'],
                    "database": config['DB_NAME'],
                    "collection_name": config['MEM0_COLLECTION_NAME']
                }
            }
        })
    
    async def store_conversation(
        self, 
        user_id: int, 
        messages: List[Dict[str, str]],
        conversation_id: str
    ):
        """Store conversation in memory system"""
        memory_user_id = f"humansa_prod_{user_id}"
        
        # Add metadata
        metadata = {
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "humansa_chat"
        }
        
        # Store in Mem0 (async wrapper needed)
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.memory.add,
            messages,
            memory_user_id,
            metadata
        )
```

### 9. Testing Requirements

#### Test Environment Setup
```yaml
# docker-compose.test.yml additions
services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_DB: youwoai_test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    command: |
      postgres -c shared_preload_libraries=vector
    volumes:
      - ./test-scripts/init-mem0.sql:/docker-entrypoint-initdb.d/10-mem0.sql
```

#### Test Data Requirements
- Create test users with known IDs
- Seed test conversations with medical context
- Generate test memories for retrieval testing

### 10. Performance Requirements

#### Response Time Targets
- Memory retrieval: < 100ms
- Memory storage: Async (non-blocking)
- Context building: < 200ms

#### Scalability Targets
- Support 10,000+ active users
- 100+ memories per user
- 50+ concurrent requests

### 11. Security & Privacy Requirements

#### Data Protection
- User memories isolated by user_id
- No cross-user memory access
- Encryption at rest (PostgreSQL TDE)
- Secure API authentication

#### GDPR Compliance
- User data export endpoint
- User data deletion endpoint
- Audit logging for all operations
- Consent tracking

### 12. Monitoring Requirements

#### Metrics to Track
- Memory storage success/failure rate
- Average memory retrieval time
- Memory database size growth
- API endpoint latencies

#### Logging Requirements
```python
# Structured logging for memory operations
logger.info("memory_operation", {
    "operation": "store",
    "user_id": user_id,
    "message_count": len(messages),
    "success": True,
    "duration_ms": duration
})
```

## Implementation Phases

### Phase 1: Infrastructure Setup (Week 1)
- [ ] Set up PostgreSQL with pgvector
- [ ] Create mem0_humansa schema
- [ ] Configure Azure OpenAI access
- [ ] Create test environment

### Phase 2: Core Integration (Week 2)
- [ ] Implement HumansaMemoryService
- [ ] Create memory API endpoints
- [ ] Integrate with existing chat flow
- [ ] Add async processing

### Phase 3: Testing & Optimization (Week 3)
- [ ] Unit tests for memory service
- [ ] Integration tests
- [ ] Performance testing
- [ ] Load testing

### Phase 4: Production Deployment (Week 4)
- [ ] Deploy to staging
- [ ] Run acceptance tests
- [ ] Deploy to production
- [ ] Monitor and optimize

## Success Criteria

1. **Functional Requirements**
   - ✓ Conversations stored in Mem0
   - ✓ Memory retrieval working
   - ✓ Context enhancement active
   - ✓ GDPR endpoints functional

2. **Performance Requirements**
   - ✓ < 100ms memory retrieval
   - ✓ No impact on chat latency
   - ✓ Handles 100 concurrent users

3. **Quality Requirements**
   - ✓ 90%+ test coverage
   - ✓ No memory leaks
   - ✓ Proper error handling
   - ✓ Comprehensive logging

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mem0 API changes | High | Pin version, monitor changelog |
| Database performance | Medium | Proper indexing, connection pooling |
| Memory conflicts | Low | Implement versioning strategy |
| Data privacy concerns | High | Strict access controls, encryption |

## Conclusion

Integrating Mem0 provides a robust, scalable solution for user memory management in the Humansa system. The modular architecture ensures clean separation of concerns while maintaining system flexibility for future enhancements.