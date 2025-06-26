"""
URL Embedding Endpoints for Modular Chat System

This module provides endpoints for managing URL embeddings in the new modular architecture.
It's designed to work alongside the existing url_embeddings.py but with cleaner separation.

Endpoints:
- POST /v2/embeddings/url - Create embeddings for a URL
- GET  /v2/embeddings/url/check - Check if URL has embeddings  
- POST /v2/embeddings/url/search - Search within URL embeddings
- GET  /v2/embeddings/url/status - Get embedding status
"""

# Local imports - using internal operations only
from chat.postgres.url_embedding_operations import url_embedding_ops
from chat.attachment.file_attachment_manager import file_attachment_manager
import logging
from typing import Dict, Any, List, Optional

# Quart imports for async endpoints
from quart import Blueprint, request, jsonify
from quart_cors import cors

# Local imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


logger = logging.getLogger(__name__)

# Create blueprint
url_embeddings_v2_bp = Blueprint('url_embeddings_v2', __name__)
url_embeddings_v2_bp = cors(url_embeddings_v2_bp, allow_origin="*")


@url_embeddings_v2_bp.route('/v2/embeddings/url', methods=['POST'])
async def create_url_embedding_v2():
    """
    Create embeddings for a URL (modular version)

    Request:
    {
        "url": "https://example.com/document.pdf",
        "user_id": 123,
        "force_recreate": false
    }

    Response:
    {
        "success": true,
        "url": "https://example.com/document.pdf",
        "embedding_count": 5,
        "already_existed": false,
        "processing_time": 2.5
    }
    """
    try:
        data = await request.get_json()

        # Validate required fields
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        url = data.get('url')
        user_id = data.get('user_id')
        force_recreate = data.get('force_recreate', False)

        if not url:
            return jsonify({
                "success": False,
                "error": "url is required"
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return jsonify({
                "success": False,
                "error": "Invalid URL format - must start with http:// or https://"
            }), 400

        logger.info(
            f"🌐 Creating URL embedding for user {user_id}: {url[:50]}...")

        import time
        start_time = time.time()

        # Check if embeddings already exist
        already_existed = False
        if not force_recreate and url_embedding_ops.check_user_url_embeddings_exist(url, user_id):
            already_existed = True
            existing_embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id)
            embedding_count = len(
                existing_embeddings) if existing_embeddings else 0

            processing_time = time.time() - start_time

            return jsonify({
                "success": True,
                "message": "Embeddings already exist for this URL and user",
                "url": url,
                "embedding_count": embedding_count,
                "already_existed": True,
                "processing_time": round(processing_time, 2)
            })

        # Create new embeddings
        success = await url_embedding_ops.create_user_url_embeddings(url, user_id)

        processing_time = time.time() - start_time

        if success:
            # Get count of created embeddings
            embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id)
            embedding_count = len(embeddings) if embeddings else 0

            logger.info(
                f"✅ Created {embedding_count} embeddings for {url[:50]}... in {processing_time:.2f}s")

            return jsonify({
                "success": True,
                "message": "Embeddings created successfully",
                "url": url,
                "embedding_count": embedding_count,
                "already_existed": False,
                "processing_time": round(processing_time, 2)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create embeddings for URL",
                "processing_time": round(processing_time, 2)
            }), 500

    except Exception as e:
        logger.error(f"❌ Error in URL embedding endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_v2_bp.route('/v2/embeddings/url/check', methods=['GET'])
async def check_url_embedding_v2():
    """
    Check if embeddings exist for a URL

    Query params:
    - url: URL to check
    - user_id: User ID

    Response:
    {
        "url": "https://example.com/document.pdf",
        "user_id": 123,
        "exists": true,
        "embedding_count": 5,
        "last_updated": "2024-01-01T00:00:00Z"
    }
    """
    try:
        url = request.args.get('url')
        user_id = request.args.get('user_id')

        if not url:
            return jsonify({
                "success": False,
                "error": "url parameter is required"
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id parameter is required"
            }), 400

        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({
                "success": False,
                "error": "user_id must be a valid integer"
            }), 400

        logger.info(
            # Check if embeddings exist
            f"🔍 Checking URL embeddings for user {user_id}: {url[:50]}...")
        exists = url_embedding_ops.check_user_url_embeddings_exist(
            url, user_id)
        embedding_count = 0

        if exists:
            embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id)
            embedding_count = len(embeddings) if embeddings else 0

        return jsonify({
            "url": url,
            "user_id": user_id,
            "exists": exists,
            "embedding_count": embedding_count,
            "status": "found" if exists else "not_found"
        })

    except Exception as e:
        logger.error(f"❌ Error in URL embedding check endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_v2_bp.route('/v2/embeddings/url/search', methods=['POST'])
async def search_url_embeddings_v2():
    """
    Search within URL embeddings (modular version)

    Request:
    {
        "query": "What is the main topic?",
        "attachments": [
            {"url": "https://example.com/doc1.pdf"},
            {"url": "https://example.com/doc2.pdf"}
        ],
        "user_id": 123,
        "top_k": 8
    }

    Response:
    {
        "success": true,
        "query": "What is the main topic?",
        "results": [
            {
                "url": "https://example.com/doc1.pdf",
                "chunk_text": "...",
                "similarity": 0.85,
                "section_id": "section_1"
            }
        ],
        "total_chunks": 5,
        "urls_processed": 2,
        "processing_time": 0.5
    }
    """
    try:
        data = await request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        query = data.get('query')
        attachments = data.get('attachments', [])
        user_id = data.get('user_id')
        top_k = data.get('top_k', 8)

        if not query:
            return jsonify({
                "success": False,
                "error": "query is required"
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400

        if not attachments:
            return jsonify({
                "success": False,
                "error": "attachments list is required"
            }), 400

        logger.info(
            f"🔍 Searching {len(attachments)} URL embeddings for user {user_id}")

        import time
        start_time = time.time()

        # Use the file attachment manager to process attachments
        attachment_context = await file_attachment_manager.process_attachments(
            attachments=attachments,
            query=query,
            user_id=user_id,
            top_k=top_k
        )

        processing_time = time.time() - start_time

        # Format results for API response
        results = []
        for chunk in attachment_context.chunks:
            results.append({
                "url": chunk.url,
                "chunk_text": chunk.chunk_text,
                "similarity": round(chunk.similarity, 4),
                "section_id": chunk.section_id,
                "metadata": chunk.metadata
            })

        logger.info(
            f"✅ Found {len(results)} relevant chunks in {processing_time:.2f}s")

        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "total_chunks": attachment_context.total_chunks,
            "urls_processed": attachment_context.urls_processed,
            "urls_missing_embeddings": attachment_context.urls_missing_embeddings,
            "processing_time": round(processing_time, 2)
        })

    except Exception as e:
        logger.error(f"❌ Error in URL embedding search endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@url_embeddings_v2_bp.route('/v2/embeddings/url/status', methods=['GET'])
async def get_url_embedding_status():
    """
    Get URL embedding system status

    Response:
    {
        "status": "operational",
        "file_attachment_manager": {...},
        "supported_formats": ["pdf", "image"],
        "version": "v2"
    }
    """
    try:
        return jsonify({
            "status": "operational",
            "file_attachment_manager": file_attachment_manager.get_status(),
            "supported_formats": ["pdf", "jpg", "jpeg", "png", "gif", "webp"],
            "version": "v2",
            "endpoints": {
                "create": "/v2/embeddings/url",
                "check": "/v2/embeddings/url/check",
                "search": "/v2/embeddings/url/search",
                "status": "/v2/embeddings/url/status"
            }
        })

    except Exception as e:
        logger.error(f"❌ Error in URL embedding status endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
