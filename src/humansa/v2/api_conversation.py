"""
Conversation-based Humansa V2 API following OpenAI's pattern
Manages conversation IDs server-side and supports extending conversations
"""

from quart import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional, List, AsyncGenerator
import json
import asyncio
import time
import uuid
from datetime import datetime
from llama_index.llms.openai import OpenAI
from .conversation_manager import ConversationManager
from .context_compressor import ContextCompressor
from .memory.memory_manager import MemoryManager
from .memory.mem0_integration import Mem0MemoryManagerAdapter
from .context_manager import ContextManager
from .orchestrator_agent import HumansaOrchestratorAgent
from .orchestrator_agent_enhanced import HumansaOrchestratorAgentEnhanced
from chat.streaming.sse_formatter import SSEFormatter
import logging
import os

logger = logging.getLogger(__name__)

# Create v2 conversation blueprint
humansa_v2_conversation_bp = Blueprint('humansa_v2_conversation', __name__)

# Global instances
conversation_manager = ConversationManager(max_context_tokens=8000, max_recent_messages=6)
context_compressor: Optional[ContextCompressor] = None
memory_manager: Optional[MemoryManager] = None
context_manager = ContextManager()
orchestrator: Optional[HumansaOrchestratorAgent] = None
enhanced_orchestrator: Optional[HumansaOrchestratorAgentEnhanced] = None
sse_formatter = SSEFormatter()

# Check if enhanced logging is enabled
ENABLE_ENHANCED_LOGGING = os.getenv('HUMANSA_ENHANCED_LOGGING', 'true').lower() == 'true'

# Store active conversations (in production, use Redis or similar)
active_conversations: Dict[str, Dict[str, Any]] = {}


async def initialize_v2_conversation_system(db_pool, openai_api_key: str):
    """Initialize the conversation-based v2 Humansa system."""
    global memory_manager, orchestrator, enhanced_orchestrator, context_compressor
    
    # Initialize LLM
    llm = OpenAI(
        api_key=openai_api_key,
        model="gpt-4-turbo-preview",
        temperature=0.7
    )
    
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
        
        logger.info("✅ Orchestrators initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize orchestrators: {e}")
        raise


@humansa_v2_conversation_bp.route('/v2/humansa/conversations', methods=['POST'])
async def create_conversation():
    """
    Create a new conversation - OpenAI style
    Request body:
    {
        "user_id": "user123",
        "message": {
            "role": "user",
            "content": "你好"
        }
    }
    
    Response:
    {
        "conversation_id": "conv_abc123",
        "created": 1234567890,
        "message": {
            "role": "assistant",
            "content": "..."
        }
    }
    """
    try:
        data = await request.get_json()
        user_id = data.get('user_id', f'anonymous_{uuid.uuid4().hex[:8]}')
        message = data.get('message', {})
        
        if not message or not message.get('content'):
            return jsonify({"error": "Message content is required"}), 400
        
        # Create new conversation
        conversation_id = conversation_manager.create_conversation(user_id)
        
        # Add user message
        conversation_manager.add_message(conversation_id, "user", message['content'])
        
        # Store conversation metadata
        active_conversations[conversation_id] = {
            "user_id": user_id,
            "created": int(datetime.now().timestamp()),
            "last_updated": int(datetime.now().timestamp())
        }
        
        # Process the message
        response = await process_conversation_turn(conversation_id, message['content'], user_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "created": active_conversations[conversation_id]["created"],
            "message": response
        })
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_conversation_bp.route('/v2/humansa/conversations/<conversation_id>/messages', methods=['POST'])
async def add_message_to_conversation(conversation_id: str):
    """
    Add a message to existing conversation - OpenAI style
    Request body:
    {
        "message": {
            "role": "user",
            "content": "我想预约医生"
        }
    }
    
    Response:
    {
        "conversation_id": "conv_abc123",
        "message": {
            "role": "assistant",
            "content": "..."
        }
    }
    """
    try:
        # Check if conversation exists
        if conversation_id not in active_conversations:
            return jsonify({"error": "Conversation not found"}), 404
        
        data = await request.get_json()
        message = data.get('message', {})
        
        if not message or not message.get('content'):
            return jsonify({"error": "Message content is required"}), 400
        
        # Get user_id from conversation
        user_id = active_conversations[conversation_id]["user_id"]
        
        # Add user message
        conversation_manager.add_message(conversation_id, "user", message['content'])
        
        # Update last_updated
        active_conversations[conversation_id]["last_updated"] = int(datetime.now().timestamp())
        
        # Process the message
        response = await process_conversation_turn(conversation_id, message['content'], user_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "message": response
        })
        
    except Exception as e:
        logger.error(f"Error adding message to conversation: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_conversation_bp.route('/v2/humansa/conversations/<conversation_id>', methods=['GET'])
async def get_conversation(conversation_id: str):
    """
    Get conversation details and history
    """
    try:
        if conversation_id not in active_conversations:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Get conversation state
        state = conversation_manager.get_conversation_state(conversation_id)
        if not state:
            return jsonify({"error": "Conversation state not found"}), 404
        
        # Get message history
        history = conversation_manager.get_conversation_history(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "user_id": state.user_id,
            "created": int(state.created_at.timestamp()),
            "last_updated": int(state.last_updated.timestamp()),
            "turn_count": state.turn_count,
            "summary": state.summary,
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp")
                }
                for msg in history
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_conversation_bp.route('/v2/humansa/conversations/<conversation_id>/stream', methods=['POST'])
async def stream_conversation(conversation_id: str):
    """
    Stream response for conversation - SSE endpoint
    """
    try:
        if conversation_id not in active_conversations:
            return jsonify({"error": "Conversation not found"}), 404
        
        data = await request.get_json()
        message = data.get('message', {})
        
        if not message or not message.get('content'):
            return jsonify({"error": "Message content is required"}), 400
        
        # Get user_id from conversation
        user_id = active_conversations[conversation_id]["user_id"]
        
        # Add user message
        conversation_manager.add_message(conversation_id, "user", message['content'])
        
        # Stream response
        return Response(
            stream_conversation_response(conversation_id, message['content'], user_id),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Error streaming conversation: {e}")
        return jsonify({"error": str(e)}), 500


async def process_conversation_turn(conversation_id: str, user_message: str, user_id: str) -> Dict[str, str]:
    """
    Process a conversation turn with context management
    """
    try:
        # Get optimized context window
        context_messages, token_count = conversation_manager.get_context_window(conversation_id)
        
        logger.info(f"Processing turn with {len(context_messages)} context messages ({token_count} tokens)")
        
        # Check if we need to compress
        if token_count > 6000:  # Leave room for response
            # Compress older messages
            state = conversation_manager.get_conversation_state(conversation_id)
            if state and len(context_messages) > 5:
                summary = await context_compressor.compress_conversation(
                    context_messages[:-3],  # Compress all but last 3
                    compression_type="medical_summary"
                )
                conversation_manager.update_summary(conversation_id, summary[0])
                
                # Get new optimized context
                context_messages, token_count = conversation_manager.get_context_window(conversation_id)
                logger.info(f"Compressed context to {token_count} tokens")
        
        # Determine which orchestrator to use
        use_enhanced = ENABLE_ENHANCED_LOGGING
        current_orchestrator = enhanced_orchestrator if use_enhanced else orchestrator
        
        # Process through orchestrator
        result = await current_orchestrator.process_query(
            query=user_message,
            user_id=user_id,
            messages=context_messages,
            stream=False
        )
        
        # Extract response content
        response_content = result.get('response', '')
        
        # Add assistant response to conversation
        conversation_manager.add_message(conversation_id, "assistant", response_content)
        
        # Extract and store key facts if any
        if context_compressor:
            key_info = await context_compressor.extract_key_information(
                conversation_manager.get_conversation_history(conversation_id, last_n=2)
            )
            if key_info:
                for key, value in key_info.items():
                    if value and key in ['allergies', 'medications', 'medical_history']:
                        conversation_manager.add_key_fact(conversation_id, {
                            "type": key,
                            "value": value
                        })
        
        return {
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing conversation turn: {e}")
        return {
            "role": "assistant",
            "content": f"抱歉，处理您的请求时遇到了问题：{str(e)}",
            "timestamp": datetime.now().isoformat()
        }


async def stream_conversation_response(conversation_id: str, user_message: str, user_id: str) -> AsyncGenerator[str, None]:
    """
    Stream conversation response with context management
    """
    try:
        # Get optimized context window
        context_messages, token_count = conversation_manager.get_context_window(conversation_id)
        
        # Determine which orchestrator to use
        use_enhanced = ENABLE_ENHANCED_LOGGING
        current_orchestrator = enhanced_orchestrator if use_enhanced else orchestrator
        
        # Accumulate response for storage
        full_response = ""
        
        # Process through orchestrator with streaming
        async for chunk in current_orchestrator.process_query(
            query=user_message,
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
        
        # Add complete response to conversation
        if full_response:
            conversation_manager.add_message(conversation_id, "assistant", full_response)
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_conversation_response: {e}")
        error_chunk = {
            "choices": [{
                "delta": {"content": f"Error: {str(e)}"},
                "finish_reason": "error"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@humansa_v2_conversation_bp.route('/v2/humansa/conversations/<conversation_id>/compress', methods=['POST'])
async def compress_conversation(conversation_id: str):
    """
    Manually trigger conversation compression
    """
    try:
        if conversation_id not in active_conversations:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Get conversation history
        history = conversation_manager.get_conversation_history(conversation_id)
        
        if len(history) < 10:
            return jsonify({"message": "Conversation too short to compress"}), 200
        
        # Compress conversation
        summary, preserved = await context_compressor.compress_conversation(
            history,
            compression_type="medical_summary",
            preserve_last_n=5
        )
        
        # Update conversation summary
        conversation_manager.update_summary(conversation_id, summary)
        
        # Extract key information
        key_info = await context_compressor.extract_key_information(history)
        
        return jsonify({
            "conversation_id": conversation_id,
            "summary": summary,
            "key_information": key_info,
            "compression_ratio": context_compressor.calculate_compression_ratio(history[:-5], summary)
        })
        
    except Exception as e:
        logger.error(f"Error compressing conversation: {e}")
        return jsonify({"error": str(e)}), 500


@humansa_v2_conversation_bp.route('/v2/humansa/conversations/cleanup', methods=['POST'])
async def cleanup_conversations():
    """
    Clean up old conversations
    """
    try:
        data = await request.get_json()
        max_age_hours = data.get('max_age_hours', 24)
        
        # Clean up conversation manager
        conversation_manager.cleanup_old_conversations(max_age_hours)
        
        # Clean up active conversations dict
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = [
            conv_id for conv_id, meta in active_conversations.items()
            if meta["last_updated"] < cutoff
        ]
        
        for conv_id in to_remove:
            del active_conversations[conv_id]
        
        return jsonify({
            "cleaned_up": len(to_remove),
            "message": f"Cleaned up {len(to_remove)} old conversations"
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
        return jsonify({"error": str(e)}), 500