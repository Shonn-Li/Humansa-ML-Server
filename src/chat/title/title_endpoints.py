"""
Conversation Title Endpoints

This module provides clean endpoint handlers that delegate all business logic 
to the conversation_title_service. The main.py file only needs to import and 
register these endpoints.
"""

import logging
from quart import request, jsonify
from chat.title.conversation_title_service import conversation_title_service

logger = logging.getLogger(__name__)


async def generate_conversation_title_endpoint():
    """
    Generate title for a single conversation

    Request format:
    {
        "id": 123,
        "messages": [...],  // Optional, can be empty
        "user_id": 456,     // Optional
        "provider": "openai",  // Optional, defaults to openai
        "model": "gpt-4o-mini"  // Optional, defaults to gpt-4o-mini
    }
    """
    try:
        request_data = await request.get_json()
        logger.info(f"=== TITLE GENERATION REQUEST ===")
        logger.info(
            f"Conversation ID: {request_data.get('id') if request_data else 'None'}")
        logger.info(
            f"Message count: {len(request_data.get('messages', [])) if request_data else 0}")
        logger.info("==============================")

        result = await conversation_title_service.generate_single_title(request_data)

        logger.info(f"✅ Title generated: {result.get('generated_title')}")

        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"❌ Error in generate_conversation_title endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


async def generate_conversation_titles_batch_endpoint():
    """
    Generate titles for multiple conversations in batch

    Request format:
    {
        "conversations": [
            {
                "id": 123,
                "messages": [...],
                "user_id": 456
            },
            {
                "id": 124,
                "messages": [],
                "user_id": 456
            }
        ],
        "provider": "openai",     // Optional, applied to all
        "model": "gpt-4o-mini"    // Optional, applied to all
    }
    """
    try:
        request_data = await request.get_json()
        logger.info(f"=== BATCH TITLE GENERATION REQUEST ===")
        conversations = request_data.get(
            "conversations", []) if request_data else []
        logger.info(f"Batch size: {len(conversations)}")
        logger.info("====================================")

        result = await conversation_title_service.generate_batch_titles(request_data)

        logger.info(
            f"✅ Batch complete: {result.get('successful_count')}/{result.get('total_processed')} successful")

        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(
            f"❌ Error in generate_conversation_titles_batch endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


async def migrate_conversation_titles_endpoint():
    """
    Automatically migrate titles for all conversations without titles

    This endpoint:
    1. Finds all conversations without titles from the database
    2. Generates titles using AI for each conversation
    3. Updates the database with the generated titles

    Request format:
    {
        "batch_size": 50,        // Optional, max conversations per batch (default: 50, max: 100)
        "dry_run": false,        // Optional, if true, doesn't update database (default: false)
        "provider": "openai",    // Optional, LLM provider (default: openai)
        "model": "gpt-4o-mini",  // Optional, model to use (default: gpt-4o-mini)
        "max_conversations": 1000 // Optional, max total conversations to process (default: 1000)
    }
    """
    try:
        request_data = await request.get_json() or {}

        logger.info(f"=== TITLE MIGRATION REQUEST ===")
        logger.info(f"Batch size: {request_data.get('batch_size', 50)}")
        logger.info(f"Dry run: {request_data.get('dry_run', False)}")
        logger.info(f"Provider: {request_data.get('provider', 'openai')}")
        logger.info(
            f"Max conversations: {request_data.get('max_conversations', 1000)}")
        logger.info("==============================")

        result = await conversation_title_service.migrate_all_titles(request_data)

        logger.info(
            f"🎉 Migration complete: {result.get('successful_count', 0)}/{result.get('total_processed', 0)} successful")

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Error in migrate_conversation_titles endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "migration_complete": False
        }), 500


async def title_health_check_endpoint():
    """Simple health check endpoint for title generation service"""
    try:
        result = conversation_title_service.get_health_status()
        status_code = 200 if result.get("status") == "healthy" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "service": "conversation_title_service",
            "error": str(e),
            "timestamp": int(__import__('time').time())
        }), 500
