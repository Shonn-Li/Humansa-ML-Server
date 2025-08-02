"""
Enhanced Appointment Agent with Form Validation
The appointment agent is responsible for determining if it has enough information
and telling the orchestrator what's missing if it doesn't.
"""
import asyncio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from src.humansa.v2.forms.form_tools import create_appointment_form, submit_appointment_form
from src.humansa.v2.forms.models import FormStatus

logger = logging.getLogger(__name__)


class AppointmentAgentEnhanced:
    """
    Enhanced appointment agent that:
    1. Validates if it has enough information to book
    2. Returns what's missing if it can't proceed
    3. Creates and manages appointment forms
    """
    
    def __init__(self):
        # Define what information is required for booking
        self.required_fields = {
            'doctor': {
                'aliases': ['doctor_name', 'doctor', 'physician', '医生'],
                'description': '需要知道想看哪位医生或哪个科室'
            },
            'date': {
                'aliases': ['appointment_date', 'date', 'when', '日期', '时间'],
                'description': '需要知道什么时候就诊'
            },
            'time': {
                'aliases': ['appointment_time', 'time', 'time_slot', '时间段'],
                'description': '需要知道具体时间段（上午/下午/具体时间）'
            },
            'symptoms': {
                'aliases': ['symptoms', 'condition', 'problem', '症状', '问题'],
                'description': '需要知道什么症状或就诊原因'
            }
        }
        
    async def process_appointment_request(
        self,
        query: str,
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Main entry point for appointment requests.
        
        Returns one of:
        1. Need more information response
        2. Form preview for confirmation
        3. Booking confirmation
        """
        logger.info(f"🏥 Appointment Agent processing: {query}")
        
        # Step 1: Check what information we have
        extracted_info = self._extract_appointment_info(query, context)
        validation_result = self._validate_information(extracted_info)
        
        if not validation_result['is_complete']:
            # Tell orchestrator we need more information
            return self._create_need_info_response(
                extracted_info,
                validation_result['missing_fields']
            )
        
        # Step 2: Check if we have an active form in context
        form_id = context.get('active_form_id')
        
        if form_id:
            # We have a form, check its status
            return await self._handle_existing_form(form_id, query, user_id)
        else:
            # Create new form with complete information
            return await self._create_new_appointment_form(
                extracted_info,
                user_id
            )
    
    def _extract_appointment_info(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract appointment information from query and context"""
        info = {}
        
        # Check context first (previous conversation)
        for field, config in self.required_fields.items():
            # Check all aliases in context
            for alias in config['aliases']:
                if alias in context:
                    info[field] = context[alias]
                    break
        
        # Then check current query
        # This is simplified - in production, use NLP
        query_lower = query.lower()
        
        # Extract doctor
        if 'doctor' not in info:
            doctor_keywords = ['李明', '张医生', '王医生', '刘医生']
            for doc in doctor_keywords:
                if doc in query:
                    info['doctor'] = doc + '医生' if not doc.endswith('医生') else doc
                    break
        
        # Extract date
        if 'date' not in info:
            if '明天' in query:
                info['date'] = (datetime.now() + timedelta(days=1)).date()
            elif '后天' in query:
                info['date'] = (datetime.now() + timedelta(days=2)).date()
            elif '今天' in query:
                info['date'] = datetime.now().date()
        
        # Extract time
        if 'time' not in info:
            if '上午' in query:
                info['time'] = '上午'
            elif '下午' in query:
                info['time'] = '下午'
            elif '晚上' in query:
                info['time'] = '晚上'
        
        # Extract symptoms
        if 'symptoms' not in info:
            symptom_keywords = ['头痛', '发烧', '咳嗽', '胃痛', '失眠', '头晕']
            symptoms = [s for s in symptom_keywords if s in query]
            if symptoms:
                info['symptoms'] = '、'.join(symptoms)
        
        logger.info(f"Extracted info: {info}")
        return info
    
    def _validate_information(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if we have enough information to proceed"""
        missing_fields = []
        
        for field, config in self.required_fields.items():
            if field not in info or not info[field]:
                missing_fields.append({
                    'field': field,
                    'description': config['description']
                })
        
        return {
            'is_complete': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }
    
    def _create_need_info_response(
        self,
        current_info: Dict[str, Any],
        missing_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create response telling orchestrator we need more information"""
        
        # Build a natural language response about what's missing
        missing_descriptions = [field['description'] for field in missing_fields]
        
        response = {
            'status': 'need_more_info',
            'type': 'appointment_info_incomplete',
            'current_info': current_info,
            'missing_info': [field['field'] for field in missing_fields],
            'message': f"预约需要更多信息。{' '.join(missing_descriptions)}。",
            'suggestions': self._generate_suggestions(current_info, missing_fields)
        }
        
        # Add specific prompts for missing fields
        if any(field['field'] == 'doctor' for field in missing_fields):
            response['available_doctors'] = [
                {'name': '李明医生', 'department': '内科', 'title': '主任医师'},
                {'name': '张伟医生', 'department': '外科', 'title': '副主任医师'},
                {'name': '王芳医生', 'department': '儿科', 'title': '主治医师'}
            ]
        
        if any(field['field'] == 'time' for field in missing_fields):
            response['available_times'] = ['上午9:00-12:00', '下午14:00-17:00', '晚上18:00-20:00']
        
        return response
    
    def _generate_suggestions(
        self,
        current_info: Dict[str, Any],
        missing_fields: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate helpful suggestions for missing information"""
        suggestions = []
        
        # If we have symptoms but no doctor, suggest departments
        if 'symptoms' in current_info and any(f['field'] == 'doctor' for f in missing_fields):
            symptoms = current_info['symptoms']
            if '头痛' in symptoms or '头晕' in symptoms:
                suggestions.append("建议看神经内科或普通内科")
            elif '咳嗽' in symptoms or '发烧' in symptoms:
                suggestions.append("建议看呼吸内科或普通内科")
            elif '胃痛' in symptoms:
                suggestions.append("建议看消化内科")
        
        # If urgent symptoms, suggest immediate appointment
        if 'symptoms' in current_info:
            urgent_symptoms = ['胸痛', '呼吸困难', '严重头痛', '意识模糊']
            if any(s in current_info['symptoms'] for s in urgent_symptoms):
                suggestions.append("⚠️ 症状可能较严重，建议尽快就诊")
        
        return suggestions
    
    async def _create_new_appointment_form(
        self,
        info: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Create new appointment form with validated information"""
        
        # Build query string from extracted info
        query_parts = []
        if 'doctor' in info:
            query_parts.append(f"预约{info['doctor']}")
        if 'date' in info:
            date_str = info['date'].strftime('%Y年%m月%d日') if hasattr(info['date'], 'strftime') else str(info['date'])
            query_parts.append(date_str)
        if 'time' in info:
            query_parts.append(info['time'])
        if 'symptoms' in info:
            query_parts.append(f"症状：{info['symptoms']}")
        
        query = '，'.join(query_parts)
        
        # Create form using form tools
        result = await create_appointment_form(
            user_id=user_id,
            query=query,
            context=info
        )
        
        if result['success']:
            return {
                'status': 'form_created',
                'type': 'appointment_form_preview',
                'form_id': result['form_id'],
                'preview': result['preview'],
                'message': "预约信息已整理好，请确认：",
                'action_required': 'confirmation',
                'instructions': result.get('instructions', '请回复"确认"完成预约，或告诉我需要修改的内容')
            }
        else:
            return {
                'status': 'error',
                'type': 'form_creation_failed',
                'message': result.get('message', '创建预约表单失败'),
                'error': result.get('error')
            }
    
    async def _handle_existing_form(
        self,
        form_id: str,
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Handle operations on existing form"""
        
        # Determine user intent
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['确认', '好的', '可以', '没问题']):
            # User confirms
            result = await submit_appointment_form(form_id, user_id)
            
            if result['success']:
                return {
                    'status': 'booking_confirmed',
                    'type': 'appointment_booked',
                    'booking_id': result.get('booking_id'),
                    'confirmation_code': result.get('confirmation_code'),
                    'message': result.get('message'),
                    'next_steps': [
                        '请按时到达医院',
                        '记得携带身份证件',
                        '如需取消请提前通知'
                    ]
                }
            else:
                return {
                    'status': 'booking_failed',
                    'type': 'appointment_booking_error',
                    'message': result.get('message'),
                    'alternatives': result.get('alternatives', [])
                }
        
        elif any(word in query_lower for word in ['取消', '不要', '算了']):
            # User cancels
            return {
                'status': 'cancelled',
                'type': 'appointment_cancelled',
                'message': '预约已取消。如需重新预约请告诉我。'
            }
        
        else:
            # Assume user wants to modify
            return {
                'status': 'need_modification',
                'type': 'appointment_modification',
                'form_id': form_id,
                'message': '请告诉我您想修改什么内容',
                'current_form_id': form_id
            }


# Example of how orchestrator should use this
async def orchestrator_example():
    """
    Example of how the orchestrator should interact with appointment agent
    """
    appointment_agent = AppointmentAgentEnhanced()
    
    # Scenario 1: Missing information
    result = await appointment_agent.process_appointment_request(
        query="我想看医生",
        context={},
        user_id="user123"
    )
    
    if result['status'] == 'need_more_info':
        # Orchestrator should ask user for missing info
        print(f"Need to ask user for: {result['missing_info']}")
        print(f"Suggested message: {result['message']}")
    
    # Scenario 2: Complete information
    result = await appointment_agent.process_appointment_request(
        query="我想预约李明医生明天上午看病，最近头痛",
        context={},
        user_id="user123"
    )
    
    if result['status'] == 'form_created':
        # Orchestrator should show preview and ask for confirmation
        print(f"Show preview: {result['preview']}")
        print(f"Ask user: {result['instructions']}")