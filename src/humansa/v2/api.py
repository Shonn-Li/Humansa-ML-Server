from quart import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional
import json
import asyncio
from datetime import datetime
from llama_index.llms.openai import OpenAI
from llama_index.core.callbacks import CallbackManager
from .memory.memory_manager import MemoryManager
from .context_manager import ContextManager
from .workflows.orchestrator import HumansaOrchestrator
from .workflows.appointment_workflow import AppointmentBookingWorkflow
from .agents import (
    GeneralMedicalAgent,
    DiagnosisAgent,
    MedicationAgent,
    EmergencyTriageAgent,
    AppointmentAgent
)
from chat.streaming.sse_formatter import SSEFormatter
import logging

logger = logging.getLogger(__name__)

# Create v2 blueprint
humansa_v2_bp = Blueprint('humansa_v2', __name__)

# Global instances (would be initialized properly in production)
memory_manager: Optional[MemoryManager] = None
context_manager = ContextManager()
orchestrator: Optional[HumansaOrchestrator] = None
appointment_workflow: Optional[AppointmentBookingWorkflow] = None
sse_formatter = SSEFormatter()


async def initialize_v2_system(db_pool, openai_api_key: str):
    """Initialize the v2 Humansa system."""
    global memory_manager, orchestrator, appointment_workflow
    
    # Initialize memory manager
    memory_manager = MemoryManager(db_pool)
    await memory_manager.initialize_tables()
    
    # Initialize LLM
    llm = OpenAI(
        model="gpt-4",
        api_key=openai_api_key,
        temperature=0.7
    )
    
    # Initialize agents
    agents = [
        GeneralMedicalAgent(llm=llm),
        DiagnosisAgent(llm=llm),
        MedicationAgent(llm=llm),
        EmergencyTriageAgent(llm=llm),
        AppointmentAgent(llm=llm)
    ]
    
    # Initialize orchestrator
    orchestrator = HumansaOrchestrator(
        agents=agents,
        router_llm=llm,
        memory_manager=memory_manager
    )
    
    # Initialize appointment workflow
    appointment_workflow = AppointmentBookingWorkflow(db_pool=db_pool)
    
    logger.info("Humansa v2 system initialized successfully")


@humansa_v2_bp.route('/v2/humansa/chat', methods=['POST'])
async def chat_endpoint():
    """Main chat endpoint for Humansa v2."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id', 'anonymous')
        messages = data.get('messages', [])
        stream = data.get('stream', True)
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
            
        # Get latest user message
        user_message = messages[-1].get('content', '')
        
        # Create or get context
        context = context_manager.create_context(
            user_id=user_id,
            query=user_message
        )
        
        # Add conversation history
        for msg in messages[:-1]:
            context.conversation_history.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        
        if stream:
            return Response(
                stream_chat_response(user_id, user_message, context),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            result = await orchestrator.run(
                query=user_message,
                user_id=user_id
            )
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/appointment/search', methods=['POST'])
async def search_appointments():
    """Search for available appointments."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id', 'anonymous')
        search_criteria = data.get('search_criteria', {})
        
        # Get user context for preferences
        user_context = await memory_manager.get_user_context(user_id)
        
        result = await appointment_workflow.run(
            user_id=user_id,
            search_criteria=search_criteria,
            context=user_context
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in appointment search: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/appointment/book', methods=['POST'])
async def book_appointment():
    """Book a specific appointment slot."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        slot_id = data.get('slot_id')
        patient_info = data.get('patient_info', {})
        
        if not user_id or not slot_id:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Create booking through workflow
        result = await appointment_workflow.run(
            user_id=user_id,
            action="book",
            slot_id=slot_id,
            patient_info=patient_info
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in appointment booking: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/patient/profile', methods=['GET', 'PUT'])
async def patient_profile():
    """Get or update patient profile."""
    try:
        user_id = request.args.get('user_id') or (await request.get_json()).get('user_id')
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
            
        if request.method == 'GET':
            profile = await memory_manager.get_or_create_patient_profile(user_id)
            return jsonify(profile)
            
        else:  # PUT
            data = await request.get_json()
            await memory_manager.update_patient_profile(
                user_id=user_id,
                profile_data=data.get('profile_data'),
                medical_history=data.get('medical_history'),
                preferences=data.get('preferences')
            )
            return jsonify({"status": "updated"})
            
    except Exception as e:
        logger.error(f"Error with patient profile: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/conversation/history', methods=['GET'])
async def conversation_history():
    """Get conversation history for a user."""
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 10))
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
            
        history = await memory_manager.get_conversation_history(
            user_id=user_id,
            limit=limit
        )
        
        return jsonify({"history": history})
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/health', methods=['GET'])
async def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "orchestrator": orchestrator is not None,
            "memory_manager": memory_manager is not None,
            "appointment_workflow": appointment_workflow is not None
        }
    })


async def stream_chat_response(user_id: str, query: str, context):
    """Stream chat responses using SSE."""
    try:
        # Send initial connection message
        yield sse_formatter.format_sse({
            "type": "connection",
            "message": "Connected to Humansa v2"
        })
        
        # Process through orchestrator
        response_parts = []
        async for event in orchestrator.arun(
            query=query,
            user_id=user_id
        ):
            if isinstance(event, dict):
                # Handle different event types
                if event.get("type") == "agent_response":
                    content = event.get("content", "")
                    response_parts.append(content)
                    
                    yield sse_formatter.format_sse({
                        "type": "content",
                        "content": content,
                        "agent": event.get("agent_id")
                    })
                elif event.get("type") == "tool_call":
                    yield sse_formatter.format_sse({
                        "type": "tool_call",
                        "tool": event.get("tool_name"),
                        "agent": event.get("agent_id")
                    })
                elif event.get("type") == "citation":
                    yield sse_formatter.format_sse({
                        "type": "citation",
                        "citation": event.get("citation")
                    })
        
        # Send completion message
        yield sse_formatter.format_sse({
            "type": "done",
            "message": "Response complete",
            "full_response": "".join(response_parts)
        })
        
    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        yield sse_formatter.format_sse({
            "type": "error",
            "error": str(e)
        })


# Export blueprint and initialization function
__all__ = ['humansa_v2_bp', 'initialize_v2_system']