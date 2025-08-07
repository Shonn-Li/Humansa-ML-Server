"""
Appointment Agent V2 - Complete implementation with form system
Handles validation, form lifecycle, and user ownership
"""
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
import logging
from datetime import datetime, timedelta
import uuid
import json

from src.humansa.v2.forms.form_tools import (
    create_appointment_form,
    update_appointment_form,
    submit_appointment_form,
    handle_form_confirmation
)
from src.humansa.v2.forms.models import FormStatus

logger = logging.getLogger(__name__)


class AppointmentAgentV2:
    """
    Enhanced appointment agent that:
    1. Validates required information
    2. Manages form lifecycle
    3. Handles user ownership and updates
    4. Returns structured responses for orchestrator
    """
    
    def __init__(self, llm=None, db_pool=None):
        self.llm = llm
        self.db_pool = db_pool
        
        # Define required fields for appointment
        self.required_fields = {
            'doctor': {
                'aliases': ['doctor_name', 'doctor', '医生', 'physician'],
                'prompt': '请问您想看哪位医生？',
                'validation': self._validate_doctor
            },
            'date': {
                'aliases': ['appointment_date', 'date', '日期', 'when'],
                'prompt': '您想什么时候就诊？',
                'validation': self._validate_date
            },
            'time': {
                'aliases': ['appointment_time', 'time', '时间', 'time_slot'],
                'prompt': '您想上午还是下午就诊？',
                'validation': self._validate_time
            },
            'symptoms': {
                'aliases': ['symptoms', 'condition', '症状', 'problem'],
                'prompt': '请描述您的症状或就诊原因',
                'validation': self._validate_symptoms
            }
        }
        
        # Mock doctor database
        self.available_doctors = {
            "李明": {"id": "doc_001", "name": "李明医生", "department": "内科", "specialty": "心血管"},
            "张伟": {"id": "doc_002", "name": "张伟医生", "department": "外科", "specialty": "骨科"},
            "王芳": {"id": "doc_003", "name": "王芳医生", "department": "儿科", "specialty": "儿童呼吸"},
            "刘洋": {"id": "doc_004", "name": "刘洋医生", "department": "皮肤科", "specialty": "皮肤过敏"},
            "陈静": {"id": "doc_005", "name": "陈静医生", "department": "妇科", "specialty": "妇产科"}
        }
    
    async def process_query(
        self,
        query: str,
        context: Dict[str, Any],
        user_id: str,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main entry point for appointment requests
        Returns structured responses that orchestrator can understand
        """
        logger.info(f"🏥 AppointmentAgentV2 processing: {query}")
        logger.info(f"   Context: {json.dumps(context, ensure_ascii=False)}")
        logger.info(f"   User ID: {user_id}")
        
        # Check if we have an active form
        form_id = context.get('active_form_id') or context.get('form_id')
        
        if form_id:
            # Handle existing form operations
            result = await self._handle_existing_form(form_id, query, user_id, context)
        else:
            # Try to create new appointment
            result = await self._handle_new_appointment(query, context, user_id)
        
        # Stream or return result
        if stream:
            yield result
        else:
            yield result
    
    async def _handle_new_appointment(
        self,
        query: str,
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Handle new appointment creation"""
        
        # Extract information from query and context
        extracted_info = self._extract_info(query, context)
        
        # Validate what we have
        validation = self._validate_info(extracted_info)
        
        if not validation['is_complete']:
            # Return what's missing
            return self._create_need_info_response(
                extracted_info,
                validation['missing'],
                validation['suggestions']
            )
        
        # We have complete info, create form
        try:
            # Build appointment query from extracted info
            appointment_query = self._build_appointment_query(extracted_info)
            
            # Create form
            form_result = await create_appointment_form(
                user_id=user_id,
                query=appointment_query,
                context=extracted_info
            )
            
            if form_result['success']:
                # Return form created response with form_id
                return {
                    'type': 'form_created',
                    'form_id': form_result['form_id'],
                    'content': form_result['preview'],
                    'action_required': 'user_confirmation',
                    'instructions': '请确认以上预约信息。回复"确认"完成预约，或告诉我需要修改的内容。',
                    'metadata': {
                        'form_status': form_result.get('status', 'draft'),
                        'expires_in': form_result.get('expires_in_minutes', 30)
                    }
                }
            else:
                return {
                    'type': 'error',
                    'content': form_result.get('message', '创建预约表单失败'),
                    'error_details': form_result.get('error')
                }
                
        except Exception as e:
            logger.error(f"Error creating appointment form: {e}")
            return {
                'type': 'error',
                'content': '创建预约时出现错误，请稍后重试',
                'error_details': str(e)
            }
    
    async def _handle_existing_form(
        self,
        form_id: str,
        query: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle operations on existing form"""
        
        query_lower = query.lower()
        
        # Determine user intent
        if any(word in query_lower for word in ['确认', '是的', '对的', '好的', 'ok']):
            # User confirms
            result = await submit_appointment_form(form_id, user_id)
            
            if result['success']:
                # Form submitted successfully
                return {
                    'type': 'appointment_confirmed',
                    'booking_id': result.get('booking_id'),
                    'confirmation_code': result.get('confirmation_code'),
                    'content': result.get('message'),
                    'form_id': form_id,  # Keep for reference
                    'metadata': {
                        'booking_details': result.get('booking_details'),
                        'next_steps': [
                            '请按时到达医院',
                            '携带身份证和医保卡',
                            '如需改期请提前24小时通知'
                        ]
                    }
                }
            else:
                return {
                    'type': 'booking_failed',
                    'content': result.get('message', '预约失败'),
                    'alternatives': result.get('alternatives', []),
                    'form_id': form_id
                }
        
        elif any(word in query_lower for word in ['取消', '不要', '算了']):
            # User cancels
            return {
                'type': 'appointment_cancelled',
                'content': '预约已取消。如需重新预约请告诉我。',
                'form_id': form_id
            }
        
        elif any(word in query_lower for word in ['修改', '改', '换']):
            # User wants to modify
            # Try to extract what they want to change
            update_result = await update_appointment_form(
                form_id=form_id,
                user_input=query,
                user_id=user_id
            )
            
            if update_result['success']:
                return {
                    'type': 'form_updated',
                    'form_id': form_id,
                    'content': update_result['preview'],
                    'updated_fields': update_result.get('updated_fields', []),
                    'action_required': 'user_confirmation',
                    'instructions': '预约信息已更新。请确认是否正确？'
                }
            else:
                return {
                    'type': 'update_failed',
                    'content': update_result.get('message'),
                    'form_id': form_id
                }
        
        else:
            # Try to handle as confirmation
            confirm_result = await handle_form_confirmation(
                user_input=query,
                form_id=form_id,
                user_id=user_id
            )
            
            return {
                'type': 'confirmation_handled',
                'content': confirm_result.get('message'),
                'action': confirm_result.get('action'),
                'form_id': form_id
            }
    
    def _extract_info(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract appointment information from query and context"""
        info = {}
        
        # First check context for accumulated information
        for field, config in self.required_fields.items():
            for alias in config['aliases']:
                if alias in context and context[alias]:
                    info[field] = context[alias]
                    break
        
        # Then extract from current query
        query_lower = query.lower()
        
        # Extract doctor
        if 'doctor' not in info:
            for doc_name, doc_info in self.available_doctors.items():
                if doc_name in query or doc_info['name'] in query:
                    info['doctor'] = doc_info['name']
                    info['doctor_id'] = doc_info['id']
                    info['department'] = doc_info['department']
                    break
        
        # Extract date
        if 'date' not in info:
            today = datetime.now().date()
            if '今天' in query:
                info['date'] = today.isoformat()
            elif '明天' in query:
                info['date'] = (today + timedelta(days=1)).isoformat()
            elif '后天' in query:
                info['date'] = (today + timedelta(days=2)).isoformat()
            # Add more date patterns as needed
        
        # Extract time
        if 'time' not in info:
            if '上午' in query:
                info['time'] = '09:00'
                info['time_preference'] = '上午'
            elif '下午' in query:
                info['time'] = '14:00'
                info['time_preference'] = '下午'
            elif '晚上' in query:
                info['time'] = '18:00'
                info['time_preference'] = '晚上'
        
        # Extract symptoms
        if 'symptoms' not in info:
            symptom_keywords = [
                '头痛', '头疼', '发烧', '发热', '咳嗽', '感冒',
                '胃痛', '腹痛', '失眠', '过敏', '皮疹'
            ]
            found_symptoms = [s for s in symptom_keywords if s in query]
            if found_symptoms:
                info['symptoms'] = '、'.join(found_symptoms)
        
        logger.info(f"Extracted info: {json.dumps(info, ensure_ascii=False)}")
        return info
    
    def _validate_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted information"""
        missing = []
        suggestions = []
        
        for field, config in self.required_fields.items():
            if field not in info or not info.get(field):
                missing.append({
                    'field': field,
                    'prompt': config['prompt']
                })
            elif 'validation' in config:
                # Run field-specific validation
                is_valid, suggestion = config['validation'](info.get(field))
                if not is_valid:
                    missing.append({
                        'field': field,
                        'prompt': config['prompt'],
                        'issue': suggestion
                    })
        
        # Generate suggestions based on partial info
        if 'symptoms' in info and 'doctor' not in info:
            # Suggest doctors based on symptoms
            suggestions.append(self._suggest_doctors_for_symptoms(info['symptoms']))
        
        return {
            'is_complete': len(missing) == 0,
            'missing': missing,
            'suggestions': suggestions
        }
    
    def _create_need_info_response(
        self,
        current_info: Dict[str, Any],
        missing: List[Dict[str, Any]],
        suggestions: List[str]
    ) -> Dict[str, Any]:
        """Create response for missing information"""
        
        # Build natural message
        if len(missing) == len(self.required_fields):
            # Missing everything
            content = "我来帮您预约看医生。请告诉我：\n"
            content += "- 您想看哪位医生或哪个科室？\n"
            content += "- 有什么症状需要就诊？\n"
            content += "- 什么时候方便？"
        else:
            # Missing some fields
            content = "预约还需要以下信息：\n"
            for item in missing:
                content += f"- {item['prompt']}\n"
        
        # Add suggestions
        if suggestions:
            content += "\n建议：\n"
            for suggestion in suggestions:
                content += f"{suggestion}\n"
        
        # Add available options
        response = {
            'type': 'need_more_info',
            'content': content,
            'missing_fields': [item['field'] for item in missing],
            'current_info': current_info
        }
        
        # Add specific options based on what's missing
        if any(item['field'] == 'doctor' for item in missing):
            response['available_doctors'] = [
                f"{doc['name']}（{doc['department']}）" 
                for doc in self.available_doctors.values()
            ]
        
        if any(item['field'] == 'time' for item in missing):
            response['available_times'] = ['上午（9:00-12:00）', '下午（14:00-17:00）', '晚上（18:00-20:00）']
        
        return response
    
    def _build_appointment_query(self, info: Dict[str, Any]) -> str:
        """Build natural language query from extracted info"""
        parts = []
        
        if 'doctor' in info:
            parts.append(f"预约{info['doctor']}")
        
        if 'department' in info:
            parts.append(f"{info['department']}")
        
        if 'date' in info:
            parts.append(f"{info['date']}")
        
        if 'time' in info:
            time_pref = info.get('time_preference', info['time'])
            parts.append(f"{time_pref}")
        
        if 'symptoms' in info:
            parts.append(f"症状：{info['symptoms']}")
        
        return '，'.join(parts)
    
    def _suggest_doctors_for_symptoms(self, symptoms: str) -> str:
        """Suggest appropriate doctors based on symptoms"""
        suggestions = []
        
        if any(s in symptoms for s in ['头痛', '头疼', '头晕']):
            suggestions.append("推荐内科或神经科医生")
        
        if any(s in symptoms for s in ['发烧', '发热', '咳嗽', '感冒']):
            suggestions.append("推荐内科或呼吸科医生")
        
        if any(s in symptoms for s in ['皮疹', '过敏', '皮肤']):
            suggestions.append("推荐皮肤科医生")
        
        return ' '.join(suggestions)
    
    # Validation methods
    def _validate_doctor(self, doctor: str) -> Tuple[bool, Optional[str]]:
        """Validate doctor selection"""
        # In real implementation, check against actual doctor database
        return True, None
    
    def _validate_date(self, date: str) -> Tuple[bool, Optional[str]]:
        """Validate appointment date"""
        try:
            date_obj = datetime.fromisoformat(date)
            if date_obj.date() < datetime.now().date():
                return False, "不能预约过去的日期"
            if date_obj.date() > datetime.now().date() + timedelta(days=30):
                return False, "只能预约30天内的号"
            return True, None
        except:
            return False, "日期格式不正确"
    
    def _validate_time(self, time: str) -> Tuple[bool, Optional[str]]:
        """Validate appointment time"""
        # Check if time is within clinic hours
        return True, None
    
    def _validate_symptoms(self, symptoms: str) -> Tuple[bool, Optional[str]]:
        """Validate symptoms description"""
        if len(symptoms) < 2:
            return False, "请详细描述症状"
        return True, None


# Example of how this integrates with orchestrator
"""
# In Pattern 2 orchestrator's appointment tool:

async def call_appointment_agent(query: str) -> str:
    # Build context from accumulated state
    context = {
        'doctor_name': self._current_state.get('mentioned_doctor'),
        'symptoms': self._current_state.get('mentioned_symptoms'),
        'date': self._current_state.get('mentioned_date'),
        'time': self._current_state.get('mentioned_time'),
        'active_form_id': self._current_state.get('active_form_id')
    }
    
    # Get appointment agent
    agent = AppointmentAgentV2(llm=self.llm, db_pool=self.db_pool)
    
    # Process query
    async for result in agent.process_query(
        query=query,
        context=context,
        user_id=self._current_state.user_id,
        stream=False
    ):
        # Handle different response types
        if result['type'] == 'need_more_info':
            # Store what we have so far
            if 'current_info' in result:
                for key, value in result['current_info'].items():
                    self._current_state[f'mentioned_{key}'] = value
            
            # Return message asking for missing info
            return result['content']
            
        elif result['type'] == 'form_created':
            # Store form_id for future reference
            self._current_state['active_form_id'] = result['form_id']
            
            # Return preview with instructions
            return f"{result['content']}\n\n{result['instructions']}"
            
        elif result['type'] == 'appointment_confirmed':
            # Clear appointment state
            self._current_state['active_form_id'] = None
            
            # Store booking info for user
            self._current_state['last_booking'] = {
                'booking_id': result.get('booking_id'),
                'confirmation_code': result.get('confirmation_code'),
                'form_id': result.get('form_id')
            }
            
            return result['content']
        
        # Handle other types...
        return result.get('content', '处理预约请求时出现错误')
"""