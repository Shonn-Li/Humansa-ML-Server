# Humanza Memory System - Technical Implementation Guide

## Quick Start Implementation

### 1. Enhanced Memory Manager

```python
# src/humansa/v2/memory/enhanced_memory_manager.py

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import asyncpg
import numpy as np
from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
import chromadb
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    """Represents a memory item with metadata"""
    content: str
    type: str  # 'symptom', 'condition', 'medication', etc.
    timestamp: datetime
    confidence: float
    source: str  # 'conversation', 'form', 'import'
    metadata: Dict[str, Any]

class EnhancedMemoryManager:
    """Advanced memory management for Humanza with hierarchical storage"""
    
    def __init__(self, db_pool: asyncpg.Pool, openai_api_key: str):
        self.db_pool = db_pool
        self.embed_model = OpenAIEmbedding(api_key=openai_api_key)
        
        # Initialize vector store for mid-term memory
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.create_collection(
            name="humansa_memories",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Short-term memory cache
        self._short_term_cache: Dict[str, List[MemoryItem]] = {}
        self._cache_ttl = timedelta(hours=24)
        
    async def initialize_enhanced_tables(self):
        """Create enhanced database schema"""
        async with self.db_pool.acquire() as conn:
            # Enhanced patient profile with structured data
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS humansa_patient_profile_v2 (
                    user_id TEXT PRIMARY KEY,
                    -- Basic Demographics
                    age INTEGER,
                    gender TEXT,
                    occupation TEXT,
                    location TEXT,
                    
                    -- Medical Information (structured)
                    blood_type TEXT,
                    height_cm INTEGER,
                    weight_kg FLOAT,
                    
                    -- Complex data as JSONB
                    conditions JSONB DEFAULT '[]',
                    medications JSONB DEFAULT '[]',
                    allergies JSONB DEFAULT '[]',
                    family_history JSONB DEFAULT '[]',
                    lifestyle JSONB DEFAULT '{}',
                    preferences JSONB DEFAULT '{}',
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP,
                    profile_completeness FLOAT DEFAULT 0.0
                )
            """)
            
            # Temporal entity tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS humansa_temporal_entities (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_value TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    valid_from TIMESTAMP NOT NULL,
                    valid_to TIMESTAMP,
                    source TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES humansa_patient_profile_v2(user_id)
                )
            """)
            
            # Memory embeddings reference
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS humansa_memory_embeddings (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding_id TEXT NOT NULL,  -- ChromaDB reference
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    importance_score FLOAT DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES humansa_patient_profile_v2(user_id)
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_user_type 
                ON humansa_temporal_entities(user_id, entity_type, valid_from DESC);
                
                CREATE INDEX IF NOT EXISTS idx_memory_user_type
                ON humansa_memory_embeddings(user_id, memory_type, created_at DESC);
            """)

    async def extract_entities_from_conversation(
        self, 
        messages: List[Dict[str, str]]
    ) -> Dict[str, List[MemoryItem]]:
        """Extract medical entities from conversation using LLM"""
        
        # Prepare conversation text
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages
        ])
        
        # Use LLM for entity extraction
        extraction_prompt = f"""
        Extract medical information from this conversation.
        Return a JSON with these categories:
        - symptoms: current symptoms mentioned
        - conditions: medical conditions discussed
        - medications: medications mentioned
        - allergies: allergies mentioned
        - lifestyle: lifestyle factors (diet, exercise, habits)
        - demographics: age, gender, occupation if mentioned
        
        For each item, include confidence (0-1) based on how certain the information is.
        
        Conversation:
        {conversation_text}
        
        Return only valid JSON.
        """
        
        # TODO: Call LLM and parse response
        # For now, return placeholder
        return {
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "allergies": [],
            "lifestyle": [],
            "demographics": []
        }

    async def update_user_profile_intelligent(
        self,
        user_id: str,
        extracted_entities: Dict[str, List[MemoryItem]]
    ):
        """Intelligently update user profile with conflict resolution"""
        
        async with self.db_pool.acquire() as conn:
            # Get current profile
            current_profile = await conn.fetchrow(
                "SELECT * FROM humansa_patient_profile_v2 WHERE user_id = $1",
                user_id
            )
            
            if not current_profile:
                # Create new profile
                await conn.execute(
                    "INSERT INTO humansa_patient_profile_v2 (user_id) VALUES ($1)",
                    user_id
                )
                current_profile = {}
            
            # Process each entity type
            for entity_type, items in extracted_entities.items():
                for item in items:
                    # Check for conflicts with temporal data
                    existing = await conn.fetch("""
                        SELECT * FROM humansa_temporal_entities
                        WHERE user_id = $1 AND entity_type = $2 
                        AND entity_value = $3 AND valid_to IS NULL
                        ORDER BY valid_from DESC
                    """, user_id, entity_type, item.content)
                    
                    if existing and existing[0]['confidence'] >= item.confidence:
                        # Skip if existing data is more confident
                        continue
                    
                    if existing:
                        # Invalidate old entry
                        await conn.execute("""
                            UPDATE humansa_temporal_entities
                            SET valid_to = $1
                            WHERE id = $2
                        """, datetime.utcnow(), existing[0]['id'])
                    
                    # Insert new temporal entity
                    await conn.execute("""
                        INSERT INTO humansa_temporal_entities
                        (user_id, entity_type, entity_value, confidence, 
                         valid_from, source, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, user_id, entity_type, item.content, item.confidence,
                         item.timestamp, item.source, json.dumps(item.metadata))
            
            # Update profile completeness
            await self._calculate_profile_completeness(user_id)

    async def store_memory_embedding(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        importance: float = 0.5
    ):
        """Store memory in vector database with embedding"""
        
        # Generate embedding
        embedding = await self.embed_model.aget_text_embedding(content)
        
        # Store in ChromaDB
        embedding_id = f"{user_id}_{memory_type}_{datetime.utcnow().isoformat()}"
        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "type": memory_type,
                "timestamp": datetime.utcnow().isoformat(),
                "importance": importance
            }],
            ids=[embedding_id]
        )
        
        # Store reference in PostgreSQL
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO humansa_memory_embeddings
                (user_id, memory_type, content, embedding_id, importance_score)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, memory_type, content, embedding_id, importance)

    async def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        time_decay_factor: float = 0.95
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories with time-weighted scoring"""
        
        # Generate query embedding
        query_embedding = await self.embed_model.aget_text_embedding(query)
        
        # Build filter
        where_clause = {"user_id": user_id}
        if memory_types:
            where_clause["type"] = {"$in": memory_types}
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # Get extra for post-filtering
            where=where_clause
        )
        
        # Get additional metadata from PostgreSQL
        memories = []
        async with self.db_pool.acquire() as conn:
            for i, doc_id in enumerate(results['ids'][0]):
                memory_data = await conn.fetchrow("""
                    SELECT * FROM humansa_memory_embeddings
                    WHERE embedding_id = $1
                """, doc_id)
                
                if memory_data:
                    # Calculate time-weighted score
                    age_days = (datetime.utcnow() - memory_data['created_at']).days
                    time_weight = time_decay_factor ** age_days
                    
                    # Combine similarity and time weight
                    final_score = results['distances'][0][i] * time_weight
                    
                    memories.append({
                        'content': results['documents'][0][i],
                        'type': memory_data['memory_type'],
                        'created_at': memory_data['created_at'],
                        'score': final_score,
                        'metadata': results['metadatas'][0][i]
                    })
        
        # Sort by final score and limit
        memories.sort(key=lambda x: x['score'], reverse=True)
        return memories[:limit]

    async def get_comprehensive_user_context(
        self,
        user_id: str,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive user context for agents"""
        
        async with self.db_pool.acquire() as conn:
            # Get current profile
            profile = await conn.fetchrow(
                "SELECT * FROM humansa_patient_profile_v2 WHERE user_id = $1",
                user_id
            )
            
            if not profile:
                return {"user_id": user_id, "profile": {}, "active_entities": {}}
            
            # Get active temporal entities
            active_entities = {}
            entity_types = ['symptoms', 'conditions', 'medications', 'allergies']
            
            for entity_type in entity_types:
                entities = await conn.fetch("""
                    SELECT entity_value, confidence, valid_from, metadata
                    FROM humansa_temporal_entities
                    WHERE user_id = $1 AND entity_type = $2 AND valid_to IS NULL
                    ORDER BY confidence DESC, valid_from DESC
                """, user_id, entity_type)
                
                active_entities[entity_type] = [
                    {
                        'value': e['entity_value'],
                        'confidence': e['confidence'],
                        'since': e['valid_from'],
                        'metadata': e['metadata']
                    }
                    for e in entities
                ]
            
            # Build context
            context = {
                'user_id': user_id,
                'profile': dict(profile),
                'active_entities': active_entities,
                'last_interaction': profile['last_interaction'],
                'profile_completeness': profile['profile_completeness']
            }
            
            if include_history:
                # Get recent conversation summary
                recent_memories = await self.retrieve_relevant_memories(
                    user_id, 
                    "recent medical history",
                    limit=5
                )
                context['recent_context'] = recent_memories
            
            return context

    async def _calculate_profile_completeness(self, user_id: str):
        """Calculate and update profile completeness score"""
        
        required_fields = [
            'age', 'gender', 'conditions', 'medications', 
            'allergies', 'lifestyle'
        ]
        
        async with self.db_pool.acquire() as conn:
            profile = await conn.fetchrow(
                "SELECT * FROM humansa_patient_profile_v2 WHERE user_id = $1",
                user_id
            )
            
            if not profile:
                return 0.0
            
            completed = 0
            for field in required_fields:
                value = profile.get(field)
                if value and (
                    (isinstance(value, list) and len(value) > 0) or
                    (isinstance(value, dict) and len(value) > 0) or
                    (isinstance(value, (str, int, float)) and value)
                ):
                    completed += 1
            
            completeness = completed / len(required_fields)
            
            await conn.execute("""
                UPDATE humansa_patient_profile_v2
                SET profile_completeness = $1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $2
            """, completeness, user_id)
            
            return completeness


# Integration with existing Humanza agent
class MemoryAwareHumansaAgent:
    """Enhanced Humansa agent with memory capabilities"""
    
    def __init__(self, memory_manager: EnhancedMemoryManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory = memory_manager
        
    async def process_with_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]]
    ) -> str:
        """Process query with full memory context"""
        
        # 1. Get user context
        context = await self.memory.get_comprehensive_user_context(user_id)
        
        # 2. Extract entities from current conversation
        extracted = await self.memory.extract_entities_from_conversation(messages)
        
        # 3. Build enhanced prompt with context
        enhanced_prompt = self._build_contextual_prompt(messages[-1]['content'], context)
        
        # 4. Process with agent
        response = await self.process_query(enhanced_prompt)
        
        # 5. Update memory asynchronously
        asyncio.create_task(
            self._update_memory_async(user_id, messages, response, extracted)
        )
        
        return response
    
    async def _update_memory_async(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        response: str,
        extracted_entities: Dict[str, List[MemoryItem]]
    ):
        """Update memory in background"""
        try:
            # Update profile with extracted entities
            await self.memory.update_user_profile_intelligent(user_id, extracted_entities)
            
            # Store conversation as memory
            conversation_summary = self._summarize_conversation(messages, response)
            await self.memory.store_memory_embedding(
                user_id,
                conversation_summary,
                "conversation",
                importance=0.7
            )
            
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
    
    def _build_contextual_prompt(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt with user context"""
        
        # Format active conditions
        conditions = context['active_entities'].get('conditions', [])
        medications = context['active_entities'].get('medications', [])
        allergies = context['active_entities'].get('allergies', [])
        
        context_parts = []
        
        if conditions:
            context_parts.append(
                f"Known conditions: {', '.join([c['value'] for c in conditions[:5]])}"
            )
        
        if medications:
            context_parts.append(
                f"Current medications: {', '.join([m['value'] for m in medications[:5]])}"
            )
        
        if allergies:
            context_parts.append(
                f"Allergies: {', '.join([a['value'] for a in allergies])}"
            )
        
        if context['last_interaction']:
            days_since = (datetime.utcnow() - context['last_interaction']).days
            context_parts.append(f"Last interaction: {days_since} days ago")
        
        context_str = "\n".join(context_parts) if context_parts else "New patient"
        
        return f"""
        Patient Context:
        {context_str}
        
        Current Query: {query}
        
        Provide personalized medical guidance considering the patient's history.
        """
```

### 2. API Endpoints for Memory Management

```python
# src/humansa/v2/endpoints/memory_endpoints.py

from quart import Blueprint, request, jsonify
from typing import Dict, Any
import logging

memory_bp = Blueprint('memory', __name__)
logger = logging.getLogger(__name__)

@memory_bp.route('/v2/humansa/memory/profile/<user_id>', methods=['GET'])
async def get_user_profile(user_id: str):
    """Get complete user profile with memory context"""
    try:
        memory_manager = request.app.memory_manager
        context = await memory_manager.get_comprehensive_user_context(
            user_id, 
            include_history=True
        )
        
        return jsonify({
            'status': 'success',
            'data': context
        })
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@memory_bp.route('/v2/humansa/memory/search', methods=['POST'])
async def search_memories():
    """Search user memories"""
    try:
        data = await request.json
        user_id = data.get('user_id')
        query = data.get('query')
        memory_types = data.get('memory_types', None)
        limit = data.get('limit', 10)
        
        memory_manager = request.app.memory_manager
        memories = await memory_manager.retrieve_relevant_memories(
            user_id=user_id,
            query=query,
            memory_types=memory_types,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'data': memories
        })
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@memory_bp.route('/v2/humansa/memory/update', methods=['POST'])
async def update_memory():
    """Manually update user memory"""
    try:
        data = await request.json
        user_id = data.get('user_id')
        memory_type = data.get('type')
        content = data.get('content')
        importance = data.get('importance', 0.5)
        
        memory_manager = request.app.memory_manager
        await memory_manager.store_memory_embedding(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            importance=importance
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Memory updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@memory_bp.route('/v2/humansa/memory/timeline/<user_id>', methods=['GET'])
async def get_user_timeline(user_id: str):
    """Get temporal timeline of user's medical journey"""
    try:
        memory_manager = request.app.memory_manager
        
        async with memory_manager.db_pool.acquire() as conn:
            # Get all temporal entities
            entities = await conn.fetch("""
                SELECT entity_type, entity_value, confidence, 
                       valid_from, valid_to, source, metadata
                FROM humansa_temporal_entities
                WHERE user_id = $1
                ORDER BY valid_from DESC
                LIMIT 100
            """, user_id)
            
            timeline = []
            for entity in entities:
                timeline.append({
                    'type': entity['entity_type'],
                    'value': entity['entity_value'],
                    'confidence': entity['confidence'],
                    'from': entity['valid_from'].isoformat(),
                    'to': entity['valid_to'].isoformat() if entity['valid_to'] else None,
                    'source': entity['source'],
                    'metadata': entity['metadata']
                })
            
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user_id,
                'timeline': timeline
            }
        })
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

### 3. Integration with Main Application

```python
# Update src/main.py

from src.humansa.v2.memory.enhanced_memory_manager import EnhancedMemoryManager
from src.humansa.v2.endpoints.memory_endpoints import memory_bp

async def initialize_memory_system(app):
    """Initialize enhanced memory system"""
    # Create memory manager
    memory_manager = EnhancedMemoryManager(
        db_pool=app.db_pool,
        openai_api_key=app.config['OPENAI_API_KEY']
    )
    
    # Initialize tables
    await memory_manager.initialize_enhanced_tables()
    
    # Store in app context
    app.memory_manager = memory_manager
    
    # Register blueprints
    app.register_blueprint(memory_bp)
    
    logger.info("Enhanced memory system initialized")

# Add to app initialization
@app.before_serving
async def startup():
    # ... existing initialization ...
    
    # Initialize memory system
    await initialize_memory_system(app)
```

### 4. Testing the Memory System

```python
# test_memory_system.py

import asyncio
import asyncpg
from datetime import datetime
from src.humansa.v2.memory.enhanced_memory_manager import (
    EnhancedMemoryManager, MemoryItem
)

async def test_memory_system():
    """Test the enhanced memory system"""
    
    # Setup
    db_pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='humansa_test'
    )
    
    memory_manager = EnhancedMemoryManager(
        db_pool=db_pool,
        openai_api_key='your-api-key'
    )
    
    await memory_manager.initialize_enhanced_tables()
    
    # Test 1: Extract and store entities
    test_conversation = [
        {"role": "user", "content": "I have diabetes and take metformin daily"},
        {"role": "assistant", "content": "I understand you have diabetes..."}
    ]
    
    entities = {
        "conditions": [
            MemoryItem(
                content="diabetes",
                type="condition",
                timestamp=datetime.utcnow(),
                confidence=0.95,
                source="conversation",
                metadata={}
            )
        ],
        "medications": [
            MemoryItem(
                content="metformin",
                type="medication",
                timestamp=datetime.utcnow(),
                confidence=0.95,
                source="conversation",
                metadata={"frequency": "daily"}
            )
        ]
    }
    
    await memory_manager.update_user_profile_intelligent("test_user_1", entities)
    
    # Test 2: Store memory embedding
    await memory_manager.store_memory_embedding(
        "test_user_1",
        "Patient has type 2 diabetes, well-controlled with metformin",
        "medical_summary",
        importance=0.8
    )
    
    # Test 3: Retrieve memories
    memories = await memory_manager.retrieve_relevant_memories(
        "test_user_1",
        "diabetes treatment",
        limit=5
    )
    
    print(f"Retrieved {len(memories)} relevant memories")
    
    # Test 4: Get comprehensive context
    context = await memory_manager.get_comprehensive_user_context("test_user_1")
    print(f"User context: {json.dumps(context, indent=2, default=str)}")
    
    # Cleanup
    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(test_memory_system())
```

## Next Steps

1. **Fine-tune Medical NER**: Train or fine-tune a medical entity recognition model
2. **Implement Conflict Resolution**: Advanced logic for handling contradictory information
3. **Add Privacy Controls**: User-facing APIs for data management
4. **Performance Optimization**: Caching strategies and query optimization
5. **Integration Testing**: Full integration with Humanza V2 agents

## Resources

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [LlamaIndex Memory Guide](https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores.html)
- [PostgreSQL JSONB Best Practices](https://www.postgresql.org/docs/current/datatype-json.html)
- [Medical NER Models](https://huggingface.co/models?search=medical%20ner)