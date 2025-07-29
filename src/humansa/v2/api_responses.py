"""
Responses API for HUMANSA V2 - OpenAI-style stateful conversation management
"""

from quart import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional, List, AsyncGenerator
import json
import asyncio
import time
import uuid
from datetime import datetime
from llama_index.llms.openai import OpenAI
from .response_manager import ResponseManager
from .conversation_manager import ConversationManager
from .context_compressor import ContextCompressor
from .memory.memory_manager import MemoryManager
from .memory.mem0_integration import Mem0MemoryManagerAdapter
from .context_manager import ContextManager
from .orchestrator_agent import HumansaOrchestratorAgent
from .orchestrator_agent_enhanced import HumansaOrchestratorAgentEnhanced
from .orchestrator_agent_consolidated import HumansaOrchestratorAgentConsolidated
from chat.streaming.sse_formatter import SSEFormatter
import logging
import os

logger = logging.getLogger(__name__)

# Create v2 responses blueprint
humansa_v2_responses_bp = Blueprint('humansa_v2_responses', __name__)

# Global instances
conversation_manager: Optional[ConversationManager] = None
response_manager: Optional[ResponseManager] = None
context_compressor: Optional[ContextCompressor] = None
memory_manager: Optional[MemoryManager] = None
context_manager = ContextManager()
orchestrator: Optional[HumansaOrchestratorAgent] = None
enhanced_orchestrator: Optional[HumansaOrchestratorAgentEnhanced] = None
consolidated_orchestrator: Optional[HumansaOrchestratorAgentConsolidated] = None
sse_formatter = SSEFormatter()

# Check if enhanced logging is enabled
ENABLE_ENHANCED_LOGGING = os.getenv('HUMANSA_ENHANCED_LOGGING', 'true').lower() == 'true'
# Check if consolidated tools should be used
USE_CONSOLIDATED_TOOLS = os.getenv('HUMANSA_USE_CONSOLIDATED_TOOLS', 'true').lower() == 'true'


async def initialize_v2_responses_system(db_pool, openai_api_key: str):
    """Initialize the responses-based v2 Humansa system."""
    global memory_manager, orchestrator, enhanced_orchestrator, consolidated_orchestrator
    global context_compressor, conversation_manager, response_manager
    
    # Initialize LLM
    llm = OpenAI(
        api_key=openai_api_key,
        model="gpt-4-turbo-preview",
        temperature=0.7
    )
    
    # Initialize conversation and response managers
    conversation_manager = ConversationManager(max_context_tokens=8000, max_recent_messages=6)
    response_manager = ResponseManager(conversation_manager)
    
    # Initialize context compressor
    context_compressor = ContextCompressor(llm=llm)
    
    # Try to use Mem0 if available
    try:
        from humansa.memory.mem0_manager import Mem0Manager
        mem0_manager = Mem0Manager.get_instance()
        if mem0_manager.initialized:
            memory_manager = Mem0MemoryManagerAdapter(mem0_manager)
            logger.info("✅ Using Mem0 for memory management")
        else:
            memory_manager = MemoryManager(db_pool)
            logger.info("✅ Using basic memory manager (Mem0 not initialized)")
    except ImportError:
        memory_manager = MemoryManager(db_pool)
        logger.info("✅ Using basic memory manager")
    
    # Initialize orchestrators
    try:
        orchestrator = HumansaOrchestratorAgent(
            llm=llm,
            memory_manager=memory_manager,
            debug=False,
            use_real_tools=True,
            db_config={
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME', 'postgres'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', '')
            }
        )
        
        enhanced_orchestrator = HumansaOrchestratorAgentEnhanced(
            llm=llm,
            memory_manager=memory_manager,
            debug=True,
            use_real_tools=True,
            db_config={
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME', 'postgres'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', '')
            }
        )
        
        # Initialize consolidated orchestrator if enabled
        if USE_CONSOLIDATED_TOOLS:
            consolidated_orchestrator = HumansaOrchestratorAgentConsolidated(
                llm=llm,
                memory_manager=memory_manager,
                debug=False,
                use_real_tools=True,
                db_config={
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': int(os.getenv('DB_PORT', '5432')),
                    'database': os.getenv('DB_NAME', 'postgres'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', '')
                }
            )
            logger.info("✅ Consolidated orchestrator initialized (7 tools with dynamic loading)")
        
        logger.info("✅ Responses API orchestrators initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize orchestrators: {e}")
        raise


@humansa_v2_responses_bp.route('/v2/humansa/responses/create', methods=['POST'])
async def create_response():
    """
    Create a new response - OpenAI Responses API style
    
    Request body:
    {
        "model": "gpt-4-turbo",
        "input": "你好",
        "user_id": "user123",  # Optional if continuing
        "previous_response_id": "resp_abc123",  # Optional for continuation
        "metadata": {}  # Optional
    }
    
    Response:
    {
        "id": "resp_xyz789",
        "object": "response",
        "created": 1234567890,
        "model": "gpt-4-turbo",
        "conversation_id": "conv_123",
        "previous_response_id": "resp_abc123",
        "input": "你好",
        "output": [
            {
                "type": "text",
                "text": "您好！我是您的AI医疗助手..."
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
    """
    try:
        data = await request.get_json()
        model = data.get('model', 'gpt-4-turbo')
        input_text = data.get('input', '')
        user_id = data.get('user_id')
        previous_response_id = data.get('previous_response_id')
        metadata = data.get('metadata', {})
        
        if not input_text:
            return jsonify({"error": "Input is required"}), 400
        
        # Handle user_id for new conversations
        if not previous_response_id and not user_id:
            user_id = f'anonymous_{uuid.uuid4().hex[:8]}'
        
        # Get context if continuing from previous response
        if previous_response_id:
            context_messages, token_count = response_manager.get_context_for_response(
                previous_response_id,
                include_summary=True
            )
            
            # Check if we need compression
            if token_count > 6000:
                await compress_context_for_response(previous_response_id)
                context_messages, token_count = response_manager.get_context_for_response(
                    previous_response_id,
                    include_summary=True
                )
        else:
            context_messages = []
            token_count = 0
        
        logger.info(f"Processing response with {len(context_messages)} context messages ({token_count} tokens)")
        
        # Determine which orchestrator to use
        use_consolidated = USE_CONSOLIDATED_TOOLS and consolidated_orchestrator is not None
        use_enhanced = ENABLE_ENHANCED_LOGGING or data.get('debug', False)
        
        if use_consolidated:
            current_orchestrator = consolidated_orchestrator
            logger.info("🎯 Using consolidated orchestrator with dynamic tool loading")
        elif use_enhanced:
            current_orchestrator = enhanced_orchestrator
        else:
            current_orchestrator = orchestrator
        
        # Track start time
        start_time = time.time()
        
        # Process through orchestrator
        result = await current_orchestrator.process_query(
            query=input_text,
            user_id=user_id,
            messages=context_messages,
            stream=False
        )
        
        # Extract response content and metadata
        response_content = result.get('response', '')
        tools_used = result.get('tools_used', [])
        
        # Calculate token usage
        prompt_tokens = token_count + len(input_text) // 4  # Approximate
        completion_tokens = len(response_content) // 4  # Approximate
        total_tokens = prompt_tokens + completion_tokens
        
        # Create output format
        output = [{
            "type": "text",
            "text": response_content
        }]
        
        # Add tool outputs if any
        if result.get('tool_outputs'):
            for tool_output in result['tool_outputs']:
                output.append({
                    "type": "tool_output",
                    "tool": tool_output.get('tool'),
                    "output": tool_output.get('output')
                })
        
        # Create response record
        response = response_manager.create_response(
            user_id=user_id,
            model=model,
            input_text=input_text,
            output=output,
            previous_response_id=previous_response_id,
            metadata={
                **metadata,
                "processing_time": time.time() - start_time,
                "enhanced_logging": use_enhanced
            },
            tools_used=tools_used,
            token_usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        )
        
        return jsonify(response.to_dict())
        
    except Exception as e:
        logger.error(f"Error creating response: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_responses_bp.route('/v2/humansa/responses/<response_id>', methods=['GET'])
async def get_response(response_id: str):
    """
    Retrieve a response and its full conversation history
    """
    try:
        response = response_manager.get_response(response_id)
        if not response:
            return jsonify({"error": "Response not found"}), 404
        
        # Get full response chain
        chain = response_manager.get_response_chain(response_id)
        
        # Build full conversation history
        messages = []
        for resp in chain:
            messages.append({
                "role": "user",
                "content": resp.input,
                "timestamp": datetime.fromtimestamp(resp.created).isoformat()
            })
            messages.append({
                "role": "assistant",
                "content": response_manager._extract_text_from_output(resp.output),
                "timestamp": datetime.fromtimestamp(resp.created).isoformat(),
                "response_id": resp.id
            })
        
        # Get conversation state
        state = conversation_manager.get_conversation_state(response.conversation_id)
        
        result = {
            **response.to_dict(),
            "conversation_history": messages,
            "conversation_state": {
                "turn_count": state.turn_count if state else 0,
                "summary": state.summary if state else None,
                "key_facts": state.key_facts if state else []
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error retrieving response: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_responses_bp.route('/v2/humansa/responses/<response_id>/stream', methods=['POST'])
async def stream_response_continuation(response_id: str):
    """
    Stream a response continuation from a previous response
    """
    try:
        # Check if previous response exists
        previous_response = response_manager.get_response(response_id)
        if not previous_response:
            return jsonify({"error": "Previous response not found"}), 404
        
        data = await request.get_json()
        input_text = data.get('input', '')
        
        if not input_text:
            return jsonify({"error": "Input is required"}), 400
        
        # Stream response
        return Response(
            stream_response_generator(
                input_text=input_text,
                previous_response_id=response_id,
                user_id=previous_response.user_id,
                model=data.get('model', previous_response.model),
                metadata=data.get('metadata', {})
            ),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Error streaming response: {e}")
        return jsonify({"error": str(e)}), 500


async def stream_response_generator(
    input_text: str,
    previous_response_id: Optional[str],
    user_id: str,
    model: str,
    metadata: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Generate streaming response"""
    try:
        # Get context
        if previous_response_id:
            context_messages, token_count = response_manager.get_context_for_response(
                previous_response_id,
                include_summary=True
            )
        else:
            context_messages = []
            token_count = 0
        
        # Determine orchestrator
        use_consolidated = USE_CONSOLIDATED_TOOLS and consolidated_orchestrator is not None
        use_enhanced = ENABLE_ENHANCED_LOGGING or metadata.get('debug', False)
        
        if use_consolidated:
            current_orchestrator = consolidated_orchestrator
        elif use_enhanced:
            current_orchestrator = enhanced_orchestrator
        else:
            current_orchestrator = orchestrator
        
        # Track response content
        full_response = ""
        tools_used = []
        start_time = time.time()
        
        # Stream through orchestrator
        async for chunk in current_orchestrator.process_query(
            query=input_text,
            user_id=user_id,
            messages=context_messages,
            stream=True
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Accumulate content
            if 'choices' in chunk and chunk['choices']:
                delta = chunk['choices'][0].get('delta', {})
                if 'content' in delta:
                    full_response += delta['content']
                
                # Track tool usage
                if 'tool_calls' in delta:
                    for tool_call in delta['tool_calls']:
                        tools_used.append(tool_call.get('function', {}).get('name', ''))
        
        # Create response record after streaming completes
        if full_response:
            output = [{
                "type": "text",
                "text": full_response
            }]
            
            # Calculate token usage
            prompt_tokens = token_count + len(input_text) // 4
            completion_tokens = len(full_response) // 4
            
            response = response_manager.create_response(
                user_id=user_id,
                model=model,
                input_text=input_text,
                output=output,
                previous_response_id=previous_response_id,
                metadata={
                    **metadata,
                    "processing_time": time.time() - start_time,
                    "enhanced_logging": use_enhanced,
                    "streamed": True
                },
                tools_used=list(set(tools_used)),
                token_usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            )
            
            # Send final response metadata
            yield f"data: {json.dumps({'response_id': response.id, 'conversation_id': response.conversation_id})}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_response_generator: {e}")
        error_chunk = {
            "choices": [{
                "delta": {"content": f"Error: {str(e)}"},
                "finish_reason": "error"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@humansa_v2_responses_bp.route('/v2/humansa/responses/conversations/<conversation_id>/tree', methods=['GET'])
async def get_conversation_tree(conversation_id: str):
    """
    Get the full conversation tree showing all response branches
    """
    try:
        tree = response_manager.get_conversation_tree(conversation_id)
        if not tree:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Add statistics
        stats = response_manager.get_response_statistics(conversation_id)
        
        return jsonify({
            "tree": tree,
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation tree: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_responses_bp.route('/v2/humansa/responses/cleanup', methods=['POST'])
async def cleanup_responses():
    """
    Clean up old responses
    """
    try:
        data = await request.get_json()
        max_age_hours = data.get('max_age_hours', 24)
        
        # Clean up both managers
        response_manager.cleanup_old_responses(max_age_hours)
        conversation_manager.cleanup_old_conversations(max_age_hours)
        
        return jsonify({
            "message": f"Cleaned up responses older than {max_age_hours} hours"
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up responses: {e}")
        return jsonify({"error": str(e)}), 500


async def compress_context_for_response(response_id: str):
    """Compress context for a response chain"""
    try:
        chain = response_manager.get_response_chain(response_id)
        if not chain or len(chain) < 10:
            return
        
        conversation_id = chain[0].conversation_id
        
        # Build messages for compression
        messages = []
        for response in chain[:-5]:  # Keep last 5 uncompressed
            messages.append({"role": "user", "content": response.input})
            messages.append({
                "role": "assistant",
                "content": response_manager._extract_text_from_output(response.output)
            })
        
        # Compress
        summary, _ = await context_compressor.compress_conversation(
            messages,
            compression_type="medical_summary"
        )
        
        # Update conversation summary
        conversation_manager.update_summary(conversation_id, summary)
        
        logger.info(f"Compressed context for response chain ending at {response_id}")
        
    except Exception as e:
        logger.error(f"Error compressing context: {e}")