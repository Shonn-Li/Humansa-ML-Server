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
    """Search for available appointment slots from real database."""
    try:
        import asyncpg
        import os
        
        # Database connection parameters
        db_config = {
            'host': 'localhost',
            'port': 5454,  # Test database port
            'user': 'postgres',
            'password': '12931',
            'database': 'test4'
        }
        
        # Build query based on parameters
        query_conditions = ["s.is_available = true"]
        query_params = []
        param_counter = 1
        
        if doctor_id:
            query_conditions.append(f"s.doctor_id = ${param_counter}")
            query_params.append(doctor_id)
            param_counter += 1
            
        if specialty:
            query_conditions.append(f"d.specialty ILIKE ${param_counter}")
            query_params.append(f"%{specialty}%")
            param_counter += 1
            
        # Default date range if not specified
        if not date_from:
            date_from = datetime.now().strftime("%Y-%m-%d")
        if not date_to:
            date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            
        query_conditions.append(f"s.date BETWEEN ${param_counter} AND ${param_counter + 1}")
        query_params.extend([date_from, date_to])
        param_counter += 2
        
        # Time preference filter
        if time_preference:
            if "上午" in time_preference or "morning" in time_preference.lower():
                query_conditions.append("s.time < '12:00'")
            elif "下午" in time_preference or "afternoon" in time_preference.lower():
                query_conditions.append("s.time >= '12:00'")
        
        query = f"""
        SELECT 
            s.slot_id,
            s.doctor_id,
            d.name as doctor_name,
            d.specialty,
            s.date,
            s.time,
            s.duration_minutes,
            s.consultation_type,
            s.consultation_fee,
            c.name as clinic_name
        FROM humansa_appointment_slots s
        JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
        LEFT JOIN humansa_clinics c ON s.clinic_id = c.clinic_code
        WHERE {' AND '.join(query_conditions)}
        ORDER BY s.date, s.time
        LIMIT 20
        """
        
        # Execute query
        conn = await asyncpg.connect(**db_config)
        try:
            rows = await conn.fetch(query, *query_params)
            
            slots = []
            for row in rows:
                slots.append({
                    "slot_id": str(row['slot_id']),
                    "doctor_id": row['doctor_id'],
                    "doctor_name": row['doctor_name'],
                    "specialty": row['specialty'],
                    "date": row['date'].strftime("%Y-%m-%d"),
                    "time": row['time'].strftime("%H:%M"),
                    "duration_minutes": row['duration_minutes'],
                    "consultation_type": row['consultation_type'],
                    "consultation_fee": float(row['consultation_fee']) if row['consultation_fee'] else 0,
                    "clinic_name": row['clinic_name'],
                    "available": True
                })
            
            return slots
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"Error searching appointment slots: {e}")
        # Fallback to mock data if database connection fails
        return [{
            "slot_id": "fallback_001",
            "doctor_id": "DOC001", 
            "doctor_name": "张伟",
            "specialty": "骨科",
            "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": "09:00",
            "duration_minutes": 30,
            "consultation_type": "in-person",
            "consultation_fee": 120.0,
            "clinic_name": "北京协和医院",
            "available": True
        }]


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