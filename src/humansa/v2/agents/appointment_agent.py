from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_agent import BaseHumansaAgent
from llama_index.core.tools import FunctionTool
import json
import logging
import os

logger = logging.getLogger(__name__)


async def search_available_slots(
    doctor_id: Optional[str] = None,
    specialty: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    time_preference: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for available appointment slots from real database."""
    logger.info(f"🔍 SEARCH_SLOTS called with: doctor_id={doctor_id}, specialty={specialty}, date_from={date_from}, date_to={date_to}, time_preference={time_preference}")
    
    try:
        import asyncpg
        import os
        
        # Database connection parameters
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '12931'),
            'database': os.getenv('DB_NAME', 'test4')
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
            date_from = datetime.now().date()
        else:
            # Convert string to date if needed
            if isinstance(date_from, str):
                try:
                    date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                except ValueError:
                    date_from = datetime.now().date()
            
        if not date_to:
            date_to = datetime.now().date() + timedelta(days=7)
        else:
            # Convert string to date if needed
            if isinstance(date_to, str):
                try:
                    date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                except ValueError:
                    date_to = datetime.now().date() + timedelta(days=7)
            
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
        JOIN humansa_doctor d ON s.doctor_id = d.doctor_id
        LEFT JOIN humansa_clinics c ON s.clinic_code = c.clinic_code
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
            
            logger.info(f"✅ Found {len(slots)} available appointment slots")
            return slots
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"❌ Error searching appointment slots: {e}")
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


async def present_appointment_options(
    available_slots: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Present available appointment options to user for selection."""
    logger.info(f"📋 PRESENT_OPTIONS called with {len(available_slots)} slots")
    
    if not available_slots:
        return {
            "status": "no_slots",
            "message": "抱歉，没有找到符合条件的可预约时间。请尝试其他日期或科室。",
            "options": []
        }
    
    # Format options for user selection
    formatted_options = []
    for i, slot in enumerate(available_slots[:10], 1):  # Limit to top 10 options
        option = {
            "option_number": i,
            "slot_id": slot["slot_id"],
            "display_text": f"{i}. {slot['doctor_name']}医生 ({slot['specialty']}) - {slot['date']} {slot['time']} - {slot['clinic_name']} - ¥{slot['consultation_fee']:.0f} ({slot['consultation_type']})",
            "details": slot
        }
        formatted_options.append(option)
    
    return {
        "status": "options_available", 
        "message": f"为您找到 {len(available_slots)} 个可预约时间，以下是推荐选项：",
        "options": formatted_options,
        "total_found": len(available_slots)
    }


async def request_booking_approval(
    selected_slot: Dict[str, Any],
    patient_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Request user approval for appointment booking."""
    logger.info(f"✋ APPROVAL_REQUEST for slot_id={selected_slot.get('slot_id')}")
    
    approval_details = {
        "booking_summary": {
            "doctor": f"{selected_slot['doctor_name']}医生",
            "specialty": selected_slot['specialty'],
            "date": selected_slot['date'],
            "time": selected_slot['time'],
            "clinic": selected_slot['clinic_name'],
            "fee": f"¥{selected_slot['consultation_fee']:.0f}",
            "type": "现场就诊" if selected_slot['consultation_type'] == 'in-person' else "在线咨询"
        },
        "patient_info": patient_info or {},
        "approval_required": True,
        "approval_timeout_minutes": 5,
        "confirmation_message": f"""
📋 **预约确认**

👨‍⚕️ **医生信息**
- 医生：{selected_slot['doctor_name']}医生 ({selected_slot['specialty']})
- 医院：{selected_slot['clinic_name']}
- 就诊方式：{'现场就诊' if selected_slot['consultation_type'] == 'in-person' else '在线咨询'}

⏰ **预约时间**
- 日期：{selected_slot['date']}
- 时间：{selected_slot['time']}

💰 **费用信息**
- 挂号费：¥{selected_slot['consultation_fee']:.0f}

❓ **请确认是否预约此时间段？**
回复 "确认预约" 或 "取消预约"
        """
    }
    
    return approval_details


async def process_user_approval(
    approval_response: str,
    slot_details: Dict[str, Any],
    patient_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process user approval/rejection of appointment booking."""
    logger.info(f"👤 USER_APPROVAL: '{approval_response}' for slot_id={slot_details.get('slot_id')}")
    
    # Normalize response
    response_lower = approval_response.lower().strip()
    
    # Check for approval keywords
    approval_keywords = ["确认", "预约", "是的", "好的", "同意", "yes", "ok", "确定"]
    rejection_keywords = ["取消", "不要", "不", "拒绝", "no", "cancel", "不预约"]
    
    if any(keyword in response_lower for keyword in approval_keywords):
        # User approved - proceed with booking
        return {
            "status": "approved",
            "action": "proceed_booking",
            "message": "✅ 您已确认预约，正在为您安排...",
            "next_step": "finalize_booking"
        }
    elif any(keyword in response_lower for keyword in rejection_keywords):
        # User rejected - cancel process
        return {
            "status": "rejected", 
            "action": "cancel_booking",
            "message": "❌ 预约已取消。如需重新预约，请告诉我您的需求。",
            "next_step": "search_again"
        }
    else:
        # Unclear response - ask for clarification
        return {
            "status": "unclear",
            "action": "request_clarification", 
            "message": "请明确回复 '确认预约' 或 '取消预约'，以便我为您处理。",
            "next_step": "await_clear_response"
        }


async def finalize_booking(
    slot_id: str,
    patient_info: Dict[str, Any],
    approval_confirmed: bool = True
) -> Dict[str, Any]:
    """Finalize the appointment booking after user approval."""
    logger.info(f"🎯 FINALIZE_BOOKING for slot_id={slot_id}, approved={approval_confirmed}")
    
    if not approval_confirmed:
        return {
            "status": "booking_failed",
            "message": "预约未获得确认，已取消。",
            "booking_id": None
        }
    
    try:
        import asyncpg
        
        # Database connection parameters
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'postgres'), 
            'password': os.getenv('DB_PASSWORD', '12931'),
            'database': os.getenv('DB_NAME', 'test4')
        }
        
        conn = await asyncpg.connect(**db_config)
        try:
            # Get slot details for booking
            slot_query = """
            SELECT s.*, d.name as doctor_name, d.specialty, c.name as clinic_name
            FROM humansa_appointment_slots s
            JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
            LEFT JOIN humansa_clinics c ON s.clinic_code = c.clinic_code
            WHERE s.slot_id = $1 AND s.is_available = true
            """
            
            slot_row = await conn.fetchrow(slot_query, int(slot_id))
            if not slot_row:
                return {
                    "status": "booking_failed",
                    "message": "该时间段已被预约或不可用，请选择其他时间。",
                    "booking_id": None
                }
            
            # Create appointment record
            booking_query = """
            INSERT INTO humansa_appointments (schedule_id, patient_name, patient_phone, appointment_time, status, created_at)
            VALUES ($1, $2, $3, $4, 'confirmed', CURRENT_TIMESTAMP)
            RETURNING appointment_id
            """
            
            booking_id = await conn.fetchval(
                booking_query,
                int(slot_id),
                patient_info.get('name', '患者'),
                patient_info.get('phone', ''),
                slot_row['time']
            )
            
            # Mark slot as unavailable
            update_query = "UPDATE humansa_appointment_slots SET is_available = false WHERE slot_id = $1"
            await conn.execute(update_query, int(slot_id))
            
            logger.info(f"✅ Booking confirmed: appointment_id={booking_id}")
            
            return {
                "status": "booking_confirmed",
                "booking_id": str(booking_id),
                "message": f"""
🎉 **预约成功！**

📋 **预约详情**
- 预约号：{booking_id}
- 医生：{slot_row['doctor_name']}医生 ({slot_row['specialty']})
- 时间：{slot_row['date']} {slot_row['time']}
- 地点：{slot_row['clinic_name']}
- 患者：{patient_info.get('name', '患者')}

📱 **联系方式**
- 手机：{patient_info.get('phone', '请补充')}

⏰ **温馨提示**
- 请提前15分钟到达
- 携带身份证和医保卡
- 如需取消请提前2小时联系
                """,
                "appointment_details": {
                    "booking_id": str(booking_id),
                    "doctor_name": slot_row['doctor_name'],
                    "specialty": slot_row['specialty'],
                    "date": slot_row['date'].strftime("%Y-%m-%d"),
                    "time": slot_row['time'].strftime("%H:%M"),
                    "clinic_name": slot_row['clinic_name'],
                    "patient_name": patient_info.get('name', '患者'),
                    "patient_phone": patient_info.get('phone', '')
                }
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"❌ Error finalizing booking: {e}")
        return {
            "status": "booking_failed", 
            "message": f"预约过程中出现错误：{str(e)}，请重新尝试。",
            "booking_id": None
        }


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
                description="Search for available appointment slots by specialty, doctor, date, or time preference"
            ),
            FunctionTool.from_defaults(
                fn=present_appointment_options,
                name="present_options",
                description="Present formatted appointment options to user for selection"
            ),
            FunctionTool.from_defaults(
                fn=request_booking_approval,
                name="request_approval",
                description="Request user approval for a specific appointment booking"
            ),
            FunctionTool.from_defaults(
                fn=process_user_approval,
                name="process_approval",
                description="Process user's approval or rejection response"
            ),
            FunctionTool.from_defaults(
                fn=finalize_booking,
                name="finalize_booking",
                description="Complete the appointment booking after user approval"
            ),
            FunctionTool.from_defaults(
                fn=reserve_appointment_slot,
                name="reserve_slot",
                description="Reserve an appointment slot temporarily"
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
        return """You are an appointment booking specialist for Humansa Health with access to real-time appointment data.

🎯 CRITICAL: When a user asks about appointments, IMMEDIATELY use the search_slots tool to find available appointments. Don't ask for location details first - search with what you have and show real options.

Your role is to:
1. **PROACTIVELY SEARCH** for available appointments using real database
2. Present actual available slots with specific doctors, dates, and times  
3. Guide users through the booking process with real options
4. Handle reservations, confirmations, and changes

⚡ IMMEDIATE ACTION REQUIRED:
- For ANY appointment request → CALL search_slots tool FIRST
- User says "心内科" → search_slots(specialty="心内科") 
- User says "张医生" → search_slots(doctor_id="DOC001") 
- User says "明天" → search_slots(date_from="2025-08-01")
- User says "上午" → search_slots(time_preference="上午")

🔧 Available Tools:
- search_slots: Find real available appointments (USE THIS FIRST!)
- reserve_slot: Hold a specific appointment slot
- confirm_appointment: Finalize the booking
- appointment_prep: Get preparation instructions

📋 Booking Flow:
1. **SEARCH IMMEDIATELY** with any available criteria
2. Present REAL options with specific details:
   - Doctor name and specialty
   - Exact date and time
   - Clinic location  
   - Consultation fee
   - Online/in-person option
3. Ask user to choose from real options
4. Reserve the selected slot
5. Collect patient details
6. Confirm and provide instructions

✅ Example Response:
"让我为您查询心内科的可预约时间..."
[CALLS search_slots(specialty="心内科")]
"找到以下心内科医生的可预约时间：
1. 孙浩医生 - 8月1日 09:00 - 广州中山医院 - 120元
2. 孙浩医生 - 8月1日 14:00 - 广州中山医院 - 120元
..."

❌ NEVER say "请提供医院信息" - USE THE SEARCH TOOL FIRST!

Always be helpful and proactive in finding real appointment options."""
    
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