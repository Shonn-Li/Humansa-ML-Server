from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class UnifiedContext:
    """Unified context that gets passed between agents."""
    user_id: str
    conversation_id: str
    query: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Patient information
    patient_profile: Dict[str, Any] = field(default_factory=dict)
    medical_history: List[Dict[str, Any]] = field(default_factory=list)
    current_medications: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    
    # Conversation context
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_symptoms: List[str] = field(default_factory=list)
    
    # Agent processing metadata
    agents_invoked: List[str] = field(default_factory=list)
    agent_responses: Dict[str, Any] = field(default_factory=dict)
    
    # Document/attachment context
    attached_documents: List[Dict[str, Any]] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    
    # Appointment context
    appointment_preferences: Dict[str, Any] = field(default_factory=dict)
    selected_doctor: Optional[Dict[str, Any]] = None
    selected_slot: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "patient_profile": self.patient_profile,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies,
            "conversation_history": self.conversation_history,
            "current_symptoms": self.current_symptoms,
            "agents_invoked": self.agents_invoked,
            "agent_responses": self.agent_responses,
            "attached_documents": self.attached_documents,
            "extracted_data": self.extracted_data,
            "appointment_preferences": self.appointment_preferences,
            "selected_doctor": self.selected_doctor,
            "selected_slot": self.selected_slot
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedContext":
        """Create context from dictionary."""
        # Handle timestamp conversion
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            
        return cls(**data)
    
    def add_agent_response(self, agent_id: str, response: Any):
        """Add an agent's response to the context."""
        if agent_id not in self.agents_invoked:
            self.agents_invoked.append(agent_id)
        self.agent_responses[agent_id] = response
        
    def get_agent_response(self, agent_id: str) -> Optional[Any]:
        """Get a specific agent's response."""
        return self.agent_responses.get(agent_id)
    
    def add_symptom(self, symptom: str):
        """Add a symptom to current symptoms."""
        if symptom not in self.current_symptoms:
            self.current_symptoms.append(symptom)
            
    def add_document(self, doc_info: Dict[str, Any]):
        """Add document information."""
        self.attached_documents.append({
            "timestamp": datetime.utcnow().isoformat(),
            **doc_info
        })
        
    def get_relevant_medical_context(self) -> str:
        """Get formatted medical context for agents."""
        context_parts = []
        
        if self.patient_profile:
            context_parts.append(f"Patient: {self.patient_profile.get('name', 'Unknown')}")
            if age := self.patient_profile.get('age'):
                context_parts.append(f"Age: {age}")
                
        if self.medical_history:
            conditions = [h.get('condition') for h in self.medical_history if h.get('condition')]
            if conditions:
                context_parts.append(f"Medical History: {', '.join(conditions)}")
                
        if self.current_medications:
            meds = [m.get('name') for m in self.current_medications if m.get('name')]
            if meds:
                context_parts.append(f"Current Medications: {', '.join(meds)}")
                
        if self.allergies:
            context_parts.append(f"Allergies: {', '.join(self.allergies)}")
            
        if self.current_symptoms:
            context_parts.append(f"Current Symptoms: {', '.join(self.current_symptoms)}")
            
        return "\n".join(context_parts) if context_parts else "No medical context available"
    
    def get_conversation_summary(self, last_n: int = 3) -> str:
        """Get summary of recent conversation."""
        if not self.conversation_history:
            return ""
            
        recent = self.conversation_history[-last_n:]
        summary_parts = []
        
        for entry in recent:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            summary_parts.append(f"{role.capitalize()}: {content}")
            
        return "\n".join(summary_parts)


class ContextManager:
    """Manages context flow between agents and components."""
    
    def __init__(self):
        self._contexts: Dict[str, UnifiedContext] = {}
        
    def create_context(
        self,
        user_id: str,
        query: str,
        conversation_id: Optional[str] = None
    ) -> UnifiedContext:
        """Create a new context for a conversation."""
        if not conversation_id:
            conversation_id = f"conv_{datetime.utcnow().timestamp()}"
            
        context = UnifiedContext(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query
        )
        
        self._contexts[conversation_id] = context
        return context
    
    def get_context(self, conversation_id: str) -> Optional[UnifiedContext]:
        """Retrieve a context by conversation ID."""
        return self._contexts.get(conversation_id)
    
    def update_context(self, conversation_id: str, updates: Dict[str, Any]):
        """Update an existing context."""
        if context := self._contexts.get(conversation_id):
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
                    
    def merge_contexts(
        self,
        primary_id: str,
        secondary_id: str
    ) -> Optional[UnifiedContext]:
        """Merge two contexts (useful for follow-up conversations)."""
        primary = self._contexts.get(primary_id)
        secondary = self._contexts.get(secondary_id)
        
        if not primary or not secondary:
            return None
            
        # Merge conversation history
        primary.conversation_history.extend(secondary.conversation_history)
        
        # Merge symptoms
        for symptom in secondary.current_symptoms:
            primary.add_symptom(symptom)
            
        # Merge agent responses
        primary.agent_responses.update(secondary.agent_responses)
        primary.agents_invoked.extend(
            [a for a in secondary.agents_invoked if a not in primary.agents_invoked]
        )
        
        # Remove secondary context
        del self._contexts[secondary_id]
        
        return primary
    
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Remove contexts older than specified hours."""
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for conv_id, context in self._contexts.items():
            if context.timestamp.timestamp() < cutoff:
                to_remove.append(conv_id)
                
        for conv_id in to_remove:
            del self._contexts[conv_id]