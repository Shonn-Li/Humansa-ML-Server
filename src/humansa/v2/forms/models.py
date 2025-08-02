"""
Form models for appointment booking system
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
import json


class FormStatus(str, Enum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation" 
    CONFIRMED = "confirmed"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class FormField:
    """Definition of a form field"""
    name: str
    type: str  # text, number, date, select, boolean, textarea
    label: str
    required: bool = False
    readonly: bool = False
    value: Any = None
    placeholder: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None  # For select fields
    validation: Optional[Dict[str, Any]] = None
    datasource: Optional[str] = None  # For dynamic options

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "label": self.label,
            "required": self.required,
            "readonly": self.readonly,
            "value": self.value,
            "placeholder": self.placeholder,
            "options": self.options,
            "validation": self.validation,
            "datasource": self.datasource
        }


@dataclass
class AppointmentForm:
    """Appointment booking form"""
    form_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    form_type: str = "appointment"
    user_id: str = ""
    conversation_id: Optional[str] = None
    status: FormStatus = FormStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=30))
    
    # Form data
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    speciality: Optional[str] = None
    clinic_name: Optional[str] = None
    date: Optional[str] = None
    time_slot: Optional[str] = None
    symptoms: Optional[str] = None
    is_urgent: bool = False
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    estimated_fee: Optional[float] = None
    
    # Metadata
    confirmed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    confirmation_code: Optional[str] = None
    submission_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(cls, user_id: str, initial_data: Optional[Dict[str, Any]] = None) -> 'AppointmentForm':
        """Create a new appointment form with initial data"""
        form = cls(user_id=user_id)
        
        if initial_data:
            # Map form data fields
            for field, value in initial_data.items():
                if hasattr(form, field) and value is not None:
                    setattr(form, field, value)
        
        return form

    def to_dict(self) -> Dict[str, Any]:
        """Convert form to dictionary"""
        return {
            "form_id": self.form_id,
            "form_type": self.form_type,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "form_data": {
                "doctor_id": self.doctor_id,
                "doctor_name": self.doctor_name,
                "speciality": self.speciality,
                "clinic_name": self.clinic_name,
                "date": self.date,
                "time_slot": self.time_slot,
                "symptoms": self.symptoms,
                "is_urgent": self.is_urgent,
                "patient_name": self.patient_name,
                "patient_phone": self.patient_phone,
                "estimated_fee": self.estimated_fee
            },
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "confirmation_code": self.confirmation_code,
            "submission_result": self.submission_result,
            "metadata": self.metadata
        }

    def to_form_data(self) -> Dict[str, Any]:
        """Get just the form data fields"""
        return {
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "speciality": self.speciality,
            "clinic_name": self.clinic_name,
            "date": self.date,
            "time_slot": self.time_slot,
            "symptoms": self.symptoms,
            "is_urgent": self.is_urgent,
            "patient_name": self.patient_name,
            "patient_phone": self.patient_phone,
            "estimated_fee": self.estimated_fee
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppointmentForm":
        """Create form from dictionary"""
        form_data = data.get("form_data", {})
        
        # Handle datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
            
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now()
            
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        elif not isinstance(expires_at, datetime):
            expires_at = datetime.now() + timedelta(minutes=30)
        
        return cls(
            form_id=data.get("form_id", str(uuid.uuid4())),
            form_type=data.get("form_type", "appointment"),
            user_id=data.get("user_id", ""),
            conversation_id=data.get("conversation_id"),
            status=FormStatus(data.get("status", "draft")),
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            doctor_id=form_data.get("doctor_id"),
            doctor_name=form_data.get("doctor_name"),
            speciality=form_data.get("speciality"),
            clinic_name=form_data.get("clinic_name"),
            date=form_data.get("date"),
            time_slot=form_data.get("time_slot"),
            symptoms=form_data.get("symptoms"),
            is_urgent=form_data.get("is_urgent", False),
            patient_name=form_data.get("patient_name"),
            patient_phone=form_data.get("patient_phone"),
            estimated_fee=form_data.get("estimated_fee"),
            confirmed_at=data.get("confirmed_at"),
            submitted_at=data.get("submitted_at"),
            confirmation_code=data.get("confirmation_code"),
            submission_result=data.get("submission_result"),
            metadata=data.get("metadata", {})
        )

    def get_missing_required_fields(self) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        
        # Required fields
        if not self.doctor_id:
            missing.append("doctor_id")
        if not self.date:
            missing.append("date")
        if not self.time_slot:
            missing.append("time_slot")
        if not self.symptoms:
            missing.append("symptoms")
        if not self.patient_name:
            missing.append("patient_name")
        if not self.patient_phone:
            missing.append("patient_phone")
            
        return missing

    def is_complete(self) -> bool:
        """Check if all required fields are filled"""
        return len(self.get_missing_required_fields()) == 0

    def generate_preview(self) -> str:
        """Generate human-readable preview"""
        lines = []
        
        if self.doctor_name:
            lines.append(f"医生：{self.doctor_name}")
        if self.speciality:
            lines.append(f"科室：{self.speciality}")
        if self.clinic_name:
            lines.append(f"诊所：{self.clinic_name}")
        if self.date and self.time_slot:
            lines.append(f"时间：{self.date} {self.time_slot}")
        elif self.date:
            lines.append(f"日期：{self.date}")
        if self.symptoms:
            lines.append(f"症状：{self.symptoms}")
        if self.is_urgent:
            lines.append("⚠️ 紧急预约")
        if self.estimated_fee:
            lines.append(f"预计费用：{self.estimated_fee}元")
            
        return "\n".join(lines)
    
    def get_preview_message(self) -> str:
        """Get preview message for display"""
        preview = self.generate_preview()
        if preview:
            return f"预约信息预览：\n{preview}"
        return "预约信息不完整"

    def generate_confirmation_message(self) -> str:
        """Generate confirmation message for user"""
        preview = self.generate_preview()
        missing = self.get_missing_required_fields()
        
        if missing:
            missing_labels = {
                "doctor_id": "医生",
                "date": "日期",
                "time_slot": "时间",
                "symptoms": "症状",
                "patient_name": "患者姓名",
                "patient_phone": "联系电话"
            }
            missing_text = "、".join([missing_labels.get(f, f) for f in missing])
            
            return f"""{preview}

还需要以下信息：{missing_text}
请提供缺失的信息以完成预约。"""
        else:
            return f"""预约信息如下：
━━━━━━━━━━━━━━━━━━
{preview}
━━━━━━━━━━━━━━━━━━

请确认以上信息是否正确？
- 回复"确认"完成预约
- 回复"修改"加具体内容（如"修改时间到下午"）
- 回复"取消"放弃预约"""