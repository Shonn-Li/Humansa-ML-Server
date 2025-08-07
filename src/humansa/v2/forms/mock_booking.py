"""
Mock booking service for testing form submissions
"""
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MockBookingService:
    """Mock booking service that simulates real appointment booking"""
    
    def __init__(self):
        # Simulate a booking database
        self._bookings = {}
        self._confirmation_codes = set()
    
    def _generate_confirmation_code(self) -> str:
        """Generate unique confirmation code"""
        while True:
            code = 'APT-' + ''.join(random.choices(string.digits, k=8))
            if code not in self._confirmation_codes:
                self._confirmation_codes.add(code)
                return code
    
    async def check_availability(
        self, 
        doctor_id: str, 
        date: str, 
        time_slot: str
    ) -> Dict[str, Any]:
        """Mock availability check"""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Random availability (80% available)
        is_available = random.random() > 0.2
        
        if not is_available:
            # Suggest alternative slots
            alternatives = []
            base_time = datetime.strptime(f"{date} {time_slot.split('-')[0]}", "%Y-%m-%d %H:%M")
            
            for i in range(3):
                alt_time = base_time + timedelta(hours=i+1)
                alternatives.append({
                    "date": alt_time.strftime("%Y-%m-%d"),
                    "time": alt_time.strftime("%H:%M") + "-" + (alt_time + timedelta(minutes=30)).strftime("%H:%M")
                })
        
            return {
                "available": False,
                "reason": "该时段已被预约",
                "alternatives": alternatives
            }
        
        return {
            "available": True,
            "hold_until": (datetime.now() + timedelta(minutes=5)).isoformat()
        }
    
    async def book_appointment(
        self, 
        form_id: str,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock appointment booking"""
        try:
            # Simulate processing
            await asyncio.sleep(1.0)
            
            # Extract key information
            doctor_name = form_data.get('doctor_name', '未知医生')
            patient_name = form_data.get('patient_name', '未知患者')
            appointment_date = form_data.get('appointment_date', form_data.get('date'))
            appointment_time = form_data.get('appointment_time', form_data.get('time_slot', '未知时间'))
            department = form_data.get('department', form_data.get('speciality', '未知科室'))
            
            # Generate confirmation
            confirmation_code = self._generate_confirmation_code()
            booking_id = f"BK_{form_id[:8]}_{int(datetime.now().timestamp())}"
            
            # Create booking record
            booking = {
                "booking_id": booking_id,
                "confirmation_code": confirmation_code,
                "form_id": form_id,
                "status": "confirmed",
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "department": department,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "created_at": datetime.now().isoformat(),
                "qr_code": f"https://hospital.example.com/qr/{confirmation_code}",
                "location": "北京协和医院 门诊楼3层 " + department,
                "instructions": [
                    "请提前15分钟到达医院",
                    "请携带身份证和医保卡",
                    "如需空腹检查，请勿进食"
                ],
                "estimated_wait_time": random.randint(10, 30),
                "fee_details": {
                    "registration_fee": form_data.get('registration_fee', 50),
                    "consultation_fee": form_data.get('consultation_fee', 100),
                    "service_fee": form_data.get('service_fee', 5),
                    "total": form_data.get('total_fee', 155)
                }
            }
            
            # Store booking
            self._bookings[booking_id] = booking
            
            logger.info(f"✅ Mock booking created: {booking_id} with confirmation: {confirmation_code}")
            
            return {
                "success": True,
                "booking": booking,
                "message": f"预约成功！预约号：{confirmation_code}"
            }
            
        except Exception as e:
            logger.error(f"Mock booking failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "预约失败，请稍后重试"
            }
    
    async def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        """Mock booking cancellation"""
        if booking_id in self._bookings:
            self._bookings[booking_id]["status"] = "cancelled"
            self._bookings[booking_id]["cancelled_at"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "message": "预约已取消"
            }
        
        return {
            "success": False,
            "message": "找不到该预约"
        }
    
    async def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking details"""
        return self._bookings.get(booking_id)


# Global mock booking service instance
mock_booking_service = MockBookingService()


async def mock_submit_appointment_form(
    form_id: str,
    form_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mock function to submit appointment form and create booking
    This simulates what would happen when form is confirmed
    """
    logger.info(f"🏥 Mock booking appointment for form: {form_id}")
    
    # Check availability first
    availability = await mock_booking_service.check_availability(
        doctor_id=form_data.get('doctor_id', 'doc_001'),
        date=form_data.get('appointment_date', form_data.get('date')),
        time_slot=form_data.get('appointment_time', form_data.get('time_slot'))
    )
    
    if not availability['available']:
        return {
            "success": False,
            "reason": "time_unavailable",
            "message": availability['reason'],
            "alternatives": availability.get('alternatives', [])
        }
    
    # Book appointment
    result = await mock_booking_service.book_appointment(form_id, form_data)
    
    if result['success']:
        booking = result['booking']
        
        # Format success message
        success_message = f"""
✅ 预约成功！

预约确认号：{booking['confirmation_code']}
患者姓名：{booking['patient_name']}
就诊医生：{booking['doctor_name']}（{booking['department']}）
就诊时间：{booking['appointment_date']} {booking['appointment_time']}
就诊地点：{booking['location']}

注意事项：
""" + "\n".join([f"- {inst}" for inst in booking['instructions']]) + f"""

预计等待时间：约{booking['estimated_wait_time']}分钟

费用明细：
- 挂号费：¥{booking['fee_details']['registration_fee']}
- 诊疗费：¥{booking['fee_details']['consultation_fee']}
- 服务费：¥{booking['fee_details']['service_fee']}
- 总计：¥{booking['fee_details']['total']}

二维码：{booking['qr_code']}

请准时到达，祝您早日康复！
"""
        
        return {
            "success": True,
            "booking_id": booking['booking_id'],
            "confirmation_code": booking['confirmation_code'],
            "message": success_message,
            "booking_details": booking
        }
    
    return result