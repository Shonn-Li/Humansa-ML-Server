"""
Form-based tools for Pattern 2 appointment booking.
"""
import asyncio
from typing import Dict, Any, Optional
import logging
import re
from datetime import datetime, timedelta
import json

from .models import AppointmentForm, FormStatus
from .form_service import get_form_service
from .form_filling_agent import FormFillingAgent
from .mock_booking import mock_submit_appointment_form

logger = logging.getLogger(__name__)

# Initialize services
form_service = get_form_service()
form_filling_agent = FormFillingAgent()


async def create_appointment_form(
    user_id: str,
    query: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an appointment form from natural language query.
    
    This function:
    1. Uses FormFillingAgent to extract information
    2. Creates a form with extracted data
    3. Returns form_id and preview for confirmation
    
    Args:
        user_id: User ID
        query: Natural language appointment request
        context: Optional context with doctor/department info
    
    Returns:
        Dict with form_id, preview message, and status
    """
    try:
        logger.info(f"📋 Creating appointment form for user {user_id}")
        logger.info(f"   Query: {query}")
        
        # Step 1: Use FormFillingAgent to extract information
        extracted_data = form_filling_agent.fill_form_from_query(query, context)
        
        # Log extraction results
        logger.info(f"   Extraction confidence: {extracted_data.get('extraction_confidence', 0):.0%}")
        logger.info(f"   Missing fields: {extracted_data.get('missing_fields', [])}")
        
        # Step 2: Clean extracted data for form creation
        form_data = {}
        
        # Map extracted fields to form fields
        field_mapping = {
            'doctor_name': 'doctor_name',
            'doctor_id': 'doctor_id',
            'department': 'department',
            'appointment_date': 'date',  # Map to 'date' field
            'appointment_time': 'time_slot',  # Map to 'time_slot' field
            'symptoms': 'symptoms',
            'is_urgent': 'is_urgent',
            'doctor_title': 'doctor_title',
            'patient_name': 'patient_name',
            'patient_phone': 'patient_phone'
        }
        
        for extracted_key, form_key in field_mapping.items():
            if extracted_key in extracted_data:
                form_data[form_key] = extracted_data[extracted_key]
        
        # Step 3: Calculate fees if we have enough information
        if 'doctor_name' in form_data or 'department' in form_data:
            doctor_type = '普通门诊'  # Default
            if '专家' in query or (form_data.get('doctor_title') and '主任' in form_data.get('doctor_title', '')):
                doctor_type = '专家门诊'
            elif '特需' in query:
                doctor_type = '特需门诊'
            
            form_data['appointment_type'] = doctor_type
            
            # Calculate fees
            fees = form_service.calculate_fees(
                doctor_type, 
                form_data.get('department', '内科')
            )
            form_data.update(fees)
        
        # Step 4: Create form
        form = await form_service.create_form(user_id, form_data)
        
        # Step 5: Generate response based on completeness
        response = {
            'success': True,
            'form_id': form.form_id,
            'status': 'draft',
            'expires_in_minutes': 30
        }
        
        # Check if form is complete
        if form.is_complete():
            response['preview'] = form.get_preview_message()
            response['action_required'] = 'confirmation'
            response['instructions'] = '请确认以上预约信息是否正确？回复"确认"进行预约，或告诉我需要修改的内容。'
        else:
            # Form is incomplete
            missing_fields = extracted_data.get('missing_fields', [])
            missing_msg = "预约信息不完整，还需要提供：\n"
            
            field_prompts = {
                'doctor': '- 想看哪位医生？（如：李明医生）',
                'appointment_date': '- 想什么时候就诊？（如：明天、下周一）',
                'appointment_time': '- 想几点就诊？（如：上午9点）',
                'symptoms': '- 有什么症状？（如：头痛、发烧）'
            }
            
            for field in missing_fields:
                if field in field_prompts:
                    missing_msg += field_prompts[field] + "\n"
            
            # Add suggestions if available
            if extracted_data.get('suggestions'):
                missing_msg += "\n建议：\n"
                for suggestion in extracted_data['suggestions']:
                    if suggestion['type'] == 'doctor_recommendation':
                        missing_msg += "推荐医生：\n"
                        for doc in suggestion.get('doctors', []):
                            missing_msg += f"  - {doc['name']}（{doc['title']}）\n"
            
            response['preview'] = missing_msg
            response['action_required'] = 'provide_missing_info'
            response['missing_fields'] = missing_fields
        
        logger.info(f"✅ Form created with ID: {form.form_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error creating appointment form: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': '创建预约表单失败，请稍后重试'
        }


async def update_appointment_form(
    form_id: str,
    user_input: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Update appointment form based on user input.
    
    Args:
        form_id: Form ID to update
        user_input: Natural language update request
        user_id: User ID for validation
    
    Returns:
        Dict with updated preview
    """
    try:
        logger.info(f"📝 Updating form {form_id} based on: {user_input}")
        
        # Get form
        form = await form_service.get_form(form_id)
        if not form:
            return {
                'success': False,
                'error': 'Form not found',
                'message': '找不到该预约表单'
            }
        
        # Validate user
        if form.user_id != user_id:
            return {
                'success': False,
                'error': 'Unauthorized',
                'message': '您无权修改此预约'
            }
        
        # Check status
        if form.status != FormStatus.DRAFT:
            return {
                'success': False,
                'error': 'Form not editable',
                'message': '该预约已提交，无法修改'
            }
        
        # Use form filling agent to extract updates
        update_data = form_filling_agent.fill_form_from_query(user_input)
        
        # Also use form service's natural language parser
        nl_updates = form_service.parse_natural_language_updates(user_input)
        
        # Merge updates
        updates = {}
        for key in ['doctor_name', 'appointment_date', 'appointment_time', 'symptoms', 'department']:
            if key in update_data:
                updates[key] = update_data[key]
            elif key in nl_updates:
                updates[key] = nl_updates[key]
        
        # Update form
        if updates:
            success = await form_service.update_form(form_id, updates)
            if success:
                # Get updated form
                updated_form = await form_service.get_form(form_id)
                
                return {
                    'success': True,
                    'form_id': form_id,
                    'preview': updated_form.get_preview_message(),
                    'updated_fields': list(updates.keys()),
                    'message': '预约信息已更新',
                    'action_required': 'confirmation' if updated_form.is_complete() else 'provide_missing_info'
                }
        
        return {
            'success': False,
            'message': '未能识别修改内容，请说明要修改的具体信息'
        }
        
    except Exception as e:
        logger.error(f"Error updating form {form_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': '更新预约失败，请稍后重试'
        }


async def submit_appointment_form(
    form_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Submit confirmed appointment form for booking.
    
    Args:
        form_id: Form ID to submit
        user_id: User ID for validation
    
    Returns:
        Dict with booking result
    """
    try:
        logger.info(f"✅ Submitting form {form_id} for booking")
        
        # Get form
        form = await form_service.get_form(form_id)
        if not form:
            return {
                'success': False,
                'error': 'Form not found',
                'message': '找不到该预约表单'
            }
        
        # Validate user
        if form.user_id != user_id:
            return {
                'success': False,
                'error': 'Unauthorized',
                'message': '您无权提交此预约'
            }
        
        # Check if form is complete
        if not form.is_complete():
            return {
                'success': False,
                'error': 'Form incomplete',
                'message': '预约信息不完整，请补充必要信息',
                'preview': form.get_preview_message()
            }
        
        # Update status to submitted
        success = await form_service.update_form_status(form_id, FormStatus.SUBMITTED)
        if not success:
            return {
                'success': False,
                'error': 'Already submitted',
                'message': '该预约已经提交过了'
            }
        
        # Use mock booking service to simulate real booking
        booking_result = await mock_submit_appointment_form(
            form_id=form_id,
            form_data=form.to_dict()
        )
        
        if booking_result['success']:
            # Update form status to completed
            await form_service.update_form_status(form_id, FormStatus.COMPLETED)
            
            # Register completed appointment
            from .form_registry import register_form_completion
            registry_id = await register_form_completion(
                form.to_dict(),
                booking_result
            )
            
            # Add registry_id to result
            if registry_id:
                logger.info(f"✅ Appointment registered: {registry_id}")
            
            return {
                'success': True,
                'form_id': form_id,
                'booking_id': booking_result.get('booking_id'),
                'confirmation_code': booking_result.get('confirmation_code'),
                'message': booking_result.get('message'),
                'booking_details': booking_result.get('booking_details'),
                'registry_id': registry_id
            }
        else:
            # Booking failed, revert to confirmed status
            await form_service.update_form_status(form_id, FormStatus.CONFIRMED)
            
            return {
                'success': False,
                'error': booking_result.get('reason', 'booking_failed'),
                'message': booking_result.get('message', '预约失败，请稍后重试'),
                'alternatives': booking_result.get('alternatives')
            }
        
    except Exception as e:
        logger.error(f"Error submitting form {form_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': '提交预约失败，请稍后重试'
        }


async def handle_form_confirmation(
    user_input: str,
    form_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Handle user confirmation/cancellation response.
    
    Args:
        user_input: User's response text
        form_id: Form ID being confirmed
        user_id: User ID for validation
    
    Returns:
        Dict with action result
    """
    try:
        logger.info(f"🤝 Handling user response for form {form_id}: {user_input}")
        
        # Detect confirmation intent
        confirm_keywords = ['确认', '是的', '对的', '没错', '可以', '好的', 'ok', 'yes', '确定']
        cancel_keywords = ['取消', '不要', '算了', '放弃', 'no', '不是', '退出']
        modify_keywords = ['修改', '改', '换', '更改', '调整', '变更']
        
        user_input_lower = user_input.lower()
        
        # Check for confirmation
        if any(keyword in user_input_lower for keyword in confirm_keywords):
            logger.info("   User confirmed, submitting form...")
            return await submit_appointment_form(form_id, user_id)
        
        # Check for cancellation
        elif any(keyword in user_input_lower for keyword in cancel_keywords):
            logger.info("   User cancelled appointment")
            success = await form_service.update_form_status(form_id, FormStatus.CANCELLED)
            if success:
                return {
                    'success': True,
                    'action': 'cancelled',
                    'message': '预约已取消。如需重新预约，请告诉我您的需求。'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to cancel',
                    'message': '取消预约失败'
                }
        
        # Check for modification
        elif any(keyword in user_input_lower for keyword in modify_keywords):
            logger.info("   User wants to modify, processing update...")
            return await update_appointment_form(form_id, user_input, user_id)
        
        # Try to extract update intent from the input
        else:
            # Maybe user is providing missing information or updates
            logger.info("   Unclear intent, trying to update form with input...")
            update_result = await update_appointment_form(form_id, user_input, user_id)
            
            if update_result['success']:
                return update_result
            else:
                # Really unclear intent
                return {
                    'success': False,
                    'action': 'unclear',
                    'message': '请明确告诉我：\n- 回复"确认"完成预约\n- 回复"取消"放弃预约\n- 或直接告诉我需要修改的内容',
                    'options': ['确认预约', '取消预约', '修改信息']
                }
            
    except Exception as e:
        logger.error(f"Error handling confirmation: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': '处理确认失败，请稍后重试'
        }