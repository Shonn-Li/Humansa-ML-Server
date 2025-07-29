"""
Mem0 API endpoints for Humansa
Direct access to memory operations
"""

from quart import Blueprint, request, jsonify
from typing import Dict, Any
import logging
from .mem0_manager import Mem0Manager

logger = logging.getLogger(__name__)

# Create blueprint for Mem0 endpoints
mem0_bp = Blueprint('mem0', __name__)


@mem0_bp.route('/v2/humansa/memory/add', methods=['POST'])
async def add_memory():
    """Add a conversation to user's memory."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id')
        metadata = data.get('metadata', {})
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        if not messages:
            return jsonify({"error": "messages are required"}), 400
            
        # Get Mem0 manager
        mem0_manager = Mem0Manager.get_instance()
        if not mem0_manager.initialized:
            return jsonify({
                "error": "Mem0 is not initialized",
                "status": "unavailable"
            }), 503
            
        # Add conversation
        success = await mem0_manager.add_conversation(
            user_id=user_id,
            messages=messages,
            conversation_id=conversation_id,
            metadata=metadata
        )
        
        if success:
            return jsonify({
                "status": "success",
                "user_id": user_id,
                "message": "Conversation added to memory"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to add conversation to memory"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in add_memory endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@mem0_bp.route('/v2/humansa/memory/search', methods=['POST'])
async def search_memories():
    """Search user memories."""
    try:
        data = await request.get_json()
        user_id = data.get('user_id')
        query = data.get('query', '')
        limit = data.get('limit', 10)
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
            
        # Get Mem0 manager
        mem0_manager = Mem0Manager.get_instance()
        if not mem0_manager.initialized:
            return jsonify({
                "error": "Mem0 is not initialized",
                "memories": []
            }), 503
            
        # Search memories
        memories = await mem0_manager.search_memories(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        return jsonify({
            "user_id": user_id,
            "query": query,
            "count": len(memories),
            "memories": memories
        })
        
    except Exception as e:
        logger.error(f"Error in search_memories endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@mem0_bp.route('/v2/humansa/memory/context/<user_id>', methods=['GET'])
async def get_user_context(user_id: str):
    """Get user context from memories."""
    try:
        # Get Mem0 manager
        mem0_manager = Mem0Manager.get_instance()
        if not mem0_manager.initialized:
            return jsonify({
                "error": "Mem0 is not initialized",
                "context": {"user_id": user_id}
            }), 503
            
        # Get context
        context = await mem0_manager.get_user_context(user_id)
        
        return jsonify({
            "user_id": user_id,
            "context": context
        })
        
    except Exception as e:
        logger.error(f"Error in get_user_context endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@mem0_bp.route('/v2/humansa/memory/status', methods=['GET'])
async def memory_status():
    """Get Mem0 status and configuration."""
    try:
        mem0_manager = Mem0Manager.get_instance()
        
        status = {
            "initialized": mem0_manager.initialized,
            "environment": mem0_manager.config.get("vector_store", {}).get("config", {}).get("collection_name", "unknown"),
            "provider": "mem0",
            "features": [
                "semantic_search",
                "memory_extraction",
                "context_awareness",
                "multi_service_support"
            ]
        }
        
        if mem0_manager.initialized:
            # Test connectivity
            try:
                test_user = "mem0_status_test"
                test_memories = mem0_manager.memory.get_all(user_id=test_user)
                status["connectivity"] = "healthy"
                status["test_result"] = "success"
            except Exception as test_error:
                status["connectivity"] = "unhealthy"
                status["test_error"] = str(test_error)
        else:
            status["connectivity"] = "not_initialized"
            
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error in memory_status endpoint: {e}")
        return jsonify({
            "error": str(e),
            "initialized": False,
            "connectivity": "error"
        }), 500


@mem0_bp.route('/v2/humansa/memory/clear/<user_id>', methods=['DELETE'])
async def clear_user_memories(user_id: str):
    """Clear all memories for a user (use with caution)."""
    try:
        # Get Mem0 manager
        mem0_manager = Mem0Manager.get_instance()
        if not mem0_manager.initialized:
            return jsonify({
                "error": "Mem0 is not initialized"
            }), 503
            
        # Get memory user ID
        memory_user_id = mem0_manager.get_memory_user_id(user_id)
        
        # Get all memories
        import asyncio
        loop = asyncio.get_event_loop()
        memories = await loop.run_in_executor(
            None,
            lambda: mem0_manager.memory.get_all(user_id=memory_user_id)
        )
        
        # Delete each memory
        deleted_count = 0
        for memory in memories:
            try:
                await loop.run_in_executor(
                    None,
                    mem0_manager.memory.delete,
                    memory.get('id')
                )
                deleted_count += 1
            except Exception as del_error:
                logger.warning(f"Failed to delete memory {memory.get('id')}: {del_error}")
                
        return jsonify({
            "user_id": user_id,
            "memories_deleted": deleted_count,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Error in clear_user_memories endpoint: {e}")
        return jsonify({"error": str(e)}), 500