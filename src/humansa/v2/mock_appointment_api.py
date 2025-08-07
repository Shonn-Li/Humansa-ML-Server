"""
Mock Appointment Booking API for Humansa V2 Testing
This provides realistic appointment booking functionality for testing
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import logging

logger = logging.getLogger(__name__)


class MockAppointmentSystem:
    """Mock appointment system for testing."""
    
    def __init__(self):
        self.appointments = {}  # Store appointments by ID
        self.slots = {}  # Store available slots
        self._generate_mock_slots()
    
    def _generate_mock_slots(self):
        """Generate mock appointment slots for the next 30 days."""
        start_date = datetime.now().date()
        
        # List of mock doctors with schedules
        doctors = [
            {"id": "DOC001", "name": "张伟", "specialty": "骨科"},
            {"id": "DOC002", "name": "李娜", "specialty": "儿科"},
            {"id": "DOC003", "name": "王强", "specialty": "内科"},
            {"id": "DOC007", "name": "孙浩", "specialty": "心内科"},
            {"id": "DOC011", "name": "林涛", "specialty": "骨科"},
        ]
        
        time_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"]
        
        for day_offset in range(30):
            date = start_date + timedelta(days=day_offset)
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
                
            for doctor in doctors:
                # Each doctor has 60-80% of slots available
                available_slots = random.sample(time_slots, k=random.randint(6, 8))
                
                for time_slot in available_slots:
                    slot_id = f"SLOT_{doctor['id']}_{date.strftime('%Y%m%d')}_{time_slot.replace(':', '')}"
                    
                    self.slots[slot_id] = {
                        "slot_id": slot_id,
                        "doctor_id": doctor["id"],
                        "doctor_name": doctor["name"],
                        "specialty": doctor["specialty"],
                        "date": date.isoformat(),
                        "time": time_slot,
                        "duration_minutes": 30,
                        "status": "available",
                        "clinic_name": "诺亚新舟北京医疗中心",
                        "clinic_address": "北京市朝阳区建国路456号",
                        "price": 300.0
                    }
    
    async def search_appointments(self, search_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available appointment slots."""
        try:
            doctor_name = search_criteria.get("doctor_name")
            specialty = search_criteria.get("specialty")
            date_from = search_criteria.get("date_from", datetime.now().date().isoformat())
            date_to = search_criteria.get("date_to", (datetime.now().date() + timedelta(days=7)).isoformat())
            
            # Filter slots
            matching_slots = []
            for slot in self.slots.values():
                if slot["status"] != "available":
                    continue
                    
                if doctor_name and doctor_name not in slot["doctor_name"]:
                    continue
                    
                if specialty and specialty != slot["specialty"]:
                    continue
                    
                if slot["date"] < date_from or slot["date"] > date_to:
                    continue
                    
                matching_slots.append(slot)
            
            # Sort by date and time
            matching_slots.sort(key=lambda x: (x["date"], x["time"]))
            
            return {
                "success": True,
                "total_found": len(matching_slots),
                "slots": matching_slots[:20],  # Limit to 20 results
                "search_criteria": search_criteria,
                "message": f"Found {len(matching_slots)} available appointment slots"
            }
            
        except Exception as e:
            logger.error(f"Error searching appointments: {e}")
            return {
                "success": False,
                "error": str(e),
                "slots": []
            }
    
    async def book_appointment(self, slot_id: str, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """Book an appointment slot."""
        try:
            if slot_id not in self.slots:
                return {
                    "success": False,
                    "error": "Invalid slot ID"
                }
            
            slot = self.slots[slot_id]
            
            if slot["status"] != "available":
                return {
                    "success": False,
                    "error": "This slot is no longer available"
                }
            
            # Create appointment
            appointment_id = f"APT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
            
            appointment = {
                "appointment_id": appointment_id,
                "slot_id": slot_id,
                "patient_name": patient_info.get("name", "Unknown"),
                "patient_phone": patient_info.get("phone", ""),
                "patient_id": patient_info.get("patient_id", ""),
                "doctor_id": slot["doctor_id"],
                "doctor_name": slot["doctor_name"],
                "specialty": slot["specialty"],
                "appointment_date": slot["date"],
                "appointment_time": slot["time"],
                "clinic_name": slot["clinic_name"],
                "clinic_address": slot["clinic_address"],
                "price": slot["price"],
                "status": "confirmed",
                "created_at": datetime.now().isoformat(),
                "confirmation_code": f"HMN{random.randint(10000, 99999)}"
            }
            
            # Mark slot as booked
            slot["status"] = "booked"
            self.appointments[appointment_id] = appointment
            
            return {
                "success": True,
                "appointment": appointment,
                "message": "Appointment booked successfully"
            }
            
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Get appointment details."""
        if appointment_id in self.appointments:
            return {
                "success": True,
                "appointment": self.appointments[appointment_id]
            }
        
        return {
            "success": False,
            "error": "Appointment not found"
        }
    
    async def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """Cancel an appointment."""
        try:
            if appointment_id not in self.appointments:
                return {
                    "success": False,
                    "error": "Appointment not found"
                }
            
            appointment = self.appointments[appointment_id]
            
            # Check if can be cancelled (e.g., not less than 24 hours before)
            appointment_datetime = datetime.fromisoformat(f"{appointment['appointment_date']}T{appointment['appointment_time']}")
            if appointment_datetime - datetime.now() < timedelta(hours=24):
                return {
                    "success": False,
                    "error": "Cannot cancel appointment less than 24 hours in advance"
                }
            
            # Cancel appointment
            appointment["status"] = "cancelled"
            appointment["cancelled_at"] = datetime.now().isoformat()
            
            # Make slot available again
            slot_id = appointment["slot_id"]
            if slot_id in self.slots:
                self.slots[slot_id]["status"] = "available"
            
            return {
                "success": True,
                "message": "Appointment cancelled successfully",
                "appointment_id": appointment_id
            }
            
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def reschedule_appointment(self, appointment_id: str, new_slot_id: str) -> Dict[str, Any]:
        """Reschedule an appointment to a new slot."""
        try:
            # Cancel old appointment
            cancel_result = await self.cancel_appointment(appointment_id)
            if not cancel_result["success"]:
                return cancel_result
            
            # Get patient info from old appointment
            old_appointment = self.appointments[appointment_id]
            patient_info = {
                "name": old_appointment["patient_name"],
                "phone": old_appointment["patient_phone"],
                "patient_id": old_appointment.get("patient_id", "")
            }
            
            # Book new appointment
            booking_result = await self.book_appointment(new_slot_id, patient_info)
            
            if booking_result["success"]:
                booking_result["message"] = "Appointment rescheduled successfully"
                booking_result["old_appointment_id"] = appointment_id
            
            return booking_result
            
        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
mock_appointment_system = MockAppointmentSystem()