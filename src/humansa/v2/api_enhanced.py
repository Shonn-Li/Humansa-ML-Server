"""
Enhanced Humansa V2 API with detailed logging support
This version supports the enhanced orchestrator for better test visibility
"""

from quart import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional, List, AsyncGenerator
import json
import asyncio
import time
from datetime import datetime
from llama_index.llms.openai import OpenAI
from llama_index.core.callbacks import CallbackManager
from .memory.memory_manager import MemoryManager
from .memory.mem0_integration import Mem0MemoryManagerAdapter
from .context_manager import ContextManager
from .orchestrator_agent import HumansaOrchestratorAgent
from .orchestrator_agent_enhanced import HumansaOrchestratorAgentEnhanced
from .workflows.appointment_workflow import AppointmentBookingWorkflow
from chat.streaming.sse_formatter import SSEFormatter
import logging
import os

logger = logging.getLogger(__name__)

# Create v2 blueprint
humansa_v2_enhanced_bp = Blueprint('humansa_v2_enhanced', __name__)

# Global instances (would be initialized properly in production)
memory_manager: Optional[MemoryManager] = None
context_manager = ContextManager()
orchestrator: Optional[HumansaOrchestratorAgent] = None
enhanced_orchestrator: Optional[HumansaOrchestratorAgentEnhanced] = None
appointment_workflow: Optional[AppointmentBookingWorkflow] = None
sse_formatter = SSEFormatter()

# Check if enhanced logging is enabled via environment variable
# Default to true for better visibility of agent thinking process
ENABLE_ENHANCED_LOGGING = os.getenv('HUMANSA_ENHANCED_LOGGING', 'true').lower() == 'true'


async def initialize_v2_enhanced_system(db_pool, openai_api_key: str):
    """Initialize the enhanced v2 Humansa system."""
    global memory_manager, orchestrator, enhanced_orchestrator, appointment_workflow
    
    # Try to use Mem0 if available, otherwise fall back to basic memory manager
    try:
        from humansa.memory.mem0_manager import Mem0Manager
        mem0_manager = Mem0Manager.get_instance()
        if mem0_manager.initialized:
            # Use Mem0 adapter
            memory_manager = Mem0MemoryManagerAdapter(db_pool, mem0_manager)
            logger.info("Using Mem0 memory layer for Humansa v2 enhanced")
        else:
            # Fall back to basic memory manager
            memory_manager = MemoryManager(db_pool)
            logger.info("Using basic memory manager (Mem0 not available)")
    except Exception as e:
        logger.warning(f"Failed to initialize Mem0 adapter: {e}")
        memory_manager = MemoryManager(db_pool)
        
    await memory_manager.initialize_tables()
    
    # Initialize LLM
    llm = OpenAI(
        model="gpt-4",
        api_key=openai_api_key,
        temperature=0.7
    )
    
    # Initialize both orchestrators
    # Standard orchestrator
    orchestrator = HumansaOrchestratorAgent(
        llm=llm,
        agents=None,
        memory_manager=memory_manager,
        debug=True
    )
    
    # Enhanced orchestrator with detailed logging
    enhanced_orchestrator = HumansaOrchestratorAgentEnhanced(
        llm=llm,
        agents=None,
        memory_manager=memory_manager,
        debug=True,
        enable_enhanced_logging=True
    )
    
    # Initialize appointment workflow
    appointment_workflow = AppointmentBookingWorkflow(db_pool=db_pool)
    
    logger.info(f"Humansa v2 enhanced system initialized (Enhanced logging: {ENABLE_ENHANCED_LOGGING})")


@humansa_v2_enhanced_bp.route('/v2/humansa/chat', methods=['POST'])
async def chat_endpoint():
    """Main chat endpoint for Humansa v2 with enhanced logging support."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id', 'anonymous')
        messages = data.get('messages', [])
        stream = data.get('stream', True)
        debug = data.get('debug', False)  # Check if debug mode is requested
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
            
        # Get latest user message
        user_message = messages[-1].get('content', '')
        
        # Determine which orchestrator to use
        use_enhanced = debug or ENABLE_ENHANCED_LOGGING
        current_orchestrator = enhanced_orchestrator if use_enhanced else orchestrator
        
        logger.info(f"Using {'enhanced' if use_enhanced else 'standard'} orchestrator for user {user_id}")
        
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
                stream_chat_response_enhanced(
                    user_id, 
                    user_message, 
                    messages, 
                    current_orchestrator,
                    include_debug=debug
                ),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            result = await current_orchestrator.process_query(
                query=user_message,
                user_id=user_id,
                messages=messages,
                stream=False
            )
            
            # Add debug flag to response if requested
            if debug and 'debug' in result:
                result['_debug_enabled'] = True
                
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500


async def stream_chat_response_enhanced(
    user_id: str, 
    query: str, 
    messages: List[Dict],
    orchestrator_instance,
    include_debug: bool = False
) -> AsyncGenerator[str, None]:
    """Stream chat responses with optional debug information."""
    try:
        # Track debug events
        debug_events = []
        content_chunks = []
        
        # Process through orchestrator with streaming
        async for chunk in orchestrator_instance.process_query(
            query=query,
            user_id=user_id,
            messages=messages,
            stream=True
        ):
            # Check if this is a debug event
            if chunk.get('object') == 'debug.event' or chunk.get('type') == 'debug':
                debug_events.append(chunk.get('event', chunk))
                
                # If debug mode is on, stream debug events too
                if include_debug:
                    debug_chunk = {
                        "id": f"debug-{int(time.time()*1000)}",
                        "object": "debug.event",
                        "created": int(time.time()),
                        "model": "gpt-4",
                        "debug": chunk.get('event', chunk)
                    }
                    yield f"data: {json.dumps(debug_chunk)}\n\n"
            else:
                # Regular content chunk
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # Track content
                if 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        content_chunks.append(delta['content'])
        
        # Send summary event if debug mode
        if include_debug and debug_events:
            summary = {
                "id": f"summary-{int(time.time())}",
                "object": "debug.summary",
                "created": int(time.time()),
                "model": "gpt-4",
                "summary": {
                    "total_events": len(debug_events),
                    "agent_calls": len([e for e in debug_events if e.get('type') == 'tool_call_start']),
                    "thinking_steps": len([e for e in debug_events if e.get('type') == 'thinking_start']),
                    "memory_events": len([e for e in debug_events if e.get('type') in ['memory', 'mem0_check', 'memory_context']]),
                    "full_response": "".join(content_chunks)
                }
            }
            yield f"data: {json.dumps(summary)}\n\n"
        
        # Send final done message
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_chat_response_enhanced: {e}")
        error_chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": f"Error: {str(e)}"
                },
                "finish_reason": "stop"
            }],
            "error": str(e)
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@humansa_v2_enhanced_bp.route('/v2/humansa/health', methods=['GET'])
async def health_check():
    """Enhanced health check endpoint."""
    mem0_status = "not_initialized"
    if memory_manager and hasattr(memory_manager, 'mem0_manager'):
        mem0_status = "initialized" if memory_manager.mem0_manager.initialized else "not_initialized"
    
    return jsonify({
        "status": "healthy",
        "version": "2.0-enhanced",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "orchestrator": orchestrator is not None,
            "enhanced_orchestrator": enhanced_orchestrator is not None,
            "memory_manager": memory_manager is not None,
            "appointment_workflow": appointment_workflow is not None,
            "mem0": mem0_status
        },
        "enhanced_logging": ENABLE_ENHANCED_LOGGING
    })


# Include all other endpoints from the original api.py
@humansa_v2_enhanced_bp.route('/v2/humansa/appointment/search', methods=['POST'])
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


@humansa_v2_enhanced_bp.route('/v2/humansa/memory/status', methods=['GET'])
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


# Export blueprint and initialization function
__all__ = ['humansa_v2_enhanced_bp', 'initialize_v2_enhanced_system']