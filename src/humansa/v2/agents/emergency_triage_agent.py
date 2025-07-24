from typing import Dict, Any, List, Tuple
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
from datetime import datetime


async def assess_emergency_symptoms(symptoms: List[str]) -> Dict[str, Any]:
    """Assess symptoms for emergency severity."""
    # Red flag symptoms that require immediate attention
    emergency_symptoms = [
        "chest pain", "difficulty breathing", "severe bleeding",
        "unconscious", "stroke", "heart attack", "severe allergic",
        "anaphylaxis", "seizure", "severe burn", "head injury"
    ]
    
    warning_symptoms = [
        "high fever", "persistent vomiting", "severe pain",
        "confusion", "weakness", "dizziness", "fainting",
        "severe headache", "vision changes", "numbness"
    ]
    
    symptoms_lower = [s.lower() for s in symptoms]
    
    # Check for emergency symptoms
    emergency_matches = [s for s in emergency_symptoms if any(s in symptom for symptom in symptoms_lower)]
    warning_matches = [s for s in warning_symptoms if any(s in symptom for symptom in symptoms_lower)]
    
    if emergency_matches:
        return {
            "severity": "EMERGENCY",
            "action_required": "CALL 911 IMMEDIATELY",
            "identified_concerns": emergency_matches,
            "instructions": [
                "Call emergency services (911) immediately",
                "Do not drive yourself to the hospital",
                "Stay calm and follow dispatcher instructions",
                "Have someone stay with you if possible"
            ]
        }
    elif warning_matches:
        return {
            "severity": "URGENT",
            "action_required": "Seek immediate medical care",
            "identified_concerns": warning_matches,
            "instructions": [
                "Visit emergency room or urgent care immediately",
                "Do not wait for appointment",
                "Bring list of current medications",
                "Have someone drive you if possible"
            ]
        }
    else:
        return {
            "severity": "NON-URGENT",
            "action_required": "Schedule appointment with healthcare provider",
            "identified_concerns": [],
            "instructions": [
                "Monitor symptoms",
                "Schedule appointment with your doctor",
                "Keep symptom diary",
                "Seek care if symptoms worsen"
            ]
        }


async def get_nearest_emergency_facilities(location: str = "Singapore") -> List[Dict[str, Any]]:
    """Get nearest emergency facilities."""
    # This would integrate with a real facility database
    return [
        {
            "name": "Singapore General Hospital Emergency",
            "type": "Emergency Department",
            "address": "Outram Road, Singapore",
            "phone": "6222 3322",
            "wait_time": "Variable",
            "distance": "Depends on location"
        },
        {
            "name": "National University Hospital Emergency",
            "type": "Emergency Department", 
            "address": "Kent Ridge, Singapore",
            "phone": "6779 5555",
            "wait_time": "Variable",
            "distance": "Depends on location"
        }
    ]


class EmergencyTriageAgent(BaseHumansaAgent):
    """Specialized agent for emergency assessment and triage."""
    
    def __init__(self, llm, **kwargs):
        tools = [
            FunctionTool.from_defaults(
                fn=assess_emergency_symptoms,
                name="assess_emergency",
                description="Assess symptoms for emergency severity"
            ),
            FunctionTool.from_defaults(
                fn=get_nearest_emergency_facilities,
                name="emergency_facilities",
                description="Find nearest emergency facilities"
            )
        ]
        
        super().__init__(
            agent_id="emergency_triage",
            agent_name="Emergency Triage Specialist",
            description="Assesses urgent symptoms and guides emergency care",
            llm=llm,
            tools=tools,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """You are an emergency triage specialist for Humansa Health.

CRITICAL ROLE: Identify and respond to medical emergencies appropriately.

Your responsibilities:
1. Rapidly assess symptom severity
2. Identify red flag symptoms requiring immediate care
3. Provide clear emergency instructions
4. Direct to appropriate level of care
5. Never delay emergency response

EMERGENCY SYMPTOMS requiring immediate 911 call:
- Chest pain or pressure
- Difficulty breathing or shortness of breath
- Severe bleeding that won't stop
- Loss of consciousness
- Signs of stroke (FAST: Face drooping, Arm weakness, Speech difficulty, Time to call 911)
- Severe allergic reaction (anaphylaxis)
- Severe burns
- Head injuries with confusion
- Seizures
- Sudden severe pain

URGENT SYMPTOMS requiring immediate medical care:
- High fever (>103°F/39.4°C) or fever with stiff neck
- Persistent vomiting or diarrhea
- Severe headache unlike any before
- Vision changes or eye injuries
- Deep cuts or wounds
- Possible broken bones
- Severe abdominal pain

Guidelines:
- ALWAYS err on the side of caution
- Never downplay serious symptoms
- Be direct and clear in emergency situations
- Provide specific actionable instructions
- Document time of assessment
- Consider patient's age and medical history

Response format for emergencies:
1. State severity level clearly
2. Give immediate action required
3. Provide specific instructions
4. Suggest what to prepare/bring
5. Offer nearest facility information"""
    
    def get_capabilities(self) -> List[str]:
        return [
            "Emergency symptom assessment",
            "Triage severity determination",
            "Emergency response guidance",
            "Facility recommendations",
            "First aid instructions",
            "911 call preparation",
            "Urgent care vs ER guidance"
        ]
    
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """Determine if this agent should handle the query."""
        query_lower = query.lower()
        
        # Maximum confidence for emergency keywords
        emergency_keywords = [
            "emergency", "urgent", "immediately", "911", "ambulance",
            "emergency room", "ER", "accident", "injury", "bleeding",
            "can't breathe", "chest pain", "heart attack", "stroke",
            "unconscious", "passed out", "severe pain", "help now"
        ]
        
        # High confidence for concerning symptoms
        concerning_phrases = [
            "really bad", "getting worse", "can't stop", "won't stop",
            "never felt", "worst ever", "suddenly", "all of a sudden",
            "right now", "immediately", "quickly getting"
        ]
        
        # Check for emergency keywords
        emergency_score = sum(0.3 for kw in emergency_keywords if kw in query_lower)
        concern_score = sum(0.2 for phrase in concerning_phrases if phrase in query_lower)
        
        # Check for symptom severity in context
        if context.get("current_symptoms"):
            symptoms_str = " ".join(context["current_symptoms"]).lower()
            if any(kw in symptoms_str for kw in emergency_keywords):
                emergency_score += 0.3
        
        # Calculate total score
        total_score = min(emergency_score + concern_score, 1.0)
        
        # This agent should activate even with moderate confidence for safety
        return max(total_score, 0.4 if emergency_score > 0 else 0)
    
    async def process_query(self, query: str, context: Dict[str, Any], stream: bool = True):
        """Process emergency queries with immediate assessment."""
        # Add timestamp to context for documentation
        context["triage_timestamp"] = datetime.utcnow().isoformat()
        
        # Process with high priority
        async for chunk in super().process_query(query, context, stream):
            yield chunk