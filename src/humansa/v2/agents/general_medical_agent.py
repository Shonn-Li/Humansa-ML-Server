from typing import Dict, Any, List
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
from ..tools.medical_tools import (
    search_doctors,
    check_doctor_availability,
    get_service_pricing,
    get_clinic_info
)
import re


class GeneralMedicalAgent(BaseHumansaAgent):
    """General medical consultation agent for initial patient interactions."""
    
    def __init__(self, llm, **kwargs):
        # Define tools for general medical consultation
        tools = [
            FunctionTool.from_defaults(
                fn=search_doctors,
                name="search_doctors",
                description="Search for doctors by specialty, name, or location"
            ),
            FunctionTool.from_defaults(
                fn=check_doctor_availability,
                name="check_availability",
                description="Check doctor availability for specific dates"
            ),
            FunctionTool.from_defaults(
                fn=get_service_pricing,
                name="get_pricing",
                description="Get pricing information for medical services"
            ),
            FunctionTool.from_defaults(
                fn=get_clinic_info,
                name="get_clinic_info",
                description="Get information about clinics and facilities"
            )
        ]
        
        super().__init__(
            agent_id="general_medical",
            agent_name="General Medical Consultant",
            description="Handles general medical inquiries, doctor searches, and initial consultations",
            llm=llm,
            tools=tools,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """You are a professional medical consultation assistant for Humansa Health.
        
Your role is to:
1. Provide initial medical guidance and information
2. Help patients find appropriate doctors and specialists
3. Answer questions about services, pricing, and availability
4. Collect relevant symptoms and medical history
5. Guide patients to appropriate care pathways

Important guidelines:
- Always maintain a professional, empathetic tone
- Never provide definitive diagnoses - only guidance
- Encourage patients to see healthcare providers for serious concerns
- Collect detailed information about symptoms when relevant
- Respect patient privacy and confidentiality

When searching for doctors:
- Consider the patient's specific needs and preferences
- Provide relevant information about qualifications and specialties
- Help with appointment scheduling when requested

Remember: You are a consultation assistant, not a replacement for professional medical care."""
    
    def get_capabilities(self) -> List[str]:
        return [
            "General medical consultation",
            "Doctor and specialist search",
            "Appointment availability checking",
            "Service pricing information",
            "Clinic and facility information",
            "Initial symptom assessment",
            "Healthcare navigation guidance"
        ]
    
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """Determine if this agent should handle the query."""
        query_lower = query.lower()
        
        # High confidence for general medical queries
        general_keywords = [
            "doctor", "appointment", "clinic", "hospital", "medical",
            "health", "symptom", "feeling", "pain", "check-up",
            "consultation", "specialist", "general practitioner", "gp"
        ]
        
        # Check for general medical keywords
        keyword_matches = sum(1 for keyword in general_keywords if keyword in query_lower)
        
        # Lower confidence if query is about specific medical conditions
        specific_conditions = [
            "prescription", "medication", "drug", "dosage",
            "diagnosis", "test result", "lab report",
            "emergency", "urgent", "immediate"
        ]
        
        specific_matches = sum(1 for condition in specific_conditions if condition in query_lower)
        
        # Calculate confidence score
        if keyword_matches > 0:
            base_score = min(0.5 + (keyword_matches * 0.1), 0.9)
            # Reduce score if specific conditions are mentioned
            if specific_matches > 0:
                base_score *= 0.7
            return base_score
        
        # Default confidence for general queries
        return 0.3
    
    async def process_query(self, query: str, context: Dict[str, Any], stream: bool = True):
        """Process query with symptom extraction."""
        # Extract symptoms from query if present
        symptoms = self._extract_symptoms(query)
        if symptoms and "current_symptoms" in context:
            context["current_symptoms"].extend(symptoms)
        
        # Process with base implementation
        async for chunk in super().process_query(query, context, stream):
            yield chunk
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract potential symptoms from text."""
        symptom_patterns = [
            r"(?:I have|I'm experiencing|I feel|feeling) (\w+(?:\s+\w+)*)",
            r"(?:pain in|ache in|discomfort in) (?:my\s+)?(\w+(?:\s+\w+)*)",
            r"(?:my\s+)?(\w+(?:\s+\w+)*) (?:hurts|aches|is sore)",
        ]
        
        symptoms = []
        for pattern in symptom_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            symptoms.extend(matches)
        
        # Clean and deduplicate
        cleaned_symptoms = []
        for symptom in symptoms:
            cleaned = symptom.strip().lower()
            if cleaned and len(cleaned) > 2 and cleaned not in cleaned_symptoms:
                cleaned_symptoms.append(cleaned)
        
        return cleaned_symptoms[:5]  # Limit to 5 symptoms