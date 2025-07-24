from typing import Dict, Any, List, Optional
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
import json


async def check_drug_interactions(medications: List[str]) -> Dict[str, Any]:
    """Check for potential drug interactions."""
    # This would integrate with a drug interaction database
    return {
        "checked_medications": medications,
        "interactions_found": False,
        "severity": "none",
        "recommendations": ["Always consult with your healthcare provider before changing medications"]
    }


async def get_medication_info(medication_name: str) -> Dict[str, Any]:
    """Get detailed information about a medication."""
    # Placeholder for medication database lookup
    return {
        "medication": medication_name,
        "generic_name": medication_name.lower(),
        "drug_class": "Requires database lookup",
        "common_uses": ["Information requires medical database access"],
        "common_side_effects": ["Consult medication guide or pharmacist"],
        "warnings": ["Always follow prescriber instructions"],
        "note": "For detailed medication information, consult your pharmacist or prescriber"
    }


async def suggest_medication_schedule(medications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Suggest optimal medication scheduling."""
    return {
        "schedule_suggestions": [
            {
                "medication": med.get("name", "Unknown"),
                "suggested_times": ["As prescribed by your doctor"],
                "with_food": "Follow prescription instructions"
            }
            for med in medications
        ],
        "general_tips": [
            "Take medications at the same time each day",
            "Set reminders on your phone",
            "Use a pill organizer",
            "Keep a medication log"
        ]
    }


class MedicationAgent(BaseHumansaAgent):
    """Specialized agent for medication-related queries and management."""
    
    def __init__(self, llm, **kwargs):
        tools = [
            FunctionTool.from_defaults(
                fn=check_drug_interactions,
                name="check_interactions",
                description="Check for potential drug interactions"
            ),
            FunctionTool.from_defaults(
                fn=get_medication_info,
                name="medication_info",
                description="Get information about specific medications"
            ),
            FunctionTool.from_defaults(
                fn=suggest_medication_schedule,
                name="medication_schedule",
                description="Suggest medication scheduling optimization"
            )
        ]
        
        super().__init__(
            agent_id="medication_agent",
            agent_name="Medication Specialist",
            description="Handles medication queries, interactions, and management",
            llm=llm,
            tools=tools,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """You are a medication specialist assistant for Humansa Health.

Your role is to:
1. Provide medication information and education
2. Check for potential drug interactions
3. Help with medication scheduling and adherence
4. Answer questions about side effects and warnings
5. Guide patients on proper medication use

Critical guidelines:
- NEVER recommend changing prescribed medications
- Always defer to prescribing physicians for dosage changes
- Emphasize the importance of following prescription instructions
- Flag potential serious interactions for immediate medical review
- Promote medication adherence and proper storage

When discussing medications:
- Use both brand and generic names when known
- Explain common side effects clearly
- Emphasize the importance of completing prescribed courses
- Suggest strategies for remembering medications
- Address cost concerns with generic alternatives info

Safety priorities:
- Never suggest stopping medications without medical consultation
- Highlight black box warnings when relevant
- Stress the importance of informing all providers about all medications
- Include over-the-counter and supplement considerations"""
    
    def get_capabilities(self) -> List[str]:
        return [
            "Medication information lookup",
            "Drug interaction checking",
            "Side effect information",
            "Medication scheduling assistance",
            "Adherence strategies",
            "Generic alternative information",
            "Storage recommendations"
        ]
    
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """Determine if this agent should handle the query."""
        query_lower = query.lower()
        
        # High confidence for medication-related keywords
        medication_keywords = [
            "medication", "medicine", "drug", "prescription", "pill",
            "tablet", "dose", "dosage", "mg", "ml", "capsule",
            "side effect", "interaction", "generic", "brand name"
        ]
        
        # Specific medication-related phrases
        medication_phrases = [
            "take with food", "how often", "when to take",
            "can i take", "is it safe", "mix with",
            "forgot to take", "missed dose", "ran out of",
            "refill", "pharmacy"
        ]
        
        # Check for matches
        keyword_score = sum(0.2 for kw in medication_keywords if kw in query_lower)
        phrase_score = sum(0.3 for phrase in medication_phrases if phrase in query_lower)
        
        # Check context for current medications
        if context.get("current_medications"):
            context_score = 0.2
            # Higher score if query mentions a current medication
            for med in context["current_medications"]:
                if med.get("name", "").lower() in query_lower:
                    context_score = 0.4
                    break
        else:
            context_score = 0
        
        # Calculate total score
        total_score = min(keyword_score + phrase_score + context_score, 0.95)
        
        # Lower score if asking about appointments or general symptoms
        if any(word in query_lower for word in ["appointment", "book", "schedule visit", "see doctor"]):
            total_score *= 0.5
            
        return total_score