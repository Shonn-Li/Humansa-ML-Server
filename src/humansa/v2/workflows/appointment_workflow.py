from typing import Dict, Any, List, Optional
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Event
)
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from ..mock_appointment_api import mock_appointment_system

logger = logging.getLogger(__name__)


@dataclass
class AppointmentSearchEvent(Event):
    """Event for searching appointment slots."""
    user_id: str
    search_criteria: Dict[str, Any]
    context: Dict[str, Any]


@dataclass
class SlotSelectionEvent(Event):
    """Event for slot selection."""
    user_id: str
    available_slots: List[Dict[str, Any]]
    preferences: Dict[str, Any]


@dataclass
class ReservationEvent(Event):
    """Event for slot reservation."""
    user_id: str
    selected_slot: Dict[str, Any]
    patient_info: Dict[str, Any]


@dataclass
class ConfirmationEvent(Event):
    """Event for appointment confirmation."""
    user_id: str
    reservation_id: str
    reservation_details: Dict[str, Any]


@dataclass
class NotificationEvent(Event):
    """Event for sending notifications."""
    user_id: str
    appointment_id: str
    notification_type: str
    details: Dict[str, Any]


class AppointmentBookingWorkflow(Workflow):
    """Complete appointment booking workflow."""
    
    def __init__(self, db_pool, notification_service=None, **kwargs):
        super().__init__(**kwargs)
        self.db_pool = db_pool
        self.notification_service = notification_service
        self._reservations: Dict[str, Dict[str, Any]] = {}
        
    @step
    async def search_appointments(self, ev: StartEvent) -> AppointmentSearchEvent:
        """Initial step to process appointment search request."""
        user_id = ev.get("user_id")
        search_criteria = ev.get("search_criteria", {})
        context = ev.get("context", {})
        
        # Extract search parameters
        doctor_id = search_criteria.get("doctor_id")
        specialty = search_criteria.get("specialty")
        date_preference = search_criteria.get("date_preference")
        time_preference = search_criteria.get("time_preference")
        
        # Enhance search criteria with user preferences
        if patient_profile := context.get("patient_profile"):
            if not specialty and patient_profile.get("preferred_specialty"):
                specialty = patient_profile["preferred_specialty"]
                
        enhanced_criteria = {
            "doctor_id": doctor_id,
            "specialty": specialty,
            "date_from": date_preference.get("from") if date_preference else None,
            "date_to": date_preference.get("to") if date_preference else None,
            "time_preference": time_preference,
            "appointment_type": search_criteria.get("type", "any")
        }
        
        return AppointmentSearchEvent(
            user_id=user_id,
            search_criteria=enhanced_criteria,
            context=context
        )
    
    @step
    async def find_available_slots(self, ev: AppointmentSearchEvent) -> SlotSelectionEvent:
        """Find available appointment slots based on criteria."""
        slots = await self._search_slots_in_db(ev.search_criteria)
        
        if not slots:
            # Expand search if no slots found
            expanded_criteria = self._expand_search_criteria(ev.search_criteria)
            slots = await self._search_slots_in_db(expanded_criteria)
            
        # Sort slots by date and time
        slots.sort(key=lambda x: (x["date"], x["time"]))
        
        # Extract user preferences
        preferences = {
            "preferred_time": ev.search_criteria.get("time_preference"),
            "appointment_type": ev.search_criteria.get("appointment_type"),
            "max_wait_days": ev.context.get("patient_profile", {}).get("max_wait_days", 14)
        }
        
        return SlotSelectionEvent(
            user_id=ev.user_id,
            available_slots=slots[:10],  # Limit to 10 options
            preferences=preferences
        )
    
    @step
    async def select_and_reserve_slot(self, ev: SlotSelectionEvent) -> ReservationEvent:
        """Handle slot selection and create reservation."""
        if not ev.available_slots:
            return StopEvent(result={
                "status": "no_slots_available",
                "message": "No appointment slots available for the specified criteria"
            })
        
        # Auto-select best slot based on preferences
        selected_slot = self._select_best_slot(ev.available_slots, ev.preferences)
        
        # Get patient information
        patient_info = await self._get_patient_info(ev.user_id)
        
        return ReservationEvent(
            user_id=ev.user_id,
            selected_slot=selected_slot,
            patient_info=patient_info
        )
    
    @step
    async def create_reservation(self, ev: ReservationEvent) -> ConfirmationEvent:
        """Create appointment reservation."""
        # Generate reservation ID
        reservation_id = f"res_{datetime.now().timestamp()}_{ev.user_id}"
        
        # Create reservation record
        reservation_details = {
            "reservation_id": reservation_id,
            "user_id": ev.user_id,
            "slot_id": ev.selected_slot["slot_id"],
            "doctor_id": ev.selected_slot["doctor_id"],
            "appointment_date": ev.selected_slot["date"],
            "appointment_time": ev.selected_slot["time"],
            "appointment_type": ev.selected_slot.get("type", "in-person"),
            "patient_info": ev.patient_info,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(),
            "status": "reserved"
        }
        
        # Store reservation
        self._reservations[reservation_id] = reservation_details
        
        # In real implementation, this would update the database
        # await self._create_reservation_in_db(reservation_details)
        
        return ConfirmationEvent(
            user_id=ev.user_id,
            reservation_id=reservation_id,
            reservation_details=reservation_details
        )
    
    @step
    async def confirm_and_notify(self, ev: ConfirmationEvent) -> StopEvent:
        """Confirm appointment and send notifications."""
        # Generate confirmation code
        confirmation_code = f"HMN{int(datetime.now().timestamp()) % 10000:04d}"
        
        # Update reservation to confirmed
        appointment_id = f"apt_{datetime.now().timestamp()}_{ev.user_id}"
        
        appointment_details = {
            "appointment_id": appointment_id,
            "confirmation_code": confirmation_code,
            "reservation_id": ev.reservation_id,
            **ev.reservation_details,
            "status": "confirmed",
            "confirmed_at": datetime.now().isoformat()
        }
        
        # Send confirmation notification
        if self.notification_service:
            await self.notification_service.send_confirmation(
                ev.user_id,
                appointment_details
            )
        
        # Prepare response
        doctor_info = await self._get_doctor_info(ev.reservation_details["doctor_id"])
        
        result = {
            "status": "success",
            "appointment_id": appointment_id,
            "confirmation_code": confirmation_code,
            "details": {
                "doctor": doctor_info["name"],
                "specialty": doctor_info["specialty"],
                "date": ev.reservation_details["appointment_date"],
                "time": ev.reservation_details["appointment_time"],
                "type": ev.reservation_details["appointment_type"],
                "location": doctor_info.get("clinic_location", "TBD"),
                "duration": "30 minutes"
            },
            "preparation": self._get_preparation_instructions(
                doctor_info["specialty"],
                ev.reservation_details["appointment_type"]
            ),
            "reminders_set": True,
            "next_steps": [
                "You will receive a confirmation email shortly",
                "SMS reminder will be sent 1 day before",
                "Arrive 15 minutes early for registration"
            ]
        }
        
        return StopEvent(result=result)
    
    async def _search_slots_in_db(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for available slots using mock appointment system."""
        # Use the mock appointment system
        result = await mock_appointment_system.search_appointments(criteria)
        
        if result.get("success"):
            return result.get("slots", [])
        else:
            logger.error(f"Failed to search appointments: {result.get('error')}")
            return []
    
    def _expand_search_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Expand search criteria if no slots found."""
        expanded = criteria.copy()
        
        # Extend date range
        if not expanded.get("date_to"):
            expanded["date_to"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
        # Remove time preference
        expanded.pop("time_preference", None)
        
        return expanded
    
    def _select_best_slot(
        self,
        slots: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select the best slot based on preferences."""
        # Simple selection - first available
        # In real implementation, would use scoring algorithm
        return slots[0]
    
    async def _get_patient_info(self, user_id: str) -> Dict[str, Any]:
        """Get patient information from database."""
        # Mock implementation
        return {
            "user_id": user_id,
            "name": "Patient Name",
            "email": "patient@email.com",
            "phone": "+65 9XXX XXXX",
            "insurance": "Insurance Provider"
        }
    
    async def _get_doctor_info(self, doctor_id: str) -> Dict[str, Any]:
        """Get doctor information."""
        # Mock implementation
        return {
            "doctor_id": doctor_id,
            "name": "Dr. Sarah Chen",
            "specialty": "General Practice",
            "clinic_location": "Humansa Central Clinic"
        }
    
    def _get_preparation_instructions(
        self,
        specialty: str,
        appointment_type: str
    ) -> List[str]:
        """Get appointment preparation instructions."""
        general_prep = [
            "Bring your insurance card and ID",
            "Prepare list of current medications",
            "Note down your symptoms and questions"
        ]
        
        if appointment_type == "telemedicine":
            general_prep.extend([
                "Ensure stable internet connection",
                "Find a quiet, private space",
                "Test your camera and microphone"
            ])
        else:
            general_prep.append("Arrive 15 minutes early")
            
        return general_prep