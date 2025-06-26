"""
URL Embedding Endpoints for Modular Chat System

This module provides URL embedding endpoints using internal chat module dependencies.
Compatible with the original v1 API but uses the new modular architecture internally.

Endpoints:
- POST /v1/embeddings/url - Create embeddings for a URL
- POST /v1/embeddings/url/check - Check if URL has embeddings  
- POST /v1/embeddings/url/search - Search within URL embeddings
- GET  /v1/embeddings/url/status - Get embedding status
"""

import logging
import time
from typing import Dict, Any, List, Optional

# Quart imports for async endpoints
from quart import Blueprint, request, jsonify
from quart_cors import cors

# Internal modular chat imports
from chat.postgres.url_embedding_operations import url_embedding_ops
from chat.attachment.file_attachment_manager import file_attachment_manager

logger = logging.getLogger(__name__)

# Create blueprint
url_embeddings_bp = Blueprint('url_embeddings_modular', __name__)
url_embeddings_bp = cors(url_embeddings_bp, allow_origin="*")


@url_embeddings_bp.route('/v1/embeddings/url', methods=['POST'])
async def create_url_embedding_endpoint():
    """
    Create embeddings for a URL (document/image) - Modular version

    Compatible with original v1 API but uses internal modular operations.

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

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return jsonify({
                "success": False,
                "error": "Invalid URL format - must start with http:// or https://"
            }), 400

        logger.info(
            f"🌐 Creating URL embedding: {url[:50]}... (user: {user_id})")

        start_time = time.time()

        # Check if embeddings already exist (using user_id if provided, otherwise fallback)
        if user_id:
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
        else:
            # Fallback for non-user specific embeddings (use user_id = 0)
            success = await url_embedding_ops.create_user_url_embeddings(url, 0)

        processing_time = time.time() - start_time

        if success:
            # Get count of created embeddings
            embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id or 0)
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


@url_embeddings_bp.route('/v1/embeddings/url/check', methods=['POST'])
async def check_url_embedding_endpoint():
    """
    Check if embeddings exist for a URL - Modular version

    Compatible with original v1 API but uses internal modular operations.

    Request body:
    {
        "url": "https://example.com/document.pdf",
        "user_id": 123  // optional
    }

    Response:
    {
        "success": true,
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
        user_id = data.get('user_id', 0)  # Default to 0 for compatibility

        logger.info(
            f"🔍 Checking URL embeddings: {url[:50]}... (user: {user_id})")

        # Check if embeddings exist
        exists = url_embedding_ops.check_user_url_embeddings_exist(
            url, user_id)
        embedding_count = 0

        if exists:
            embeddings = url_embedding_ops.get_user_url_embeddings(
                url, user_id)
            embedding_count = len(embeddings) if embeddings else 0

        return jsonify({
            "success": True,
            "url": url,
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


@url_embeddings_bp.route('/v1/embeddings/url/search', methods=['POST'])
async def search_url_embeddings_endpoint():
    """
    Search within URL embeddings - Modular version using file attachment manager

    New endpoint that leverages the modular file attachment system.

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
        user_id = data.get('user_id', 0)  # Default to 0 for compatibility
        top_k = data.get('top_k', 8)

        if not query:
            return jsonify({
                "success": False,
                "error": "query is required"
            }), 400

        if not attachments:
            return jsonify({
                "success": False,
                "error": "attachments list is required"
            }), 400

        logger.info(
            f"🔍 Searching {len(attachments)} URL embeddings for user {user_id}")

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


@url_embeddings_bp.route('/v1/embeddings/url/status', methods=['GET'])
async def get_url_embedding_status():
    """
    Get URL embedding system status - Modular version

    Response:
    {
        "status": "operational",
        "version": "modular",
        "file_attachment_manager": {...},
        "supported_formats": ["pdf", "image"]
    }
    """
    try:
        return jsonify({
            "status": "operational",
            "version": "modular",
            "architecture": "internal_dependencies",
            "file_attachment_manager": file_attachment_manager.get_status(),
            "supported_formats": ["pdf", "jpg", "jpeg", "png", "gif", "webp"],
            "endpoints": {
                "create": "/v1/embeddings/url",
                "check": "/v1/embeddings/url/check",
                "search": "/v1/embeddings/url/search",
                "status": "/v1/embeddings/url/status"
            }
        })

    except Exception as e:
        logger.error(f"❌ Error in URL embedding status endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
