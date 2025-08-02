"""
Service layer for form operations.
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging
import uuid
import re

from src.humansa.v2.forms.models import AppointmentForm, FormStatus

logger = logging.getLogger(__name__)


# Global form storage for testing (shared across instances)
_FORM_STORAGE: Dict[str, AppointmentForm] = {}

# Global instance
_form_service_instance = None


class FormService:
    """Service for managing appointment forms."""
    
    def __init__(self):
        """Initialize form service."""
        self.default_expiry_hours = 24
        # Use global form storage for testing
        self._forms = _FORM_STORAGE
    
    async def create_form(self, user_id: str, initial_data: Optional[Dict[str, Any]] = None) -> AppointmentForm:
        """Create a new appointment form."""
        form = AppointmentForm.create_new(user_id, initial_data)
        
        # Set expiration
        form.expires_at = datetime.now() + timedelta(hours=self.default_expiry_hours)
        
        # Store in memory for testing
        self._forms[form.form_id] = form
        logger.info(f"Created form {form.form_id} for user {user_id}")
        return form
    
    async def get_form(self, form_id: str) -> Optional[AppointmentForm]:
        """Get form by ID."""
        logger.info(f"Looking for form {form_id} in storage with {len(self._forms)} forms")
        logger.info(f"Available forms: {list(self._forms.keys())}")
        form = self._forms.get(form_id)
        if form:
            # Check if expired
            if form.expires_at and form.expires_at < datetime.now() and form.status == FormStatus.DRAFT:
                form.status = FormStatus.EXPIRED
                logger.info(f"Form {form_id} has expired")
        return form
    
    async def update_form(self, form_id: str, updates: Dict[str, Any]) -> bool:
        """Update form fields."""
        form = self._forms.get(form_id)
        if not form:
            return False
        
        # Apply updates
        form.update_from_dict(updates)
        logger.info(f"Updated form {form_id} with {len(updates)} fields")
        return True
    
    async def update_form_status(self, form_id: str, new_status: FormStatus) -> bool:
        """Update form status."""
        form = self._forms.get(form_id)
        if not form:
            return False
        
        form.status = new_status
        form.updated_at = datetime.now()
        
        if new_status == FormStatus.SUBMITTED:
            form.submitted_at = datetime.now()
        
        logger.info(f"Updated form {form_id} status to {new_status.value}")
        return True
    
    async def expire_old_forms(self) -> int:
        """Expire forms past their expiration time."""
        # In production, this would update database
        return 0
    
    def parse_natural_language_updates(self, user_input: str) -> Dict[str, Any]:
        """Parse natural language updates to form fields."""
        updates = {}
        
        # Extract date patterns
        date_patterns = [
            (r'明天', lambda: (datetime.now() + timedelta(days=1)).date()),
            (r'后天', lambda: (datetime.now() + timedelta(days=2)).date()),
            (r'大后天', lambda: (datetime.now() + timedelta(days=3)).date()),
            (r'下周一', lambda: self._next_weekday(0)),
            (r'下周二', lambda: self._next_weekday(1)),
            (r'下周三', lambda: self._next_weekday(2)),
            (r'下周四', lambda: self._next_weekday(3)),
            (r'下周五', lambda: self._next_weekday(4)),
            (r'(\d+)月(\d+)[日号]', lambda m: datetime(datetime.now().year, int(m.group(1)), int(m.group(2))).date()),
        ]
        
        for pattern, date_func in date_patterns:
            match = re.search(pattern, user_input)
            if match:
                try:
                    if callable(date_func):
                        updates['appointment_date'] = date_func(match) if match.groups() else date_func()
                    break
                except:
                    pass
        
        # Extract time patterns
        time_patterns = [
            (r'上午(\d+)点', lambda m: f"{int(m.group(1)):02d}:00"),
            (r'下午(\d+)点', lambda m: f"{int(m.group(1))+12:02d}:00"),
            (r'(\d+):(\d+)', lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"),
            (r'(\d+)点(\d+)分', lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"),
        ]
        
        for pattern, time_func in time_patterns:
            match = re.search(pattern, user_input)
            if match:
                try:
                    updates['appointment_time'] = time_func(match)
                    break
                except:
                    pass
        
        # Extract doctor name
        doctor_match = re.search(r'[改换]成(.{2,4})医生', user_input)
        if doctor_match:
            updates['doctor_name'] = doctor_match.group(1)
        
        # Extract symptoms
        symptom_match = re.search(r'症状[是为：:](.*?)(?:[，。,.]|$)', user_input)
        if symptom_match:
            updates['symptoms'] = symptom_match.group(1).strip()
        
        return updates
    
    def _next_weekday(self, weekday: int) -> datetime.date:
        """Get next occurrence of weekday (0=Monday)."""
        today = datetime.now().date()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def calculate_fees(self, doctor_type: str, department: str) -> Dict[str, float]:
        """Calculate appointment fees based on doctor type and department."""
        fees = {
            'consultation_fee': 0.0,
            'registration_fee': 0.0,
            'service_fee': 5.0,  # Fixed service fee
            'total_fee': 0.0
        }
        
        # Base fees by doctor type
        if '专家' in doctor_type:
            fees['consultation_fee'] = 100.0
            fees['registration_fee'] = 50.0
        elif '特需' in doctor_type:
            fees['consultation_fee'] = 200.0
            fees['registration_fee'] = 100.0
        else:
            fees['consultation_fee'] = 30.0
            fees['registration_fee'] = 20.0
        
        # Department adjustments
        if department in ['儿科', '急诊科']:
            fees['consultation_fee'] *= 1.2
        
        # Calculate total
        fees['total_fee'] = sum(fees[k] for k in ['consultation_fee', 'registration_fee', 'service_fee'])
        
        return fees


def get_form_service() -> FormService:
    """Get singleton instance of FormService"""
    global _form_service_instance
    if _form_service_instance is None:
        _form_service_instance = FormService()
    return _form_service_instance