# Mem0 Technology Stack Analysis & Integration Report

## Executive Summary

Mem0 is a production-ready memory layer for AI agents with 36.6k GitHub stars. It provides a unified interface for managing user-specific memories while supporting multiple backends including PostgreSQL with pgvector. This report analyzes its technical requirements and provides recommendations for integrating with the YouWoAI system.

## Mem0 Technology Stack

### Core Dependencies

```python
# Required technologies
- Python 3.8+
- OpenAI API (or compatible LLM provider)
- Vector store backend (one of):
  - PostgreSQL with pgvector extension
  - Qdrant
  - ChromaDB
  - Pinecone
  - Weaviate
```

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 Mem0 Core                       │
├─────────────────────────────────────────────────┤
│  Memory Manager                                 │
│  ├── Extraction Layer (LLM-based)              │
│  ├── Embedding Layer (OpenAI/custom)           │
│  ├── Storage Layer (Vector DB)                 │
│  └── Retrieval Layer (Semantic Search)         │
├─────────────────────────────────────────────────┤
│  Supported Backends                             │
│  ├── PostgreSQL + pgvector ✅                  │
│  ├── Qdrant                                    │
│  ├── ChromaDB                                  │
│  └── Others...                                 │
└─────────────────────────────────────────────────┘
```

### PostgreSQL + pgvector Configuration

```python
# Minimal configuration for PostgreSQL backend
config = {
    "llm": {
        "provider": "azure_openai",  # Supports Azure
        "config": {
            "api_key": "your-azure-key",
            "azure_endpoint": "https://your-endpoint.openai.azure.com",
            "api_version": "2024-02-01",
            "azure_deployment": "gpt-4"
        }
    },
    "embedder": {
        "provider": "azure_openai",
        "config": {
            "api_key": "your-azure-key",
            "azure_endpoint": "https://your-endpoint.openai.azure.com",
            "api_version": "2024-02-01",
            "azure_deployment": "text-embedding-ada-002"
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password",
            "database": "mem0_db"
        }
    }
}
```

### Database Requirements

1. **PostgreSQL Setup**:
   ```sql
   -- Create database
   CREATE DATABASE mem0_db;
   
   -- Enable pgvector extension
   CREATE EXTENSION IF NOT EXISTS vector;
   
   -- Mem0 will create these tables automatically:
   -- - mem0_memories (stores memory content and metadata)
   -- - mem0_memory_embeddings (stores vector embeddings)
   ```

2. **Storage Schema** (auto-created by Mem0):
   - Memory content table with user_id indexing
   - Embedding vectors (1536 dimensions for OpenAI)
   - Metadata JSONB for flexible attributes
   - Timestamps for temporal queries

## Integration Architecture for YouWoAI

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YouWoAI System                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────┐         │
│  │  Backend Server  │         │    ML Server         │         │
│  │  (NestJS)        │◄────────┤  (Quart/Python)      │         │
│  │                  │  API    │                      │         │
│  │  - User Auth     │         │  - Humansa Agent    │         │
│  │  - Conversations │         │  - Multi-Agent       │         │
│  │  - Subscriptions │         │  - RAG System        │         │
│  └──────────────────┘         └──────────────────────┘         │
│           │                              │                       │
│           │                              │                       │
│           ▼                              ▼                       │
│  ┌──────────────────────────────────────────────────┐          │
│  │           Shared PostgreSQL Database              │          │
│  ├──────────────────────────────────────────────────┤          │
│  │  YouWoAI Tables        │  Mem0 Tables            │          │
│  │  - user_v1             │  - mem0_memories        │          │
│  │  - conversation_v1     │  - mem0_embeddings      │          │
│  │  - embedding_v1        │  - mem0_metadata        │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Strategy

#### Option 1: Shared Database, Separate Schema (Recommended)

```sql
-- Create separate schema for Mem0
CREATE SCHEMA IF NOT EXISTS mem0;

-- Configure Mem0 to use this schema
config = {
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password",
            "database": "youwoai_db",
            "schema": "mem0"  # Separate schema
        }
    }
}
```

**Advantages**:
- Single database to manage
- Easy cross-schema queries if needed
- Shared connection pooling
- Consistent backups

#### Option 2: Separate Database

```sql
-- Create dedicated Mem0 database
CREATE DATABASE humansa_memory;
```

**Advantages**:
- Complete isolation
- Independent scaling
- No risk of interference
- Easier to migrate later

### User ID Mapping Strategy

```python
class HumansaMemoryBridge:
    """Bridge between YouWoAI users and Mem0 memories"""
    
    def get_memory_user_id(self, youwoai_user_id: int, context: str = "humansa") -> str:
        """
        Create consistent memory user ID from YouWoAI user ID
        Format: {context}_{user_id}
        Example: humansa_12345
        """
        return f"{context}_{youwoai_user_id}"
    
    def parse_memory_user_id(self, memory_user_id: str) -> tuple[str, int]:
        """Extract context and user ID from memory user ID"""
        context, user_id = memory_user_id.split('_', 1)
        return context, int(user_id)
```

### Conversation Storage Strategy

Since Mem0 handles its own conversation storage for memory extraction, we need to decide on data flow:

```python
class ConversationSyncStrategy:
    """
    Option A: Dual Storage (Recommended)
    - Store full conversations in conversation_v1 table
    - Send copies to Mem0 for memory extraction
    """
    async def sync_conversation_to_memory(
        self,
        conversation_id: int,
        messages: List[Message]
    ):
        # 1. Store in YouWoAI database as usual
        await self.conversation_service.save_messages(conversation_id, messages)
        
        # 2. Send to Mem0 for memory extraction
        memory_user_id = self.get_memory_user_id(user_id)
        self.mem0.add(
            messages=[
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            user_id=memory_user_id,
            metadata={
                "conversation_id": conversation_id,
                "source": "humansa",
                "timestamp": datetime.utcnow()
            }
        )
    
    """
    Option B: Mem0 as Primary Storage
    - Let Mem0 handle all conversation storage
    - Query Mem0 for conversation history
    """
```

## Modular Agent Service Design

### Proposed Humansa Memory Service

```python
# src/humansa/memory/humansa_memory_service.py

from mem0 import Memory
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class HumansaMemoryConfig:
    """Configuration for Humansa memory system"""
    azure_endpoint: str
    azure_api_key: str
    azure_deployment: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    memory_schema: str = "mem0_humansa"

class HumansaMemoryService:
    """
    Standalone memory service for Humansa agents
    Can be used independently or integrated with other services
    """
    
    def __init__(self, config: HumansaMemoryConfig):
        self.config = config
        self._init_mem0()
        
    def _init_mem0(self):
        """Initialize Mem0 with configuration"""
        self.memory = Memory.from_config({
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "api_key": self.config.azure_api_key,
                    "azure_endpoint": self.config.azure_endpoint,
                    "azure_deployment": self.config.azure_deployment,
                    "api_version": "2024-02-01"
                }
            },
            "embedder": {
                "provider": "azure_openai",
                "config": {
                    "api_key": self.config.azure_api_key,
                    "azure_endpoint": self.config.azure_endpoint,
                    "azure_deployment": "text-embedding-ada-002",
                    "api_version": "2024-02-01"
                }
            },
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": self.config.db_host,
                    "port": self.config.db_port,
                    "user": self.config.db_user,
                    "password": self.config.db_password,
                    "database": self.config.db_name,
                    "collection_name": f"{self.config.memory_schema}_memories"
                }
            },
            "history_db_path": f"{self.config.memory_schema}_history.db"
        })
    
    async def add_conversation(
        self,
        user_id: int,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add conversation to memory"""
        memory_user_id = f"humansa_{user_id}"
        
        # Add default metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            "source": "humansa",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Mem0 operations are sync, so run in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.memory.add,
            messages,
            memory_user_id,
            metadata
        )
    
    async def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search user memories"""
        memory_user_id = f"humansa_{user_id}"
        
        loop = asyncio.get_event_loop()
        memories = await loop.run_in_executor(
            None,
            self.memory.search,
            query,
            memory_user_id,
            limit
        )
        
        return memories
    
    async def get_user_context(
        self,
        user_id: int,
        recent_limit: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive user context for agents"""
        memory_user_id = f"humansa_{user_id}"
        
        loop = asyncio.get_event_loop()
        
        # Get all memories
        all_memories = await loop.run_in_executor(
            None,
            self.memory.get_all,
            memory_user_id
        )
        
        # Extract key information
        context = {
            "user_id": user_id,
            "memory_count": len(all_memories),
            "recent_memories": all_memories[:recent_limit],
            "extracted_facts": self._extract_facts(all_memories),
            "preferences": self._extract_preferences(all_memories),
            "medical_context": self._extract_medical_context(all_memories)
        }
        
        return context
    
    def _extract_facts(self, memories: List[Dict]) -> List[str]:
        """Extract factual information from memories"""
        facts = []
        for memory in memories:
            if memory.get("metadata", {}).get("type") == "fact":
                facts.append(memory["memory"])
        return facts
    
    def _extract_preferences(self, memories: List[Dict]) -> List[str]:
        """Extract user preferences from memories"""
        preferences = []
        for memory in memories:
            content = memory.get("memory", "").lower()
            if any(word in content for word in ["prefer", "like", "favorite", "want"]):
                preferences.append(memory["memory"])
        return preferences
    
    def _extract_medical_context(self, memories: List[Dict]) -> Dict[str, List[str]]:
        """Extract medical context from memories"""
        medical = {
            "conditions": [],
            "medications": [],
            "allergies": [],
            "symptoms": []
        }
        
        # Simple keyword-based extraction (enhance with NER later)
        for memory in memories:
            content = memory.get("memory", "").lower()
            
            if any(word in content for word in ["diabetes", "hypertension", "asthma"]):
                medical["conditions"].append(memory["memory"])
            elif any(word in content for word in ["metformin", "insulin", "aspirin"]):
                medical["medications"].append(memory["memory"])
            elif any(word in content for word in ["allergy", "allergic"]):
                medical["allergies"].append(memory["memory"])
            elif any(word in content for word in ["pain", "headache", "fever"]):
                medical["symptoms"].append(memory["memory"])
        
        return medical
```

### API Endpoints for Memory Service

```python
# src/humansa/memory/endpoints/memory_endpoints.py

from quart import Blueprint, request, jsonify
from ..humansa_memory_service import HumansaMemoryService

memory_bp = Blueprint('humansa_memory', __name__)

@memory_bp.route('/v2/humansa/memory/add', methods=['POST'])
async def add_memory():
    """Add conversation to user memory"""
    data = await request.json
    user_id = data.get('user_id')
    messages = data.get('messages')
    metadata = data.get('metadata', {})
    
    memory_service = request.app.humansa_memory_service
    await memory_service.add_conversation(user_id, messages, metadata)
    
    return jsonify({"status": "success", "message": "Memory added"})

@memory_bp.route('/v2/humansa/memory/search', methods=['POST'])
async def search_memory():
    """Search user memories"""
    data = await request.json
    user_id = data.get('user_id')
    query = data.get('query')
    limit = data.get('limit', 10)
    
    memory_service = request.app.humansa_memory_service
    memories = await memory_service.search_memories(user_id, query, limit)
    
    return jsonify({"status": "success", "memories": memories})

@memory_bp.route('/v2/humansa/memory/context/<int:user_id>', methods=['GET'])
async def get_user_context(user_id: int):
    """Get user context for agent"""
    memory_service = request.app.humansa_memory_service
    context = await memory_service.get_user_context(user_id)
    
    return jsonify({"status": "success", "context": context})
```

## Entity Management Recommendations

### Who Manages What?

```
┌─────────────────────────────────────────────────────────────┐
│                    Entity Ownership                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Backend Server (NestJS) Manages:                           │
│  ├── User authentication & profiles (user_v1)               │
│  ├── Subscription & payments                                │
│  ├── Conversation metadata (conversation_v1)               │
│  ├── File uploads & storage                                │
│  └── Access control & permissions                          │
│                                                              │
│  ML Server (Python) Manages:                                │
│  ├── Agent orchestration                                   │
│  ├── RAG operations (embedding_v1)                         │
│  ├── Memory extraction & storage (via Mem0)                │
│  ├── Medical knowledge base                                │
│  └── Real-time inference                                   │
│                                                              │
│  Mem0 Manages:                                              │
│  ├── User memory storage                                   │
│  ├── Memory embeddings                                     │
│  ├── Semantic search                                       │
│  └── Memory lifecycle                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Registration**: Backend → Creates user_v1 record
2. **Conversation Start**: Backend → Creates conversation_v1 record
3. **Message Processing**: Backend → ML Server → Humansa Agent
4. **Memory Extraction**: ML Server → Mem0 (async)
5. **Context Retrieval**: ML Server ← Mem0 → Agent

## Test Environment Setup

### Docker Compose Configuration

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: youwoai_test
    ports:
      - "5454:5432"
    volumes:
      - ./init-scripts:/docker-entrypoint-initdb.d
    command: >
      postgres
      -c shared_preload_libraries=vector
      -c max_connections=200

  ml-server:
    build: ./YouWoAI-ML-Server-1
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_NAME: youwoai_test
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      MEM0_SCHEMA: mem0_test
    depends_on:
      - postgres
    ports:
      - "5001:5001"

  backend:
    build: ./YouWoAI-Server-1
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USERNAME: postgres
      DB_PASSWORD: postgres
      DB_ACTIVE_DATABASE: youwoai_test
    depends_on:
      - postgres
    ports:
      - "3000:3000"
```

### Database Initialization Script

```sql
-- init-scripts/01-init-mem0.sql

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create separate schema for Mem0
CREATE SCHEMA IF NOT EXISTS mem0_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA mem0_test TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mem0_test TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mem0_test TO postgres;

-- Create test user for Humansa
INSERT INTO user_v1 (email, name, "createdAt", "updatedAt")
VALUES ('test@humansa.com', 'Test User', NOW(), NOW())
ON CONFLICT DO NOTHING;
```

## Performance Considerations

### Memory Optimization

1. **Batch Operations**: Process conversations in batches
2. **Async Processing**: Don't block on memory operations
3. **Caching**: Cache frequently accessed memories
4. **Indexing**: Ensure proper indexes on user_id fields

### Scaling Strategy

```python
# Use connection pooling
from asyncpg import create_pool

class ScalableMemoryService:
    def __init__(self):
        self.db_pool = None
        
    async def initialize(self):
        self.db_pool = await create_pool(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            min_size=10,
            max_size=20
        )
```

## Security Considerations

1. **Data Isolation**: Each user's memories are isolated by user_id
2. **Encryption**: Enable PostgreSQL encryption at rest
3. **Access Control**: Implement proper authentication before memory access
4. **Audit Trail**: Log all memory operations
5. **GDPR Compliance**: Implement user data export/deletion

## Next Steps

1. **Phase 1**: Set up test environment with Mem0
2. **Phase 2**: Implement HumansaMemoryService
3. **Phase 3**: Integrate with existing Humansa agents
4. **Phase 4**: Migrate existing conversation data
5. **Phase 5**: Performance optimization

## Conclusion

Mem0 provides a robust, production-ready solution for user memory management. By using PostgreSQL with pgvector, we can leverage our existing database infrastructure while gaining powerful semantic search capabilities. The modular design allows for easy integration while maintaining separation of concerns between services.