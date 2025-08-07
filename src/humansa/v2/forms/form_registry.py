"""
Form Registry for completed appointments
Tracks completed forms for user history and analytics
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging
import uuid
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CompletedAppointment:
    """Record of a completed appointment booking"""
    registry_id: str
    form_id: str
    user_id: str
    booking_id: str
    confirmation_code: str
    
    # Appointment details
    doctor_name: str
    doctor_id: str
    department: str
    appointment_date: str
    appointment_time: str
    symptoms: str
    
    # Booking metadata
    booked_at: datetime
    form_created_at: datetime
    form_confirmed_at: datetime
    
    # Status tracking
    status: str  # completed, cancelled, no_show
    cancellation_reason: Optional[str] = None
    
    # Follow-up
    follow_up_required: bool = False
    follow_up_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime to ISO format
        data['booked_at'] = self.booked_at.isoformat()
        data['form_created_at'] = self.form_created_at.isoformat()
        data['form_confirmed_at'] = self.form_confirmed_at.isoformat()
        return data


class FormRegistry:
    """
    Registry for completed appointment forms
    Provides user history, analytics, and follow-up tracking
    """
    
    def __init__(self):
        # In-memory storage (ready for database migration)
        self._completed_appointments: Dict[str, CompletedAppointment] = {}
        self._user_appointments: Dict[str, List[str]] = {}  # user_id -> [registry_ids]
        self._booking_to_registry: Dict[str, str] = {}  # booking_id -> registry_id
        
    async def register_completed_appointment(
        self,
        form_data: Dict[str, Any],
        booking_result: Dict[str, Any]
    ) -> str:
        """
        Register a completed appointment booking
        
        Args:
            form_data: The appointment form data
            booking_result: Result from booking service
            
        Returns:
            registry_id: Unique ID for this registry entry
        """
        registry_id = f"reg_{uuid.uuid4().hex[:12]}"
        
        # Create registry entry
        appointment = CompletedAppointment(
            registry_id=registry_id,
            form_id=form_data['form_id'],
            user_id=form_data['user_id'],
            booking_id=booking_result['booking_id'],
            confirmation_code=booking_result['confirmation_code'],
            
            # Appointment details
            doctor_name=form_data.get('doctor_name', ''),
            doctor_id=form_data.get('doctor_id', ''),
            department=form_data.get('department', ''),
            appointment_date=form_data.get('appointment_date', ''),
            appointment_time=form_data.get('appointment_time', ''),
            symptoms=form_data.get('symptoms', ''),
            
            # Timestamps
            booked_at=datetime.now(),
            form_created_at=datetime.fromisoformat(form_data.get('created_at', datetime.now().isoformat())),
            form_confirmed_at=datetime.fromisoformat(form_data.get('updated_at', datetime.now().isoformat())),
            
            # Initial status
            status='completed'
        )
        
        # Store in registry
        self._completed_appointments[registry_id] = appointment
        
        # Update user index
        user_id = form_data['user_id']
        if user_id not in self._user_appointments:
            self._user_appointments[user_id] = []
        self._user_appointments[user_id].append(registry_id)
        
        # Update booking index
        self._booking_to_registry[booking_result['booking_id']] = registry_id
        
        logger.info(f"✅ Registered completed appointment: {registry_id} for user {user_id}")
        
        # Check if follow-up might be needed
        await self._check_follow_up_requirements(appointment)
        
        return registry_id
    
    async def get_user_appointment_history(
        self,
        user_id: str,
        limit: int = 10,
        include_cancelled: bool = False
    ) -> List[CompletedAppointment]:
        """Get user's appointment history"""
        if user_id not in self._user_appointments:
            return []
        
        registry_ids = self._user_appointments[user_id]
        appointments = []
        
        for reg_id in reversed(registry_ids):  # Most recent first
            if reg_id in self._completed_appointments:
                appointment = self._completed_appointments[reg_id]
                if include_cancelled or appointment.status != 'cancelled':
                    appointments.append(appointment)
                    if len(appointments) >= limit:
                        break
        
        return appointments
    
    async def get_appointment_by_booking_id(self, booking_id: str) -> Optional[CompletedAppointment]:
        """Find appointment by booking ID"""
        registry_id = self._booking_to_registry.get(booking_id)
        if registry_id:
            return self._completed_appointments.get(registry_id)
        return None
    
    async def update_appointment_status(
        self,
        booking_id: str,
        status: str,
        reason: Optional[str] = None
    ) -> bool:
        """Update appointment status (e.g., cancelled, no_show)"""
        appointment = await self.get_appointment_by_booking_id(booking_id)
        if not appointment:
            logger.warning(f"Appointment not found for booking_id: {booking_id}")
            return False
        
        appointment.status = status
        if reason:
            appointment.cancellation_reason = reason
        
        logger.info(f"Updated appointment {appointment.registry_id} status to {status}")
        return True
    
    async def get_upcoming_appointments(
        self,
        user_id: str,
        days_ahead: int = 7
    ) -> List[CompletedAppointment]:
        """Get user's upcoming appointments"""
        appointments = await self.get_user_appointment_history(user_id, limit=50)
        upcoming = []
        
        today = datetime.now().date()
        cutoff = today + timedelta(days=days_ahead)
        
        for appointment in appointments:
            try:
                # Parse appointment date
                appt_date = datetime.fromisoformat(appointment.appointment_date).date()
                if today <= appt_date <= cutoff and appointment.status == 'completed':
                    upcoming.append(appointment)
            except:
                continue
        
        return sorted(upcoming, key=lambda x: x.appointment_date)
    
    async def _check_follow_up_requirements(self, appointment: CompletedAppointment):
        """Check if appointment might need follow-up"""
        # Simple heuristic based on symptoms
        follow_up_symptoms = ['慢性', '复查', '手术后', '化疗', '长期']
        
        if any(keyword in appointment.symptoms for keyword in follow_up_symptoms):
            appointment.follow_up_required = True
            appointment.follow_up_notes = "根据症状描述，可能需要定期复查"
            logger.info(f"Follow-up marked for appointment {appointment.registry_id}")
    
    async def get_analytics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get appointment analytics"""
        if user_id:
            # User-specific analytics
            appointments = await self.get_user_appointment_history(user_id, limit=100, include_cancelled=True)
            
            total = len(appointments)
            completed = sum(1 for a in appointments if a.status == 'completed')
            cancelled = sum(1 for a in appointments if a.status == 'cancelled')
            
            # Department distribution
            dept_counts = {}
            for appt in appointments:
                dept = appt.department
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            # Most visited doctors
            doctor_counts = {}
            for appt in appointments:
                doctor = appt.doctor_name
                doctor_counts[doctor] = doctor_counts.get(doctor, 0) + 1
            
            return {
                'user_id': user_id,
                'total_appointments': total,
                'completed': completed,
                'cancelled': cancelled,
                'completion_rate': completed / total if total > 0 else 0,
                'departments': dept_counts,
                'doctors': doctor_counts,
                'upcoming': len(await self.get_upcoming_appointments(user_id))
            }
        else:
            # System-wide analytics
            total_users = len(self._user_appointments)
            total_appointments = len(self._completed_appointments)
            
            status_counts = {}
            for appt in self._completed_appointments.values():
                status_counts[appt.status] = status_counts.get(appt.status, 0) + 1
            
            return {
                'total_users': total_users,
                'total_appointments': total_appointments,
                'status_distribution': status_counts,
                'average_appointments_per_user': total_appointments / total_users if total_users > 0 else 0
            }
    
    def export_user_history(self, user_id: str) -> Dict[str, Any]:
        """Export user's complete appointment history"""
        appointments = []
        if user_id in self._user_appointments:
            for reg_id in self._user_appointments[user_id]:
                if reg_id in self._completed_appointments:
                    appointments.append(self._completed_appointments[reg_id].to_dict())
        
        return {
            'user_id': user_id,
            'export_date': datetime.now().isoformat(),
            'total_appointments': len(appointments),
            'appointments': appointments
        }


# Global registry instance
form_registry = FormRegistry()


# Integration with form submission
async def register_form_completion(form_data: Dict[str, Any], booking_result: Dict[str, Any]):
    """
    Helper function to register form completion
    Called after successful booking
    """
    try:
        registry_id = await form_registry.register_completed_appointment(
            form_data,
            booking_result
        )
        
        # Add registry_id to booking result for reference
        booking_result['registry_id'] = registry_id
        
        # Log for monitoring
        logger.info(f"Form {form_data['form_id']} registered as {registry_id}")
        
        return registry_id
    except Exception as e:
        logger.error(f"Failed to register form completion: {e}")
        return None