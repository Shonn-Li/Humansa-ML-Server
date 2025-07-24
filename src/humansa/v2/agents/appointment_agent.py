from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
import json


async def search_available_slots(
    doctor_id: Optional[str] = None,
    specialty: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    time_preference: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for available appointment slots."""
    # This would integrate with the real booking system
    # For now, return mock data
    base_date = datetime.now()
    slots = []
    
    for i in range(5):  # Next 5 days
        date = base_date + timedelta(days=i+1)
        if date.weekday() < 5:  # Weekdays only
            slots.extend([
                {
                    "slot_id": f"slot_{date.strftime('%Y%m%d')}_0900",
                    "doctor_id": doctor_id or "dr_001",
                    "date": date.strftime("%Y-%m-%d"),
                    "time": "09:00",
                    "duration_minutes": 30,
                    "available": True,
                    "type": "in-person"
                },
                {
                    "slot_id": f"slot_{date.strftime('%Y%m%d')}_1400", 
                    "doctor_id": doctor_id or "dr_001",
                    "date": date.strftime("%Y-%m-%d"),
                    "time": "14:00",
                    "duration_minutes": 30,
                    "available": True,
                    "type": "telemedicine"
                }
            ])
    
    return slots


async def reserve_appointment_slot(
    slot_id: str,
    patient_id: str,
    appointment_type: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """Reserve an appointment slot (mock - no actual booking)."""
    return {
        "status": "reserved",
        "reservation_id": f"res_{datetime.now().timestamp()}",
        "slot_id": slot_id,
        "patient_id": patient_id,
        "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(),
        "next_step": "confirm_booking",
        "note": "This is a mock reservation. Slot held for 15 minutes."
    }


async def confirm_appointment(
    reservation_id: str,
    patient_details: Dict[str, Any]
) -> Dict[str, Any]:
    """Confirm a reserved appointment (mock)."""
    return {
        "status": "confirmed",
        "appointment_id": f"apt_{datetime.now().timestamp()}",
        "reservation_id": reservation_id,
        "confirmation_code": f"HMN{int(datetime.now().timestamp()) % 10000:04d}",
        "details": {
            **patient_details,
            "confirmed_at": datetime.now().isoformat()
        },
        "reminders_set": True,
        "note": "This is a mock confirmation. No actual appointment was booked."
    }


async def get_appointment_preparation(appointment_type: str, specialty: str) -> Dict[str, Any]:
    """Get preparation instructions for appointment."""
    general_prep = [
        "Bring your insurance card and ID",
        "Arrive 15 minutes early for check-in",
        "Bring list of current medications",
        "Prepare questions for your doctor"
    ]
    
    specialty_prep = {
        "cardiology": ["Wear comfortable clothing", "Avoid caffeine before appointment"],
        "dermatology": ["Remove makeup if facial consultation", "Wear loose clothing"],
        "gastroenterology": ["Follow any fasting instructions", "Bring previous test results"],
    }
    
    return {
        "general_preparation": general_prep,
        "specialty_preparation": specialty_prep.get(specialty.lower(), []),
        "required_documents": [
            "Insurance card",
            "Government ID",
            "Previous medical records (if any)",
            "Referral letter (if applicable)"
        ],
        "appointment_type": appointment_type
    }


class AppointmentAgent(BaseHumansaAgent):
    """Specialized agent for appointment booking and management."""
    
    def __init__(self, llm, **kwargs):
        tools = [
            FunctionTool.from_defaults(
                fn=search_available_slots,
                name="search_slots",
                description="Search for available appointment slots"
            ),
            FunctionTool.from_defaults(
                fn=reserve_appointment_slot,
                name="reserve_slot",
                description="Reserve an appointment slot"
            ),
            FunctionTool.from_defaults(
                fn=confirm_appointment,
                name="confirm_appointment",
                description="Confirm a reserved appointment"
            ),
            FunctionTool.from_defaults(
                fn=get_appointment_preparation,
                name="appointment_prep",
                description="Get appointment preparation instructions"
            )
        ]
        
        super().__init__(
            agent_id="appointment_agent",
            agent_name="Appointment Specialist",
            description="Handles appointment booking, scheduling, and management",
            llm=llm,
            tools=tools,
            **kwargs
        )
    
    def get_system_prompt(self) -> str:
        return """You are an appointment booking specialist for Humansa Health.

Your role is to:
1. Help patients find and book appointments
2. Check doctor availability and schedules
3. Reserve and confirm appointment slots
4. Provide appointment preparation instructions
5. Handle rescheduling and cancellations

Booking process:
1. Understand patient needs and preferences
2. Search for suitable appointment slots
3. Present options clearly (date, time, type)
4. Reserve chosen slot
5. Collect necessary information
6. Confirm the appointment
7. Provide preparation instructions

Important guidelines:
- Always confirm patient preferences (date, time, location)
- Explain the difference between in-person and telemedicine
- Mention the 15-minute reservation window
- Collect reason for visit to match with appropriate doctor
- Provide clear next steps after each action

When presenting slots:
- Show multiple options when available
- Include morning and afternoon choices
- Mention appointment type (in-person/virtual)
- Highlight earliest available

Information to collect:
- Preferred dates and times
- Reason for visit
- Type preference (in-person/telemedicine)
- Any specific doctor requests
- Insurance information (for confirmation)

Always end with:
- Confirmation details
- Preparation instructions
- Reminder settings confirmation"""
    
    def get_capabilities(self) -> List[str]:
        return [
            "Appointment slot search",
            "Real-time availability checking",
            "Appointment reservation",
            "Booking confirmation",
            "Preparation instructions",
            "Rescheduling assistance",
            "Cancellation handling"
        ]
    
    def should_handle_query(self, query: str, context: Dict[str, Any]) -> float:
        """Determine if this agent should handle the query."""
        query_lower = query.lower()
        
        # High confidence for appointment-related keywords
        appointment_keywords = [
            "appointment", "book", "booking", "schedule", "availability",
            "available", "slot", "slots", "reserve", "confirm",
            "reschedule", "cancel", "when can i see", "next available"
        ]
        
        # Specific appointment phrases
        appointment_phrases = [
            "make an appointment", "book an appointment",
            "see a doctor", "see the doctor", "available times",
            "earliest appointment", "change my appointment",
            "cancel my appointment", "book a consultation"
        ]
        
        # Check for matches
        keyword_score = sum(0.2 for kw in appointment_keywords if kw in query_lower)
        phrase_score = sum(0.3 for phrase in appointment_phrases if phrase in query_lower)
        
        # Check context for appointment flow
        context_score = 0
        if context.get("selected_doctor"):
            context_score += 0.2
        if context.get("appointment_preferences"):
            context_score += 0.1
            
        # Calculate total score
        total_score = min(keyword_score + phrase_score + context_score, 0.95)
        
        # Lower score if emergency-related
        if any(word in query_lower for word in ["emergency", "urgent", "immediately", "911"]):
            total_score *= 0.3
            
        return total_score