"""
URL Embedding Endpoint for creating embeddings from file attachments
"""

from quart import Blueprint, request, jsonify
from quart_cors import cors
import logging
from typing import Dict, Any
from src.utility.conversation_embeddings import create_user_url_embeddings
from src.utility.postgres import check_user_url_embeddings_exist, get_user_url_embeddings, check_url_embeddings_exist, get_url_embeddings, update_embeddings_to_conversation

logger = logging.getLogger(__name__)

# Create blueprint
url_embeddings_bp = Blueprint('url_embeddings', __name__)
url_embeddings_bp = cors(url_embeddings_bp, allow_origin="*")


@url_embeddings_bp.route('/v1/embeddings/url', methods=['POST'])
async def create_url_embedding_endpoint():
    """
    Create embeddings for a URL (document/image)

    Request body:
    {
        "url": "https://example.com/document.pdf",
        "force_recreate": false,  // optional, default false
        "user_id": 123,          // optional, for usage tracking
        "type": "attachment"     // optional, for categorization
    }

    Response:
    {
        "success": true,
        "message": "Embeddings created successfully",
        "url": "https://example.com/document.pdf", 
        "embedding_count": 5,
        "already_existed": false
    }
    """
    try:
        data = await request.get_json()

        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "URL is required"
            }), 400

        url = data['url']
        force_recreate = data.get('force_recreate', False)
        user_id = data.get('user_id')
        attachment_type = data.get('type', 'attachment')

        # user_id is required for the new strategy
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400

        # Log usage tracking information
        logger.info(
            f"Creating URL embedding for user {user_id}, type: {attachment_type}, URL: {url[:50]}...")

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return jsonify({
                "success": False,
                "error": "Invalid URL format"
            }), 400

        # Check if embeddings already exist for this user and URL
        already_existed = False
        if not force_recreate and check_user_url_embeddings_exist(url, user_id):
            already_existed = True
            existing_embeddings = get_user_url_embeddings(url, user_id)
            embedding_count = len(
                existing_embeddings) if existing_embeddings else 0

            return jsonify({
                "success": True,
                "message": "Embeddings already exist for this URL and user",
                "url": url,
                "embedding_count": embedding_count,
                "already_existed": True
            })

        # Create embeddings with user ownership
        success = await create_user_url_embeddings(url, user_id)

        if success:
            # Get count of created embeddings
            embeddings = get_user_url_embeddings(url, user_id)
            embedding_count = len(embeddings) if embeddings else 0

            return jsonify({
                "success": True,
                "message": "Embeddings created successfully",
                "url": url,
                "embedding_count": embedding_count,
                "already_existed": already_existed
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create embeddings for URL"
            }), 500

    except Exception as e:
        logger.error(f"Error in URL embedding endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_bp.route('/v1/embeddings/url/check', methods=['POST'])
async def check_url_embedding_endpoint():
    """
    Check if embeddings exist for a URL

    Request body:
    {
        "url": "https://example.com/document.pdf"
    }

    Response:
    {
        "url": "https://example.com/document.pdf",
        "exists": true,
        "embedding_count": 5
    }
    """
    try:
        data = await request.get_json()

        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "URL is required"
            }), 400

        url = data['url']

        # Check if embeddings exist
        exists = check_url_embeddings_exist(url)
        embedding_count = 0

        if exists:
            embeddings = get_url_embeddings(url)
            embedding_count = len(embeddings) if embeddings else 0

        return jsonify({
            "url": url,
            "exists": exists,
            "embedding_count": embedding_count
        })

    except Exception as e:
        logger.error(f"Error in URL embedding check endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_bp.route('/v1/embeddings/conversation', methods=['POST'])
async def create_conversation_embedding_endpoint():
    """
    Create embeddings for a specific conversation (individual use)

    Request body:
    {
        "conversation_id": 123,
        "messages": [
            {"role": "user", "content": "Hello", "id": 1},
            {"role": "assistant", "content": "Hi there!", "id": 2}
        ],
        "incremental": false  // true for adding to existing conversation
    }

    Response:
    {
        "success": true,
        "message": "Conversation embeddings created successfully",
        "conversation_id": 123,
        "embedding_count": 1
    }
    """
    try:
        data = await request.get_json()

        if not data or 'conversation_id' not in data or 'messages' not in data:
            return jsonify({
                "success": False,
                "error": "conversation_id and messages are required"
            }), 400

        conversation_id = data['conversation_id']
        messages = data['messages']
        incremental = data.get('incremental', False)

        # Validate conversation_id
        if not isinstance(conversation_id, int) or conversation_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid conversation_id"
            }), 400

        # Validate messages
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({
                "success": False,
                "error": "Messages must be a non-empty list"
            }), 400

        # Create embeddings
        if incremental:
            from src.utility.conversation_embeddings import create_incremental_message_embeddings
            success = await create_incremental_message_embeddings(conversation_id, messages)
        else:
            from src.utility.conversation_embeddings import create_conversation_embeddings
            success = await create_conversation_embeddings(conversation_id, messages)

        if success:
            # Get count of embeddings
            from src.utility.postgres import get_embeddings_v2
            embeddings = get_embeddings_v2(conversation_id, 'conversation')
            embedding_count = len(embeddings) if embeddings else 0

            return jsonify({
                "success": True,
                "message": "Conversation embeddings created successfully",
                "conversation_id": conversation_id,
                "embedding_count": embedding_count,
                "incremental": incremental
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create conversation embeddings"
            }), 500

    except Exception as e:
        logger.error(f"Error in conversation embedding endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_bp.route('/v1/embeddings/update-to-conversation', methods=['POST'])
async def update_embeddings_to_conversation_endpoint():
    """
    Update user embeddings to conversation ownership

    Request body:
    {
        "user_id": 123,
        "conversation_type": "user",
        "conversation_type_id": 456,
        "attachment_urls": ["https://example.com/file1.pdf", "https://example.com/file2.jpg"]
    }

    Response:
    {
        "success": true,
        "message": "Embeddings updated to conversation ownership",
        "updated_count": 2
    }
    """
    try:
        data = await request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        # Validate required fields
        required_fields = ['user_id', 'conversation_type',
                           'conversation_type_id', 'attachment_urls']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Field '{field}' is required"
                }), 400

        user_id = data['user_id']
        conversation_type = data['conversation_type']
        conversation_type_id = data['conversation_type_id']
        attachment_urls = data['attachment_urls']

        # Validate types
        if not isinstance(user_id, int) or user_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid user_id"
            }), 400

        if not isinstance(conversation_type_id, int) or conversation_type_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid conversation_type_id"
            }), 400

        if not isinstance(attachment_urls, list) or len(attachment_urls) == 0:
            return jsonify({
                "success": False,
                "error": "attachment_urls must be a non-empty list"
            }), 400

        # Update embeddings ownership
        updated_count = update_embeddings_to_conversation(
            user_id=user_id,
            conversation_type=conversation_type,
            conversation_type_id=conversation_type_id,
            attachment_urls=attachment_urls
        )

        logger.info(
            f"Updated {updated_count} embeddings to conversation ownership for user {user_id}")

        return jsonify({
            "success": True,
            "message": "Embeddings updated to conversation ownership",
            "updated_count": updated_count
        })

    except Exception as e:
        logger.error(
            f"Error in update embeddings to conversation endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
