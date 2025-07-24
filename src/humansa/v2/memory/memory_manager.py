from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncpg
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.storage.chat_store import SimpleChatStore
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages persistent patient memory and conversation history."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._memory_cache: Dict[str, ChatMemoryBuffer] = {}
        
    async def initialize_tables(self):
        """Create necessary database tables for patient memory."""
        async with self.db_pool.acquire() as conn:
            # Create patient profile table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS humansa_patient_profile (
                    user_id TEXT PRIMARY KEY,
                    profile_data JSONB NOT NULL DEFAULT '{}',
                    medical_history JSONB DEFAULT '[]',
                    preferences JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create conversation history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS humansa_conversation_history (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES humansa_patient_profile(user_id)
                )
            """)
            
            # Create index for faster queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_user_id 
                ON humansa_conversation_history(user_id, created_at DESC)
            """)
            
    async def get_or_create_patient_profile(self, user_id: str) -> Dict[str, Any]:
        """Get or create a patient profile."""
        async with self.db_pool.acquire() as conn:
            # Try to get existing profile
            row = await conn.fetchrow(
                "SELECT * FROM humansa_patient_profile WHERE user_id = $1",
                user_id
            )
            
            if row:
                return {
                    "user_id": row["user_id"],
                    "profile_data": row["profile_data"],
                    "medical_history": row["medical_history"],
                    "preferences": row["preferences"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            
            # Create new profile
            await conn.execute(
                """
                INSERT INTO humansa_patient_profile (user_id) 
                VALUES ($1)
                """,
                user_id
            )
            
            return {
                "user_id": user_id,
                "profile_data": {},
                "medical_history": [],
                "preferences": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
    
    async def update_patient_profile(
        self,
        user_id: str,
        profile_data: Optional[Dict[str, Any]] = None,
        medical_history: Optional[List[Dict[str, Any]]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ):
        """Update patient profile data."""
        updates = []
        params = [user_id]
        param_count = 1
        
        if profile_data is not None:
            param_count += 1
            updates.append(f"profile_data = ${param_count}")
            params.append(json.dumps(profile_data))
            
        if medical_history is not None:
            param_count += 1
            updates.append(f"medical_history = ${param_count}")
            params.append(json.dumps(medical_history))
            
        if preferences is not None:
            param_count += 1
            updates.append(f"preferences = ${param_count}")
            params.append(json.dumps(preferences))
            
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"""
                UPDATE humansa_patient_profile 
                SET {', '.join(updates)}
                WHERE user_id = $1
            """
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, *params)
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        query = """
            SELECT * FROM humansa_conversation_history 
            WHERE user_id = $1
        """
        params = [user_id]
        
        if conversation_id:
            query += " AND conversation_id = $2"
            params.append(conversation_id)
            
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": row["metadata"],
                "created_at": row["created_at"]
            }
            for row in reversed(rows)  # Return in chronological order
        ]
    
    async def update_conversation(
        self,
        user_id: str,
        query: str,
        response: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update conversation history."""
        if not conversation_id:
            conversation_id = f"conv_{datetime.utcnow().isoformat()}"
            
        async with self.db_pool.acquire() as conn:
            # Add user message
            await conn.execute(
                """
                INSERT INTO humansa_conversation_history 
                (user_id, conversation_id, role, content, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, conversation_id, "user", query, json.dumps(metadata or {})
            )
            
            # Add assistant response
            await conn.execute(
                """
                INSERT INTO humansa_conversation_history 
                (user_id, conversation_id, role, content, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, conversation_id, "assistant", response, json.dumps(metadata or {})
            )
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get complete user context including profile and recent history."""
        # Get patient profile
        profile = await self.get_or_create_patient_profile(user_id)
        
        # Get recent conversation history
        history = await self.get_conversation_history(user_id, limit=5)
        
        # Build context
        context = {
            "user_id": user_id,
            "patient_profile": profile,
            "conversation_history": self._format_conversation_history(history),
            "last_interaction": history[-1]["created_at"] if history else None
        }
        
        return context
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for context."""
        if not history:
            return ""
            
        formatted = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
            
        return "\n".join(formatted)
    
    def get_memory_buffer(self, user_id: str) -> ChatMemoryBuffer:
        """Get or create a memory buffer for streaming conversations."""
        if user_id not in self._memory_cache:
            self._memory_cache[user_id] = ChatMemoryBuffer.from_defaults(
                chat_store=SimpleChatStore(),
                token_limit=4000
            )
            
        return self._memory_cache[user_id]
    
    async def extract_medical_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities from text for profile updates."""
        # This would integrate with a medical NER model
        # For now, return placeholder
        return {
            "conditions": [],
            "medications": [],
            "allergies": [],
            "symptoms": []
        }