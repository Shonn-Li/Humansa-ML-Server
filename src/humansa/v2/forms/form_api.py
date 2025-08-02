"""
API endpoints for appointment form management
"""

from quart import Blueprint, request, jsonify
import logging
from typing import Dict, Any
import asyncpg

from .form_service import get_form_service
from .models import FormStatus

logger = logging.getLogger(__name__)

# Create blueprint
forms_bp = Blueprint('forms', __name__, url_prefix='/v1-humansa/forms')


async def get_db_pool() -> asyncpg.Pool:
    """Get database pool from app context"""
    from quart import current_app
    if not hasattr(current_app, 'db_pool'):
        raise RuntimeError("Database pool not initialized")
    return current_app.db_pool


@forms_bp.route('/create', methods=['POST'])
async def create_form():
    """
    Create a new appointment form
    
    Expected JSON body:
    {
        "user_id": "string",
        "conversation_id": "string (optional)",
        "initial_data": {
            "doctor_name": "string",
            "date": "YYYY-MM-DD",
            "time_slot": "HH:MM-HH:MM",
            "symptoms": "string",
            ...
        }
    }
    """
    try:
        data = await request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({"error": "user_id is required"}), 400
        
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Create form
        form = await form_service.create_form(
            user_id=data['user_id'],
            conversation_id=data.get('conversation_id'),
            initial_data=data.get('initial_data', {})
        )
        
        return jsonify({
            "success": True,
            "form": form.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating form: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/<form_id>', methods=['GET'])
async def get_form(form_id: str):
    """Get form by ID"""
    try:
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Get form
        form = await form_service.get_form(form_id)
        
        if not form:
            return jsonify({"error": "Form not found"}), 404
        
        return jsonify({
            "success": True,
            "form": form.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting form: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/<form_id>', methods=['PUT'])
async def update_form(form_id: str):
    """
    Update form data
    
    Expected JSON body:
    {
        "updates": {
            "doctor_name": "new value",
            "date": "new date",
            ...
        }
    }
    """
    try:
        data = await request.get_json()
        
        if not data or 'updates' not in data:
            return jsonify({"error": "updates field is required"}), 400
        
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Update form
        form = await form_service.update_form(form_id, data['updates'])
        
        if not form:
            return jsonify({"error": "Form not found"}), 404
        
        return jsonify({
            "success": True,
            "form": form.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating form: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/<form_id>/status', methods=['PUT'])
async def update_form_status(form_id: str):
    """
    Update form status
    
    Expected JSON body:
    {
        "status": "pending_confirmation" | "confirmed" | "submitted" | "cancelled",
        "additional_data": {
            "confirmation_code": "string",
            "submission_result": {...}
        }
    }
    """
    try:
        data = await request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({"error": "status field is required"}), 400
        
        # Validate status
        try:
            status = FormStatus(data['status'])
        except ValueError:
            return jsonify({"error": f"Invalid status: {data['status']}"}), 400
        
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Update status
        success = await form_service.update_form_status(
            form_id,
            status,
            data.get('additional_data')
        )
        
        if not success:
            return jsonify({"error": "Form not found or update failed"}), 404
        
        return jsonify({
            "success": True,
            "form_id": form_id,
            "new_status": status.value
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating form status: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/<form_id>/confirm', methods=['POST'])
async def confirm_form(form_id: str):
    """
    Confirm and submit form
    
    This is a convenience endpoint that:
    1. Updates status to confirmed
    2. Submits the form for booking
    """
    try:
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Get form
        form = await form_service.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
        
        # Check if form is complete
        if not form.is_complete():
            return jsonify({
                "error": "Form is incomplete",
                "missing_fields": form.get_missing_required_fields()
            }), 400
        
        # Update to confirmed
        await form_service.update_form_status(form_id, FormStatus.CONFIRMED)
        
        # Submit form (in real implementation, this would call actual booking API)
        import random
        confirmation_code = f"AP{random.randint(100000, 999999)}"
        
        booking_result = {
            "success": True,
            "appointment_id": f"APT_{form_id[:8]}",
            "confirmation_code": confirmation_code,
            "doctor": form.doctor_name,
            "date": form.date,
            "time": form.time_slot,
            "clinic": form.clinic_name,
            "fee": form.estimated_fee
        }
        
        # Update to submitted
        await form_service.update_form_status(
            form_id,
            FormStatus.SUBMITTED,
            {
                "confirmation_code": confirmation_code,
                "submission_result": booking_result
            }
        )
        
        return jsonify({
            "success": True,
            "booking_result": booking_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error confirming form: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/user/<user_id>', methods=['GET'])
async def get_user_forms(user_id: str):
    """
    Get all forms for a user
    
    Query params:
    - status: Filter by status
    - limit: Max number of forms (default 10)
    """
    try:
        # Get query params
        status = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Get forms
        forms = await form_service.get_user_forms(
            user_id,
            FormStatus(status) if status else None,
            limit
        )
        
        return jsonify({
            "success": True,
            "forms": [form.to_dict() for form in forms],
            "count": len(forms)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user forms: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/parse', methods=['POST'])
async def parse_natural_language():
    """
    Parse natural language to form updates
    
    Expected JSON body:
    {
        "user_input": "改到明天下午3点",
        "current_form": {...}  // Optional current form data
    }
    """
    try:
        data = await request.get_json()
        
        if not data or 'user_input' not in data:
            return jsonify({"error": "user_input is required"}), 400
        
        # Get database pool
        db_pool = await get_db_pool()
        form_service = get_form_service()
        
        # Parse updates
        from .models import AppointmentForm
        current_form = None
        if 'current_form' in data:
            current_form = AppointmentForm.from_dict(data['current_form'])
        
        updates = await form_service.parse_form_updates(
            data['user_input'],
            current_form
        )
        
        return jsonify({
            "success": True,
            "parsed_updates": updates
        }), 200
        
    except Exception as e:
        logger.error(f"Error parsing natural language: {e}")
        return jsonify({"error": str(e)}), 500


@forms_bp.route('/templates', methods=['GET'])
async def get_form_templates():
    """Get available form templates"""
    try:
        # Get database pool
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, form_type, name, description, schema, ui_config
                FROM appointment_form_templates
                ORDER BY id
            """)
        
        templates = []
        for row in rows:
            templates.append({
                "id": row['id'],
                "form_type": row['form_type'],
                "name": row['name'],
                "description": row['description'],
                "schema": row['schema'],
                "ui_config": row['ui_config']
            })
        
        return jsonify({
            "success": True,
            "templates": templates
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({"error": str(e)}), 500


# Health check endpoint
@forms_bp.route('/health', methods=['GET'])
async def health_check():
    """Health check for forms API"""
    try:
        # Test database connection
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return jsonify({
            "status": "healthy",
            "service": "appointment_forms"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503