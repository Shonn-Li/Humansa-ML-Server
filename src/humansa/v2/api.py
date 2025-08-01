from quart import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional, List
import json
import asyncio
import time
import os
from datetime import datetime
# from llama_index.llms.openai import OpenAI  # Commented out - using Azure OpenAI instead
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.callbacks import CallbackManager
from .memory.memory_manager import MemoryManager
from .memory.mem0_integration import Mem0MemoryManagerAdapter
from .context_manager import ContextManager
from .orchestrator_agent import HumansaOrchestratorAgent
from .workflows.appointment_workflow import AppointmentBookingWorkflow
from .mock_appointment_api import mock_appointment_system
from chat.streaming.sse_formatter import SSEFormatter
import logging

logger = logging.getLogger(__name__)

# Create v2 blueprint
humansa_v2_bp = Blueprint('humansa_v2', __name__)

# Global instances (would be initialized properly in production)
memory_manager: Optional[MemoryManager] = None
context_manager = ContextManager()
orchestrator: Optional[HumansaOrchestratorAgent] = None
appointment_workflow: Optional[AppointmentBookingWorkflow] = None
sse_formatter = SSEFormatter()


async def initialize_v2_system(db_pool, openai_api_key: str = None, use_subagent_architecture: bool = False):
    """Initialize the v2 Humansa system.
    
    Args:
        db_pool: Database connection pool
        openai_api_key: OpenAI API key (optional)
        use_subagent_architecture: Use new sub-agent architecture (default: False)
    """
    global memory_manager, orchestrator, appointment_workflow
    
    # Try to use Mem0 if available, otherwise fall back to basic memory manager
    try:
        from humansa.memory.mem0_manager import Mem0Manager
        mem0_manager = Mem0Manager.get_instance()
        
        # Initialize Mem0 if not already initialized
        if not mem0_manager.initialized:
            logger.info("Initializing Mem0 manager...")
            init_success = await mem0_manager.initialize()
            if init_success:
                logger.info("✅ Mem0 manager initialized successfully")
            else:
                logger.warning("❌ Mem0 manager initialization failed")
        
        if mem0_manager.initialized:
            # Use Mem0 adapter
            memory_manager = Mem0MemoryManagerAdapter(db_pool, mem0_manager)
            logger.info("Using Mem0 memory layer for Humansa v2")
        else:
            # Fall back to basic memory manager
            memory_manager = MemoryManager(db_pool)
            logger.info("Using basic memory manager (Mem0 not available)")
    except Exception as e:
        logger.warning(f"Failed to initialize Mem0 adapter: {e}")
        import traceback
        traceback.print_exc()
        memory_manager = MemoryManager(db_pool)
        
    await memory_manager.initialize_tables()
    
    # Initialize LLM with Azure OpenAI
    # Using GPT-4o as requested (not GPT-4)
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not azure_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY or AZURE_INFERENCE_CREDENTIAL must be set")
    
    llm = AzureOpenAI(
        model="gpt-4.1",  # Using GPT-4.1 as requested
        deployment_name="gpt-4.1",  # Azure deployment name
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        api_version="2024-02-15-preview",
        temperature=0.7,
        max_tokens=4096  # Increase from default to handle longer responses
    )
    
    # Create database config for tools
    db_config = {
        'host': db_pool.host if hasattr(db_pool, 'host') else None,
        'port': db_pool.port if hasattr(db_pool, 'port') else None,
        'database': db_pool.database if hasattr(db_pool, 'database') else None,
        'user': db_pool.user if hasattr(db_pool, 'user') else None,
        'password': db_pool.password if hasattr(db_pool, 'password') else None
    }
    
    # Initialize orchestrator - choose between architectures
    if use_subagent_architecture:
        # Use new sub-agent architecture
        logger.info("🚀 Initializing HUMANSA V2 with Sub-Agent Architecture")
        from .orchestrator_agent_subagent import create_subagent_orchestrator
        orchestrator = create_subagent_orchestrator(
            llm=llm,
            memory_manager=memory_manager,
            debug=True,
            db_config=db_config
        )
    else:
        # Use existing consolidated tools architecture
        logger.info("📦 Initializing HUMANSA V2 with Consolidated Tools")
        orchestrator = HumansaOrchestratorAgent(
            llm=llm,
            agents=None,  # Using tools instead of agent classes
            memory_manager=memory_manager,
            debug=True,  # Enable debug logging for agent flow visibility
            use_real_tools=True,  # Enable real database tools
            db_config=db_config  # Pass database config for tools
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
                stream_chat_response(user_id, user_message, messages),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming mode - collect all chunks from async generator
            result = None
            async for chunk in orchestrator.process_query(
                query=user_message,
                user_id=user_id,
                messages=messages,
                stream=False
            ):
                # Keep the last chunk which contains the full response
                result = chunk
            
            if result is None:
                return jsonify({"error": "No response from orchestrator"}), 500
                
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
        
        # Use mock appointment system directly
        result = await mock_appointment_system.search_appointments(search_criteria)
        
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
        
        # Use mock appointment system
        result = await mock_appointment_system.book_appointment(slot_id, patient_info)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in appointment booking: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/appointment/<appointment_id>', methods=['GET'])
async def get_appointment(appointment_id: str):
    """Get appointment details."""
    try:
        result = await mock_appointment_system.get_appointment(appointment_id)
        
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/appointment/<appointment_id>/cancel', methods=['POST'])
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment."""
    try:
        result = await mock_appointment_system.cancel_appointment(appointment_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/appointment/<appointment_id>/reschedule', methods=['POST'])
async def reschedule_appointment(appointment_id: str):
    """Reschedule an appointment."""
    try:
        data = await request.get_json()
        new_slot_id = data.get('new_slot_id')
        
        if not new_slot_id:
            return jsonify({"error": "new_slot_id is required"}), 400
        
        result = await mock_appointment_system.reschedule_appointment(appointment_id, new_slot_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {e}")
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


@humansa_v2_bp.route('/v2/humansa/memory/context/<user_id>', methods=['GET'])
async def get_memory_context(user_id: str):
    """Get memory context for a user."""
    try:
        # Get user context from memory manager
        context = await memory_manager.get_user_context(user_id)
        
        # Return the context wrapped properly
        return jsonify({
            "user_id": user_id,
            "context": context
        })
        
    except Exception as e:
        logger.error(f"Error getting memory context: {e}")
        return jsonify({
            "user_id": user_id,
            "context": {
                "memory_count": 0,
                "recent_memories": [],
                "user_id": user_id
            }
        })


@humansa_v2_bp.route('/v2/humansa/memory/status', methods=['GET'])
async def memory_status():
    """Check Mem0 initialization status."""
    try:
        if memory_manager and hasattr(memory_manager, 'mem0_manager'):
            # It's using Mem0
            mem0 = memory_manager.mem0_manager
            return jsonify({
                "initialized": mem0.initialized,
                "type": "mem0",
                "config": {
                    "vector_store": mem0.config.get("vector_store", {}).get("provider", "unknown"),
                    "embedding_model": mem0.config.get("embedder", {}).get("config", {}).get("model", "unknown")
                }
            })
        elif memory_manager:
            return jsonify({
                "initialized": True,
                "type": "basic",
                "config": {}
            })
        else:
            return jsonify({
                "initialized": False,
                "type": None,
                "config": {}
            })
    except Exception as e:
        logger.error(f"Error checking memory status: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/memory/add', methods=['POST'])
async def add_memory():
    """Add memory directly."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        messages = data.get('messages', [])
        metadata = data.get('metadata', {})
        
        if not user_id or not messages:
            return jsonify({"error": "user_id and messages required"}), 400
            
        # Extract conversation from messages
        if len(messages) >= 2:
            query = messages[-2].get('content', '') if messages[-2].get('role') == 'user' else ''
            response = messages[-1].get('content', '') if messages[-1].get('role') == 'assistant' else ''
            
            await memory_manager.add_conversation(
                user_id=str(user_id),
                query=query,
                response=response,
                metadata=metadata
            )
            
            return jsonify({"status": "added", "user_id": user_id})
        else:
            return jsonify({"error": "Need at least 2 messages"}), 400
            
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_bp.route('/v2/humansa/memory/search', methods=['POST'])
async def search_memory():
    """Search user memories."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        query = data.get('query', '')
        
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
            
        # Search memories
        if memory_manager and hasattr(memory_manager, 'search_memories'):
            results = await memory_manager.search_memories(
                user_id=str(user_id),
                query=query,
                limit=10
            )
            return jsonify({
                "user_id": user_id,
                "query": query,
                "count": len(results),
                "results": results
            })
        else:
            # Basic search in conversation history
            history = await memory_manager.get_conversation_history(
                user_id=str(user_id),
                limit=20
            )
            # Simple text search
            results = []
            for conv in history:
                if query.lower() in conv.get('query', '').lower() or query.lower() in conv.get('response', '').lower():
                    results.append(conv)
            
            return jsonify({
                "user_id": user_id,
                "query": query,
                "count": len(results),
                "results": results[:10]
            })
            
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
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


async def stream_chat_response(user_id: str, query: str, messages: List[Dict]):
    """Stream chat responses in OpenAI format."""
    try:
        # Process through orchestrator with streaming
        # Note: orchestrator.process_query returns an async generator
        async for chunk in orchestrator.process_query(
            query=query,
            user_id=user_id,
            messages=messages,
            stream=True
        ):
            # Convert to SSE format
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send final done message
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        import traceback
        traceback.print_exc()
        error_chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-4.1",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": f"Error: {str(e)}"
                },
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


# Export blueprint and initialization function
__all__ = ['humansa_v2_bp', 'initialize_v2_system']