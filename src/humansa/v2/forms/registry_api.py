"""
Registry API endpoints for appointment history and analytics
"""
from quart import Blueprint, request, jsonify
from typing import Dict, Any
import logging

from .form_registry import form_registry

logger = logging.getLogger(__name__)

# Create registry blueprint
registry_bp = Blueprint('form_registry', __name__)


@registry_bp.route('/api/v2/appointments/history', methods=['GET'])
async def get_appointment_history():
    """
    Get user's appointment history
    
    Query params:
    - user_id: User ID (required)
    - limit: Max number of appointments to return (default: 10)
    - include_cancelled: Include cancelled appointments (default: false)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        limit = int(request.args.get('limit', 10))
        include_cancelled = request.args.get('include_cancelled', 'false').lower() == 'true'
        
        # Get appointment history
        appointments = await form_registry.get_user_appointment_history(
            user_id=user_id,
            limit=limit,
            include_cancelled=include_cancelled
        )
        
        # Convert to dict format
        history = [appt.to_dict() for appt in appointments]
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'total': len(history),
            'appointments': history
        })
        
    except Exception as e:
        logger.error(f"Error getting appointment history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@registry_bp.route('/api/v2/appointments/upcoming', methods=['GET'])
async def get_upcoming_appointments():
    """
    Get user's upcoming appointments
    
    Query params:
    - user_id: User ID (required)
    - days_ahead: Number of days to look ahead (default: 7)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        days_ahead = int(request.args.get('days_ahead', 7))
        
        # Get upcoming appointments
        appointments = await form_registry.get_upcoming_appointments(
            user_id=user_id,
            days_ahead=days_ahead
        )
        
        # Convert to dict format
        upcoming = [appt.to_dict() for appt in appointments]
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'days_ahead': days_ahead,
            'total': len(upcoming),
            'appointments': upcoming
        })
        
    except Exception as e:
        logger.error(f"Error getting upcoming appointments: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@registry_bp.route('/api/v2/appointments/<booking_id>', methods=['GET'])
async def get_appointment_by_booking(booking_id: str):
    """Get appointment details by booking ID"""
    try:
        appointment = await form_registry.get_appointment_by_booking_id(booking_id)
        
        if not appointment:
            return jsonify({
                'success': False,
                'error': 'Appointment not found'
            }), 404
        
        return jsonify({
            'success': True,
            'appointment': appointment.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting appointment {booking_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@registry_bp.route('/api/v2/appointments/<booking_id>/cancel', methods=['POST'])
async def cancel_appointment(booking_id: str):
    """Cancel an appointment"""
    try:
        data = await request.get_json()
        reason = data.get('reason', '用户取消')
        
        success = await form_registry.update_appointment_status(
            booking_id=booking_id,
            status='cancelled',
            reason=reason
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Appointment not found or already cancelled'
            }), 404
        
        return jsonify({
            'success': True,
            'message': '预约已成功取消',
            'booking_id': booking_id
        })
        
    except Exception as e:
        logger.error(f"Error cancelling appointment {booking_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@registry_bp.route('/api/v2/appointments/analytics', methods=['GET'])
async def get_appointment_analytics():
    """
    Get appointment analytics
    
    Query params:
    - user_id: Optional user ID for user-specific analytics
    """
    try:
        user_id = request.args.get('user_id')
        
        analytics = await form_registry.get_analytics(user_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@registry_bp.route('/api/v2/appointments/export', methods=['GET'])
async def export_appointment_history():
    """
    Export user's complete appointment history
    
    Query params:
    - user_id: User ID (required)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        export_data = form_registry.export_user_history(user_id)
        
        return jsonify({
            'success': True,
            'export': export_data
        })
        
    except Exception as e:
        logger.error(f"Error exporting history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500