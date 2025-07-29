"""
Mem0 Integration for Humansa V2
Bridges the old MemoryManager interface with the new Mem0 system
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Mem0MemoryManagerAdapter:
    """
    Adapter that makes Mem0 work with the existing MemoryManager interface
    used by Humansa v2 orchestrator and workflows.
    """
    
    def __init__(self, db_pool, mem0_manager=None):
        """Initialize adapter with database pool and optional Mem0 manager."""
        self.db_pool = db_pool
        self._mem0_manager = mem0_manager
        self._initialized = False
        
    @property
    def mem0_manager(self):
        """Get Mem0 manager instance."""
        if self._mem0_manager is None:
            from humansa.memory.mem0_manager import Mem0Manager
            self._mem0_manager = Mem0Manager.get_instance()
        return self._mem0_manager
        
    async def initialize_tables(self):
        """Initialize tables - compatibility method."""
        # Mem0 handles its own table creation
        if not self.mem0_manager.initialized:
            success = await self.mem0_manager.initialize()
            if not success:
                logger.warning("Mem0 initialization failed - falling back to basic memory")
        self._initialized = True
        
    async def get_patient_memory(self, patient_id: str) -> Dict[str, Any]:
        """Get patient memory using Mem0."""
        if not self.mem0_manager.initialized:
            return {"memories": [], "summary": "No memory available"}
            
        try:
            # Get all memories for the patient
            memory_user_id = self.mem0_manager.get_memory_user_id(patient_id)
            memories = await self._get_all_memories_async(memory_user_id)
            
            # Build patient memory structure
            patient_memory = {
                "patient_id": patient_id,
                "memories": memories,
                "medical_history": [],
                "preferences": [],
                "appointments": [],
                "medications": [],
                "allergies": []
            }
            
            # Extract categorized information from memories
            for memory in memories:
                memory_text = str(memory.get("memory", "")).lower()
                
                # Categorize memories
                if any(word in memory_text for word in ["medication", "drug", "prescription"]):
                    patient_memory["medications"].append(memory)
                elif any(word in memory_text for word in ["allergy", "allergic"]):
                    patient_memory["allergies"].append(memory)
                elif any(word in memory_text for word in ["appointment", "schedule", "booking"]):
                    patient_memory["appointments"].append(memory)
                elif any(word in memory_text for word in ["prefer", "like", "want"]):
                    patient_memory["preferences"].append(memory)
                else:
                    patient_memory["medical_history"].append(memory)
                    
            return patient_memory
            
        except Exception as e:
            logger.error(f"Error getting patient memory from Mem0: {e}")
            return {"memories": [], "error": str(e)}
            
    async def update_patient_memory(
        self,
        patient_id: str,
        interaction_data: Dict[str, Any]
    ) -> bool:
        """Update patient memory with new interaction data."""
        if not self.mem0_manager.initialized:
            return False
            
        try:
            # Extract messages from interaction data
            messages = []
            
            # Add the original query
            if "query" in interaction_data:
                messages.append({
                    "role": "user",
                    "content": interaction_data["query"]
                })
                
            # Add synthesis/response
            if "synthesis" in interaction_data:
                synthesis = interaction_data["synthesis"]
                response_content = synthesis.get("summary", "")
                if synthesis.get("key_findings"):
                    response_content += "\n\nKey findings: " + ", ".join(synthesis["key_findings"])
                if synthesis.get("recommendations"):
                    response_content += "\n\nRecommendations: " + ", ".join(synthesis["recommendations"])
                    
                messages.append({
                    "role": "assistant",
                    "content": response_content
                })
                
            # Add conversation to Mem0
            if messages:
                metadata = {
                    "source": "humansa_v2",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_results": list(interaction_data.get("agent_results", {}).keys())
                }
                
                success = await self.mem0_manager.add_conversation(
                    user_id=patient_id,
                    messages=messages,
                    metadata=metadata
                )
                
                return success
                
        except Exception as e:
            logger.error(f"Error updating patient memory in Mem0: {e}")
            return False
            
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from Mem0."""
        if not self.mem0_manager.initialized:
            return {"user_id": user_id}
            
        try:
            context = await self.mem0_manager.get_user_context(user_id)
            return context
        except Exception as e:
            logger.error(f"Error getting user context from Mem0: {e}")
            return {"user_id": user_id, "error": str(e)}
            
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search user memories using Mem0."""
        if not self.mem0_manager.initialized:
            return []
            
        try:
            memories = await self.mem0_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
            return memories
        except Exception as e:
            logger.error(f"Error searching memories in Mem0: {e}")
            return []
            
    async def get_or_create_patient_profile(self, user_id: str) -> Dict[str, Any]:
        """Get or create patient profile - uses Mem0 context."""
        context = await self.get_user_context(user_id)
        
        # Build profile from context
        profile = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "memory_count": context.get("memory_count", 0),
            "recent_interactions": context.get("recent_memories", [])
        }
        
        return profile
        
    async def update_patient_profile(
        self,
        user_id: str,
        profile_data: Optional[Dict] = None,
        medical_history: Optional[Dict] = None,
        preferences: Optional[Dict] = None
    ) -> bool:
        """Update patient profile by adding to Mem0 memories."""
        if not self.mem0_manager.initialized:
            return False
            
        try:
            messages = []
            
            # Convert profile updates to conversational format
            if profile_data:
                content = "Patient profile update: "
                content += ", ".join([f"{k}: {v}" for k, v in profile_data.items()])
                messages.append({
                    "role": "user",
                    "content": content
                })
                messages.append({
                    "role": "assistant",
                    "content": "I've updated your profile information."
                })
                
            if medical_history:
                content = "Medical history update: "
                content += ", ".join([f"{k}: {v}" for k, v in medical_history.items()])
                messages.append({
                    "role": "user",
                    "content": content
                })
                messages.append({
                    "role": "assistant",
                    "content": "I've recorded your medical history updates."
                })
                
            if preferences:
                content = "Preferences update: "
                content += ", ".join([f"{k}: {v}" for k, v in preferences.items()])
                messages.append({
                    "role": "user",
                    "content": content
                })
                messages.append({
                    "role": "assistant",
                    "content": "I've noted your preferences."
                })
                
            # Add to Mem0
            if messages:
                metadata = {
                    "source": "profile_update",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                success = await self.mem0_manager.add_conversation(
                    user_id=user_id,
                    messages=messages,
                    metadata=metadata
                )
                
                return success
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating patient profile in Mem0: {e}")
            return False
            
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history from Mem0 memories."""
        if not self.mem0_manager.initialized:
            return []
            
        try:
            # Get all memories
            memory_user_id = self.mem0_manager.get_memory_user_id(user_id)
            memories = await self._get_all_memories_async(memory_user_id)
            
            # Sort by creation time and limit
            sorted_memories = sorted(
                memories,
                key=lambda m: m.get("created_at", ""),
                reverse=True
            )[:limit]
            
            return sorted_memories
            
        except Exception as e:
            logger.error(f"Error getting conversation history from Mem0: {e}")
            return []
            
    async def update_conversation(
        self,
        user_id: str,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update conversation - compatible with v2 orchestrator."""
        if not self.mem0_manager.initialized:
            return False
            
        try:
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response}
            ]
            
            # Add conversation to Mem0
            success = await self.mem0_manager.add_conversation(
                user_id=user_id,
                messages=messages,
                metadata=metadata
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating conversation in Mem0: {e}")
            return False
            
    async def add_conversation(
        self,
        user_id: str,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add conversation - passes string user_id directly."""
        return await self.update_conversation(
            user_id=user_id,
            query=query,
            response=response,
            metadata=metadata
        )
            
    async def _get_all_memories_async(self, memory_user_id: str) -> List[Dict[str, Any]]:
        """Get all memories asynchronously."""
        import asyncio
        loop = asyncio.get_event_loop()
        memories = await loop.run_in_executor(
            None,
            lambda: self.mem0_manager.memory.get_all(user_id=memory_user_id)
        )
        return memories or []