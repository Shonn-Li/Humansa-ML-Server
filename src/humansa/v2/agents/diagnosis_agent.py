from typing import Dict, Any, List
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
import json


async def analyze_symptoms(symptoms: List[str], patient_context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze symptoms and provide potential conditions to investigate."""
    # This would integrate with a medical knowledge base
    # For now, return structured analysis
    return {
        "symptom_analysis": {
            "primary_symptoms": symptoms[:3] if len(symptoms) > 3 else symptoms,
            "duration": "Not specified",
            "severity": "To be assessed"
        },
        "recommended_specialists": [],
        "recommended_tests": [],
        "urgency_level": "routine"
    }


async def get_differential_diagnosis(symptoms: List[str], history: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate differential diagnosis possibilities."""
    # Placeholder for medical reasoning
    return [
        {
            "condition": "Requires professional evaluation",
            "probability": "N/A",
            "reasoning": "Symptoms should be evaluated by a healthcare provider",
            "next_steps": ["Schedule consultation", "Prepare symptom diary"]
        }
    ]


class DiagnosisAgent(BaseHumansaAgent):
    """Specialized agent for symptom analysis and diagnostic support."""
    
    def __init__(self, llm, **kwargs):
        tools = [
            FunctionTool.from_defaults(
                fn=analyze_symptoms,
                name="analyze_symptoms",
                description="Analyze patient symptoms and suggest next steps"
            ),
            FunctionTool.from_defaults(
                fn=get_differential_diagnosis,
                name="differential_diagnosis",
                description="Generate potential differential diagnoses"
            )
        ]
        
        super().__init__(
            agent_id="diagnosis_agent",
            agent_name="Diagnostic Assistant",
            description="Analyzes symptoms and provides diagnostic guidance",
            llm=llm,
            tools=tools,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """You are a medical diagnostic assistant specializing in symptom analysis.

Your role is to:
1. Carefully analyze patient-reported symptoms
2. Consider medical history and risk factors
3. Suggest appropriate medical specialists
4. Recommend relevant diagnostic tests
5. Assess urgency levels appropriately

Critical guidelines:
- NEVER provide definitive diagnoses
- Always emphasize the need for professional medical evaluation
- Flag urgent symptoms that require immediate care
- Consider differential diagnoses systematically
- Ask clarifying questions about symptom details

When analyzing symptoms:
- Duration and onset
- Severity and progression
- Associated symptoms
- Aggravating/relieving factors
- Impact on daily activities

Safety priorities:
- Identify red flags requiring emergency care
- Err on the side of caution
- Clearly communicate uncertainty
- Document all relevant information"""
    
    def get_capabilities(self) -> List[str]:
        return [
            "Symptom analysis and interpretation",
            "Medical history consideration",
            "Specialist recommendations",
            "Diagnostic test suggestions",
            "Urgency assessment",
            "Differential diagnosis support",
            "Red flag identification"
        ]
    
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """Determine if this agent should handle the query."""
        query_lower = query.lower()
        
        # High confidence for symptom-related queries
        symptom_keywords = [
            "symptom", "symptoms", "feeling", "pain", "ache",
            "discomfort", "problem", "issue", "condition",
            "diagnosis", "what could", "might be", "suffering from",
            "experiencing", "worried about", "concerned about"
        ]
        
        diagnostic_phrases = [
            "what is wrong", "what's wrong", "what could it be",
            "what might this be", "should i be worried",
            "is this serious", "do i need to see"
        ]
        
        # Check for matches
        keyword_score = sum(0.15 for kw in symptom_keywords if kw in query_lower)
        phrase_score = sum(0.25 for phrase in diagnostic_phrases if phrase in query_lower)
        
        # Check context for existing symptoms
        context_score = 0.3 if context.get("current_symptoms") else 0
        
        # Calculate total score
        total_score = min(keyword_score + phrase_score + context_score, 0.95)
        
        # Lower score for medication or appointment queries
        if any(word in query_lower for word in ["medication", "prescription", "appointment", "book", "schedule"]):
            total_score *= 0.6
            
        return total_score
    
    async def process_query(self, query: str, context: Dict[str, Any], stream: bool = True):
        """Process diagnostic queries with enhanced context."""
        # Add medical context to query
        medical_context = context.get("patient_profile", {})
        if medical_context.get("medical_history") or context.get("current_symptoms"):
            enhanced_context = {
                **context,
                "analysis_context": {
                    "query": query,
                    "medical_history": medical_context.get("medical_history", []),
                    "current_medications": medical_context.get("current_medications", []),
                    "allergies": medical_context.get("allergies", []),
                    "symptoms": context.get("current_symptoms", [])
                }
            }
        else:
            enhanced_context = context
            
        async for chunk in super().process_query(query, enhanced_context, stream):
            yield chunk