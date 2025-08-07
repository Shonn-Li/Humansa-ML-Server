"""
Appointment Management Tools for Humansa V2
Handles booking confirmation, rescheduling, and cancellation
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time
import json
from ..postgres.database import HumansaDatabase
from ..memory.mem0_manager import Mem0Manager

logger = logging.getLogger(__name__)

class AppointmentManagementTools:
    """Tools for managing appointments including booking, rescheduling, and cancellation"""
    
    def __init__(self, db: HumansaDatabase, memory_manager: Mem0Manager):
        self.db = db
        self.memory = memory_manager
        
    def get_or_create_patient(self, user_id: str, phone: str, name: str, city: Optional[str] = None) -> Optional[str]:
        """Get existing patient or create new one"""
        try:
            # First check if patient exists by phone
            patient = self.db.get_patient_by_phone(phone)
            if patient:
                logger.info(f"Found existing patient: {patient['patient_id']}")
                return patient['patient_id']
            
            # Create new patient
            patient_id = f"PAT_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            success = self.db.create_patient(
                patient_id=patient_id,
                phone=phone,
                name=name,
                address=city
            )
            
            if success:
                logger.info(f"Created new patient: {patient_id}")
                return patient_id
            return None
            
        except Exception as e:
            logger.error(f"Error in get_or_create_patient: {e}")
            return None
    
    def book_appointment_structured(self, **kwargs) -> Dict[str, Any]:
        """
        Book an appointment with all required information
        
        Args:
            doctor_code: Doctor code
            patient_name: Patient's name
            patient_phone: Patient's phone number
            appointment_date: Date of appointment (YYYY-MM-DD)
            appointment_time: Time of appointment (HH:MM)
            city: Patient's city (optional)
            user_id: User ID for memory tracking
            
        Returns:
            Booking confirmation with appointment details
        """
        try:
            doctor_code = kwargs.get('doctor_code')
            patient_name = kwargs.get('patient_name')
            patient_phone = kwargs.get('patient_phone')
            appointment_date = kwargs.get('appointment_date')
            appointment_time = kwargs.get('appointment_time')
            city = kwargs.get('city')
            user_id = kwargs.get('user_id', 'default_user')
            
            # Validate required fields
            if not all([doctor_code, patient_name, patient_phone, appointment_date, appointment_time]):
                return {
                    'success': False,
                    'message': '缺少必要信息。需要：医生、患者姓名、电话、日期和时间',
                    'missing_fields': [
                        f for f in ['doctor_code', 'patient_name', 'patient_phone', 'appointment_date', 'appointment_time']
                        if not kwargs.get(f)
                    ]
                }
            
            # Get or create patient
            patient_id = self.get_or_create_patient(user_id, patient_phone, patient_name, city)
            if not patient_id:
                return {
                    'success': False,
                    'message': '创建患者信息失败'
                }
            
            # Check if slot is available
            availability = self.db.check_appointment_slot(doctor_code, appointment_date, appointment_time)
            if not availability['available']:
                return {
                    'success': False,
                    'message': '该时间段已被预约或不可用',
                    'suggestion': '请选择其他时间'
                }
            
            # Create appointment
            appointment_id = self.db.create_appointment(
                patient_id=patient_id,
                doctor_code=doctor_code,
                schedule_id=availability.get('schedule_id'),
                appointment_date=appointment_date,
                appointment_time=appointment_time
            )
            
            if appointment_id:
                # Store in memory for the user
                self.memory.add_memory(
                    user_id, 
                    f"预约成功：{appointment_date} {appointment_time} 看 {availability.get('doctor_name', doctor_code)} 医生，预约号：{appointment_id}"
                )
                
                return {
                    'success': True,
                    'appointment_id': appointment_id,
                    'patient_id': patient_id,
                    'doctor_name': availability.get('doctor_name'),
                    'clinic_name': availability.get('clinic_name'),
                    'appointment_date': appointment_date,
                    'appointment_time': appointment_time,
                    'message': f'预约成功！预约号：{appointment_id}',
                    'instructions': '请准时到达诊所，带好身份证件'
                }
            else:
                return {
                    'success': False,
                    'message': '预约失败，请稍后重试'
                }
                
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return {
                'success': False,
                'message': f'预约过程中出现错误：{str(e)}'
            }
    
    def get_appointment_history_structured(self, **kwargs) -> Dict[str, Any]:
        """Get appointment history for a patient"""
        try:
            phone = kwargs.get('phone')
            patient_id = kwargs.get('patient_id')
            user_id = kwargs.get('user_id', 'default_user')
            
            if not phone and not patient_id:
                return {
                    'success': False,
                    'message': '请提供手机号或患者ID'
                }
            
            # Get appointments
            appointments = self.db.get_patient_appointments(phone=phone, patient_id=patient_id)
            
            if appointments:
                # Store in memory
                self.memory.add_memory(
                    user_id,
                    f"查询到 {len(appointments)} 个预约记录"
                )
                
                return {
                    'success': True,
                    'appointments': appointments,
                    'total': len(appointments),
                    'message': f'找到 {len(appointments)} 个预约记录'
                }
            else:
                return {
                    'success': True,
                    'appointments': [],
                    'total': 0,
                    'message': '暂无预约记录'
                }
                
        except Exception as e:
            logger.error(f"Error getting appointment history: {e}")
            return {
                'success': False,
                'message': f'查询失败：{str(e)}'
            }
    
    def reschedule_appointment_structured(self, **kwargs) -> Dict[str, Any]:
        """Reschedule an existing appointment"""
        try:
            appointment_id = kwargs.get('appointment_id')
            new_date = kwargs.get('new_date')
            new_time = kwargs.get('new_time')
            phone = kwargs.get('phone')
            
            if not appointment_id and not phone:
                return {
                    'success': False,
                    'message': '请提供预约号或手机号'
                }
            
            if not all([new_date, new_time]):
                return {
                    'success': False,
                    'message': '请提供新的日期和时间'
                }
            
            # Get appointment details
            if not appointment_id and phone:
                # Find latest appointment for this phone
                appointments = self.db.get_patient_appointments(phone=phone)
                if not appointments:
                    return {
                        'success': False,
                        'message': '未找到您的预约记录'
                    }
                # Get the latest upcoming appointment
                upcoming = [a for a in appointments if a['status'] == 'confirmed']
                if not upcoming:
                    return {
                        'success': False,
                        'message': '没有可改期的预约'
                    }
                appointment_id = upcoming[0]['appointment_id']
            
            # Reschedule
            success = self.db.reschedule_appointment(appointment_id, new_date, new_time)
            
            if success:
                return {
                    'success': True,
                    'appointment_id': appointment_id,
                    'new_date': new_date,
                    'new_time': new_time,
                    'message': f'预约已成功改期到 {new_date} {new_time}'
                }
            else:
                return {
                    'success': False,
                    'message': '改期失败，该时间段可能不可用'
                }
                
        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {
                'success': False,
                'message': f'改期失败：{str(e)}'
            }
    
    def cancel_appointment_structured(self, **kwargs) -> Dict[str, Any]:
        """Cancel an appointment"""
        try:
            appointment_id = kwargs.get('appointment_id')
            phone = kwargs.get('phone')
            reason = kwargs.get('reason', '患者要求取消')
            
            if not appointment_id and not phone:
                return {
                    'success': False,
                    'message': '请提供预约号或手机号'
                }
            
            # Find appointment if only phone provided
            if not appointment_id and phone:
                appointments = self.db.get_patient_appointments(phone=phone)
                upcoming = [a for a in appointments if a['status'] == 'confirmed']
                if not upcoming:
                    return {
                        'success': False,
                        'message': '没有可取消的预约'
                    }
                appointment_id = upcoming[0]['appointment_id']
            
            # Cancel appointment
            success = self.db.cancel_appointment(appointment_id, reason)
            
            if success:
                return {
                    'success': True,
                    'appointment_id': appointment_id,
                    'message': '预约已成功取消',
                    'refund_policy': '如已付款，退款将在3-5个工作日内处理'
                }
            else:
                return {
                    'success': False,
                    'message': '取消失败，请联系客服'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {
                'success': False,
                'message': f'取消失败：{str(e)}'
            }
    
    def collect_appointment_info_structured(self, **kwargs) -> Dict[str, Any]:
        """
        Analyze what information is missing for appointment booking
        """
        try:
            current_info = kwargs.get('current_info', {})
            request_type = kwargs.get('request_type', 'booking')
            
            missing_fields = []
            
            if request_type == 'booking':
                required_fields = {
                    'city': '就诊城市',
                    'specialty': '科室',
                    'doctor_name': '医生姓名（可选）',
                    'preferred_date': '就诊日期',
                    'preferred_time': '就诊时间段（上午/下午）',
                    'patient_name': '您的姓名',
                    'patient_phone': '联系电话'
                }
                
                for field, description in required_fields.items():
                    if field not in current_info or not current_info[field]:
                        missing_fields.append({
                            'field': field,
                            'description': description,
                            'required': field not in ['doctor_name']
                        })
                
                if missing_fields:
                    # Prioritize what to ask first
                    priority_order = ['city', 'specialty', 'preferred_date', 'preferred_time', 'patient_name', 'patient_phone']
                    next_field = None
                    for field in priority_order:
                        if any(f['field'] == field for f in missing_fields):
                            next_field = field
                            break
                    
                    prompts = {
                        'city': '请问您想在哪个城市就诊？（如：北京、上海、深圳）',
                        'specialty': '请问您需要看哪个科室？（如：骨科、内科、儿科）',
                        'preferred_date': '请问您想预约哪一天？（如：明天、本周五、下周一）',
                        'preferred_time': '请问您希望上午还是下午就诊？',
                        'patient_name': '请提供您的姓名：',
                        'patient_phone': '请提供您的手机号码（用于接收预约确认）：'
                    }
                    
                    return {
                        'success': True,
                        'complete': False,
                        'missing_fields': missing_fields,
                        'next_question': prompts.get(next_field, '请提供缺失的信息'),
                        'next_field': next_field,
                        'collected_info': current_info
                    }
                else:
                    return {
                        'success': True,
                        'complete': True,
                        'message': '信息收集完整，可以进行预约',
                        'collected_info': current_info
                    }
            
        except Exception as e:
            logger.error(f"Error collecting appointment info: {e}")
            return {
                'success': False,
                'message': f'信息收集失败：{str(e)}'
            }

# Tool function wrappers for LlamaIndex
def book_appointment_tool(db: HumansaDatabase, memory: Mem0Manager):
    """Create appointment booking tool"""
    tools = AppointmentManagementTools(db, memory)
    
    def book_appointment(**kwargs):
        return tools.book_appointment_structured(**kwargs)
    
    return book_appointment

def get_appointment_history_tool(db: HumansaDatabase, memory: Mem0Manager):
    """Create appointment history tool"""
    tools = AppointmentManagementTools(db, memory)
    
    def get_appointment_history(**kwargs):
        return tools.get_appointment_history_structured(**kwargs)
    
    return get_appointment_history

def reschedule_appointment_tool(db: HumansaDatabase, memory: Mem0Manager):
    """Create reschedule tool"""
    tools = AppointmentManagementTools(db, memory)
    
    def reschedule_appointment(**kwargs):
        return tools.reschedule_appointment_structured(**kwargs)
    
    return reschedule_appointment

def cancel_appointment_tool(db: HumansaDatabase, memory: Mem0Manager):
    """Create cancel tool"""
    tools = AppointmentManagementTools(db, memory)
    
    def cancel_appointment(**kwargs):
        return tools.cancel_appointment_structured(**kwargs)
    
    return cancel_appointment

def collect_appointment_info_tool(db: HumansaDatabase, memory: Mem0Manager):
    """Create info collection tool"""
    tools = AppointmentManagementTools(db, memory)
    
    def collect_appointment_info(**kwargs):
        return tools.collect_appointment_info_structured(**kwargs)
    
    return collect_appointment_info