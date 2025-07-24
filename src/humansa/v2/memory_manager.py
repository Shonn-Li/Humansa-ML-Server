"""
Patient memory management system for the Humansa agent.
Handles long-term patient information storage and retrieval.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.postgres.models import UserNote  # Reuse existing model
from src.chat.postgres.database import get_db_session


logger = logging.getLogger(__name__)


class PatientMemory:
    """
    Represents a patient's medical memory/history.
    """
    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.medical_history: List[Dict[str, Any]] = []
        self.medications: List[Dict[str, Any]] = []
        self.allergies: List[str] = []
        self.conditions: List[Dict[str, Any]] = []
        self.recent_interactions: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.emergency_contacts: List[Dict[str, Any]] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "patient_id": self.patient_id,
            "medical_history": self.medical_history,
            "medications": self.medications,
            "allergies": self.allergies,
            "conditions": self.conditions,
            "recent_interactions": self.recent_interactions[-10:],  # Keep last 10
            "preferences": self.preferences,
            "emergency_contacts": self.emergency_contacts,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientMemory":
        """Create from dictionary."""
        memory = cls(patient_id=data.get("patient_id", ""))
        memory.medical_history = data.get("medical_history", [])
        memory.medications = data.get("medications", [])
        memory.allergies = data.get("allergies", [])
        memory.conditions = data.get("conditions", [])
        memory.recent_interactions = data.get("recent_interactions", [])
        memory.preferences = data.get("preferences", {})
        memory.emergency_contacts = data.get("emergency_contacts", [])
        return memory


class MemoryManager:
    """
    Manages patient memory storage and retrieval.
    Uses the existing UserNote model for persistence.
    """
    
    def __init__(self, user_id: str = "humansa_system"):
        """
        Initialize memory manager.
        
        Args:
            user_id: System user ID for storing patient memories
        """
        self.user_id = user_id
        self._memory_cache: Dict[str, PatientMemory] = {}
        
    async def get_patient_memory(self, patient_id: str) -> PatientMemory:
        """
        Retrieve patient memory from storage.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            PatientMemory object
        """
        # Check cache first
        if patient_id in self._memory_cache:
            return self._memory_cache[patient_id]
            
        # Load from database
        async with get_db_session() as session:
            result = await session.execute(
                select(UserNote).where(
                    and_(
                        UserNote.user_id == self.user_id,
                        UserNote.title == f"patient_memory_{patient_id}"
                    )
                )
            )
            note = result.scalar_one_or_none()
            
            if note and note.content:
                try:
                    data = json.loads(note.content)
                    memory = PatientMemory.from_dict(data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse patient memory for {patient_id}")
                    memory = PatientMemory(patient_id)
            else:
                # Create new memory
                memory = PatientMemory(patient_id)
                
        # Cache the memory
        self._memory_cache[patient_id] = memory
        return memory
        
    async def update_patient_memory(
        self,
        patient_id: str,
        interaction_data: Dict[str, Any]
    ) -> None:
        """
        Update patient memory with new interaction data.
        
        Args:
            patient_id: Unique patient identifier
            interaction_data: Data from the current interaction
        """
        memory = await self.get_patient_memory(patient_id)
        
        # Add interaction to history
        memory.recent_interactions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "query": interaction_data.get("query"),
            "summary": self._summarize_interaction(interaction_data),
            "agent_results": interaction_data.get("agent_results", {})
        })
        
        # Extract and update medical information
        self._extract_medical_info(memory, interaction_data)
        
        # Save to database
        await self._save_memory(patient_id, memory)
        
    async def add_medical_record(
        self,
        patient_id: str,
        record_type: str,
        record_data: Dict[str, Any]
    ) -> None:
        """
        Add a specific medical record to patient memory.
        
        Args:
            patient_id: Unique patient identifier
            record_type: Type of record (medication, allergy, condition, etc.)
            record_data: Record details
        """
        memory = await self.get_patient_memory(patient_id)
        
        if record_type == "medication":
            memory.medications.append({
                **record_data,
                "added_date": datetime.utcnow().isoformat()
            })
        elif record_type == "allergy":
            if record_data.get("allergen") not in memory.allergies:
                memory.allergies.append(record_data.get("allergen"))
        elif record_type == "condition":
            memory.conditions.append({
                **record_data,
                "diagnosed_date": record_data.get("diagnosed_date", datetime.utcnow().isoformat())
            })
        elif record_type == "medical_history":
            memory.medical_history.append({
                **record_data,
                "recorded_date": datetime.utcnow().isoformat()
            })
            
        await self._save_memory(patient_id, memory)
        
    async def search_patient_history(
        self,
        patient_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search patient's medical history.
        
        Args:
            patient_id: Unique patient identifier
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of relevant history items
        """
        memory = await self.get_patient_memory(patient_id)
        
        # Simple keyword search - can be enhanced with embeddings
        query_lower = query.lower()
        results = []
        
        # Search through different memory components
        for interaction in memory.recent_interactions:
            if query_lower in str(interaction).lower():
                results.append({
                    "type": "interaction",
                    "data": interaction,
                    "relevance": 0.8
                })
                
        for med in memory.medications:
            if query_lower in str(med).lower():
                results.append({
                    "type": "medication",
                    "data": med,
                    "relevance": 0.9
                })
                
        for condition in memory.conditions:
            if query_lower in str(condition).lower():
                results.append({
                    "type": "condition",
                    "data": condition,
                    "relevance": 0.9
                })
                
        # Sort by relevance and return top results
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
        
    async def get_patient_summary(self, patient_id: str) -> Dict[str, Any]:
        """
        Get a summary of patient's medical information.
        
        Args:
            patient_id: Unique patient identifier
            
        Returns:
            Summary dictionary
        """
        memory = await self.get_patient_memory(patient_id)
        
        return {
            "patient_id": patient_id,
            "active_medications": len(memory.medications),
            "known_allergies": memory.allergies,
            "chronic_conditions": [
                c for c in memory.conditions
                if c.get("is_chronic", False)
            ],
            "last_interaction": (
                memory.recent_interactions[-1]["timestamp"]
                if memory.recent_interactions else None
            ),
            "total_interactions": len(memory.recent_interactions)
        }
        
    async def _save_memory(self, patient_id: str, memory: PatientMemory) -> None:
        """Save patient memory to database."""
        async with get_db_session() as session:
            # Check if note exists
            result = await session.execute(
                select(UserNote).where(
                    and_(
                        UserNote.user_id == self.user_id,
                        UserNote.title == f"patient_memory_{patient_id}"
                    )
                )
            )
            note = result.scalar_one_or_none()
            
            memory_data = json.dumps(memory.to_dict())
            
            if note:
                # Update existing
                note.content = memory_data
                note.updated_at = datetime.utcnow()
            else:
                # Create new
                note = UserNote(
                    user_id=self.user_id,
                    title=f"patient_memory_{patient_id}",
                    content=memory_data,
                    created_at=datetime.utcnow()
                )
                session.add(note)
                
            await session.commit()
            
    def _summarize_interaction(self, interaction_data: Dict[str, Any]) -> str:
        """Create a summary of the interaction."""
        synthesis = interaction_data.get("synthesis", {})
        if isinstance(synthesis, dict):
            return synthesis.get("summary", "Medical consultation")
        return "Medical consultation"
        
    def _extract_medical_info(
        self,
        memory: PatientMemory,
        interaction_data: Dict[str, Any]
    ) -> None:
        """
        Extract medical information from interaction data.
        This is a placeholder - should use NLP/LLM for better extraction.
        """
        # TODO: Implement intelligent extraction of medical information
        # from agent results and synthesis
        pass