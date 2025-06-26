"""
YouWoAI ML Server - Modular Implementation

This is the refactored implementation that uses:
- Modular Chat Endpoint (with citations and streaming)
- Independent link analyzer module  
- New URL embedding endpoints from chat/endpoints
- Admin embedding endpoints from chat/endpoints

V1 ENDPOINTS:
- /v1/chat/completions (modular chat with citations)
- /analyze_link (using independent link module)
- /note_text/* and /note_title/* (essential note operations)
- /v1/embeddings/url/* (URL embedding operations)  
- /admin/embedding/* (admin controls)
"""

import io
import warnings
import os
import sys
import json
import logging
import warnings
from quart import Quart, jsonify, request, Response
from quart_cors import cors

# CRITICAL: Add current directory to Python path for imports to work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce Azure logging verbosity - only show essential request info
azure_loggers = [
    'azure.core.pipeline.policies.http_logging_policy',
    'azure.ai.inference',
    'azure.core.pipeline',
    'azure.identity',
    'azure.core',
    'asyncio'  # Also reduce asyncio warnings
]
for logger_name in azure_loggers:
    azure_logger = logging.getLogger(logger_name)
    azure_logger.setLevel(logging.WARNING)

# Suppress ResourceWarnings about unclosed sessions completely
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", message=".*unclosed.*")
warnings.filterwarnings("ignore", message=".*Unclosed.*")

# Add asyncio filter to suppress connection warnings


class AsyncioCleanupFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        return not any(phrase in message.lower() for phrase in [
            'unclosed client session',
            'unclosed connector',
            'source_traceback',
            'client_session:',
            'connector:'
        ])


# Apply the filter to asyncio logger
asyncio_logger = logging.getLogger('asyncio')
asyncio_logger.addFilter(AsyncioCleanupFilter())

# Custom logger for Azure requests (optional - only if you want request URLs)
azure_request_logger = logging.getLogger('youwoai.azure.requests')
azure_request_logger.setLevel(logging.INFO)

# Log Python path for debugging
logger.info(f"🐍 Python executable: {sys.executable}")
logger.info(f"📁 Current working directory: {os.getcwd()}")
logger.info(f"📂 Script directory: {current_dir}")
logger.info(f"🛤️  Python path (first 5): {sys.path[:5]}")


def truncate_dict(data, max_length=200):
    """Truncate dictionary values for logging purposes"""
    if not isinstance(data, dict):
        return str(data)[:max_length] + "..." if len(str(data)) > max_length else str(data)

    truncated = {}
    for key, value in data.items():
        if isinstance(value, str):
            if len(value) > max_length:
                truncated[key] = value[:max_length] + \
                    f"... (truncated from {len(value)} chars)"
            else:
                truncated[key] = value
        elif isinstance(value, dict):
            truncated[key] = truncate_dict(value, max_length)
        elif isinstance(value, list):
            if len(value) > 3:
                truncated[key] = value[:3] + \
                    [f"... (and {len(value) - 3} more items)"]
            else:
                truncated[key] = value
        else:
            truncated[key] = value
    return truncated


def create_app():
    """Create and configure the Quart application."""
    app = Quart(__name__)
    app = cors(app, allow_origin="*")

    # Add global error handler
    @app.errorhandler(Exception)
    async def handle_exception(error):
        logger.error(f"🚨 UNHANDLED EXCEPTION: {error}")
        logger.error(f"Request method: {request.method}")
        logger.error(f"Request URL: {request.url}")
        try:
            request_data = await request.get_json() if request.content_type == 'application/json' else None
            logger.error(f"Request data: {request_data}")
        except:
            logger.error("Could not parse request data")

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(error),
            "status": "error",
            "type": "unhandled_exception"
        }), 500

    # Add debug route
    @app.route("/debug/info", methods=["GET"])
    async def debug_info():
        """Debug information endpoint"""
        return jsonify({
            "python_executable": sys.executable,
            "current_directory": os.getcwd(),
            "script_directory": current_dir,
            "python_path": sys.path[:10],
            "available_modules": {
                "chat_available": os.path.exists(os.path.join(current_dir, "chat")),
                "chat_endpoints_available": os.path.exists(os.path.join(current_dir, "chat", "endpoints")),
                "modular_chat_endpoint_available": os.path.exists(os.path.join(current_dir, "chat", "endpoints", "modular_chat_endpoint.py"))
            }
        })

    # Register all routes
    register_chat_endpoints(app)
    register_preserved_endpoints(app)
    register_embedding_endpoints(app)

    return app


def register_chat_endpoints(app):
    """Register new modular chat endpoints."""

    @app.route("/v1/chat/completions", methods=["POST"])
    async def v1_modular_chat_completions():
        """Modular chat endpoint with citations and streaming"""
        # Add comprehensive request logging
        request_data = None
        try:
            request_data = await request.get_json()
            logger.info(f"=== CHAT REQUEST ===")
            logger.info(f"Method: {request.method}")
            logger.info(f"URL: {request.url}")
            logger.info(f"Headers: {dict(request.headers)}")

            # Truncate request data for logging
            truncated_data = truncate_dict(request_data, max_length=200)
            logger.info(
                f"Request Body: {json.dumps(truncated_data, indent=2)}")
            logger.info(f"==================")

        except Exception as e:
            logger.error(f"Failed to parse request JSON: {e}")
            return jsonify({
                "error": "Invalid JSON in request body",
                "status": "error"
            }), 400

        try:
            # Import the new modular chat endpoint with better error handling
            logger.info("🔄 Attempting to import modular_chat_endpoint...")
            from chat.endpoints.modular_chat_endpoint import modular_chat_endpoint
            logger.info("✅ Successfully imported modular_chat_endpoint")

            if request_data.get('stream'):
                # Return streaming response
                logger.info("🌊 Starting streaming response...")

                async def generate_stream():
                    chunk_count = 0
                    try:
                        # Get the streaming response from handle_chat_request
                        stream_response = await modular_chat_endpoint.handle_chat_request(request_data)

                        # Handle different response types
                        if hasattr(stream_response, '__aiter__'):
                            # It's an async generator
                            async for chunk in stream_response:
                                chunk_count += 1
                                if chunk_count <= 3:  # Log first 3 chunks
                                    truncated_chunk = truncate_dict(
                                        chunk, max_length=200)
                                    logger.info(
                                        f"📦 Stream chunk {chunk_count}: {json.dumps(truncated_chunk)}")
                                elif chunk_count == 4:
                                    logger.info(
                                        f"📦 ... (logging first 3 chunks only, total so far: {chunk_count})")

                                yield f"data: {json.dumps(chunk)}\n\n"
                        else:
                            # It's a regular response, convert to streaming format
                            logger.info("Converting non-streaming response to streaming format")
                            if isinstance(stream_response, dict) and 'choices' in stream_response:
                                for i, choice in enumerate(stream_response['choices']):
                                    chunk = {
                                        "id": stream_response.get("id", ""),
                                        "object": "chat.completion.chunk",
                                        "choices": [{
                                            "index": i,
                                            "delta": {"content": choice.get("message", {}).get("content", "")},
                                            "finish_reason": "stop"
                                        }]
                                    }
                                    chunk_count += 1
                                    yield f"data: {json.dumps(chunk)}\n\n"

                        logger.info(
                            f"✅ Streaming complete: {chunk_count} chunks sent")
                        yield "data: [DONE]\n\n"
                    except Exception as stream_error:
                        logger.error(f"❌ Streaming error: {stream_error}")
                        import traceback
                        traceback.print_exc()
                        error_chunk = {"error": str(
                            stream_error), "status": "error"}
                        yield f"data: {json.dumps(error_chunk)}\n\n"

                return Response(generate_stream(), mimetype='text/event-stream')
            else:
                # Return standard response
                logger.info("📄 Starting non-streaming response...")
                response = await modular_chat_endpoint.handle_chat_request(request_data)

                # Validate and log response
                logger.info(f"=== CHAT RESPONSE ===")
                logger.info(f"Response type: {type(response)}")
                if isinstance(response, dict):
                    logger.info(f"Response keys: {list(response.keys())}")
                    if 'choices' in response and response['choices']:
                        first_choice = response['choices'][0] if response['choices'] else {
                        }
                        if 'message' in first_choice and 'content' in first_choice['message']:
                            content = first_choice['message']['content']
                            content_length = len(
                                str(content)) if content else 0
                            logger.info(
                                f"Content length: {content_length} characters")
                            truncated_content = content[:200] + \
                                f"... (truncated from {content_length} chars)" if content_length > 200 else content
                            logger.info(
                                f"Content preview: {truncated_content}")
                        else:
                            logger.warning(
                                "⚠️ No content found in first choice message")
                    else:
                        logger.warning("⚠️ No choices found in response")

                truncated_response = truncate_dict(response, max_length=200)
                logger.info(
                    f"Response (truncated): {json.dumps(truncated_response, indent=2)}")
                logger.info(f"====================")

                # Ensure valid response format
                if not isinstance(response, dict):
                    logger.error(f"❌ Invalid response type: {type(response)}")
                    return jsonify({
                        "error": "Invalid response format from modular endpoint",
                        "status": "error"
                    }), 500

                return jsonify(response)

        except ImportError as import_error:
            logger.error(
                f"❌ Import error for modular_chat_endpoint: {import_error}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Python path: {os.sys.path}")
            return jsonify({
                "error": f"Chat module import failed: {str(import_error)}",
                "status": "error",
                "debug_info": {
                    "cwd": os.getcwd(),
                    "python_path": os.sys.path[:3]  # First 3 entries
                }
            }), 500
        except Exception as e:
            logger.error(f"❌ Chat endpoint error: {e}")
            logger.error(f"Request data: {request_data}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"Chat processing failed: {str(e)}",
                "status": "error",
                "request_data": request_data
            }), 500

    @app.route("/v1/status", methods=["GET"])
    async def v1_system_status():
        """System status endpoint"""
        try:
            logger.info("=== STATUS REQUEST ===")
            logger.info(f"Method: {request.method}")
            logger.info(f"URL: {request.url}")
            logger.info("===================")

            logger.info(
                "🔄 Attempting to import modular_chat_endpoint for status...")
            from chat.endpoints.modular_chat_endpoint import modular_chat_endpoint
            logger.info(
                "✅ Successfully imported modular_chat_endpoint for status")

            status = modular_chat_endpoint.get_status()
            logger.info(f"✅ Status response: {json.dumps(status, indent=2)}")
            return jsonify(status)
        except ImportError as import_error:
            logger.error(f"❌ Import error for status endpoint: {import_error}")
            return jsonify({
                "error": f"Status module import failed: {str(import_error)}",
                "status": "error"
            }), 500
        except Exception as e:
            logger.error(f"❌ Status endpoint error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"Status check failed: {str(e)}",
                "status": "error"
            }), 500


def register_preserved_endpoints(app):
    """Register preserved endpoints that are still needed."""

    # Add catch-all for debugging missing endpoints
    @app.route("/notes/create-embeddings", methods=["POST", "GET"])
    async def create_embeddings_debug():
        """Debug endpoint for create-embeddings requests"""
        try:
            request_data = await request.get_json() if request.method == "POST" else None
            logger.info(f"=== MISSING ENDPOINT REQUEST ===")
            logger.info(f"Method: {request.method}")
            logger.info(f"URL: {request.url}")
            logger.info(f"Headers: {dict(request.headers)}")
            logger.info(
                f"Request Body: {json.dumps(request_data, indent=2) if request_data else 'No body'}")
            logger.info(f"==============================")

            return jsonify({
                "error": "Endpoint not implemented in new modular system",
                "status": "error",
                "suggestion": "Use /admin/embedding/* endpoints instead",
                "available_embedding_endpoints": [
                    "/admin/embedding/notes",
                    "/admin/embedding/conversations",
                    "/admin/embedding/all",
                    "/admin/embedding/status",
                    "/v1/embeddings/url"
                ]
            }), 404
        except Exception as e:
            logger.error(f"Error in debug endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    # Import link analyzer from new independent location
    try:
        from link import analyze_link
        LINK_ANALYZER_AVAILABLE = True
    except ImportError as e:
        logger.error(f"Link analyzer not available: {e}")
        LINK_ANALYZER_AVAILABLE = False

    @app.route("/analyze_link", methods=["POST"])
    async def analyze_link_endpoint():
        """Link analysis endpoint - using independent link module"""
        if not LINK_ANALYZER_AVAILABLE:
            return jsonify({"error": "Link analyzer not available"}), 503

        try:
            data = await request.get_json()
            link = data.get("link")

            # Extract options from request
            platform = data.get("platform")
            languages = data.get("languages", ["en"])
            spider_api_key = data.get("spider_api_key")

            if not link:
                return jsonify({"error": "Link is required"}), 400

            # Build options dict for analyze_link
            options = {
                "languages": languages
            }
            if spider_api_key:
                options["spider_api_key"] = spider_api_key

            result = analyze_link(link, platform=platform, options=options)
            return jsonify({
                "link": link,
                "analysis": result
            })

        except Exception as e:
            logger.error(f"Error analyzing link: {e}")
            return jsonify({"error": f"Failed to analyze link: {str(e)}"}), 500

    # Note operations (essential for system functionality)
    @app.route("/note_text/<int:note_id>", methods=["GET"])
    async def get_note_text_endpoint(note_id: int):
        """Get note text by ID"""
        try:
            from backup.old_implementation.src.utility.postgres import get_db_connection

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT content FROM notes WHERE id = %s", (note_id,))
                    result = cursor.fetchone()

                    if result is None:
                        return jsonify({"error": "Note not found"}), 404

                    return jsonify({"note_id": note_id, "content": result[0]})

        except Exception as e:
            logger.error(f"Error getting note text: {e}")
            return jsonify({"error": f"Failed to get note text: {str(e)}"}), 500

    @app.route("/note_title/<int:note_id>", methods=["GET"])
    async def get_note_title_endpoint(note_id: int):
        """Get note title by ID"""
        try:
            from backup.old_implementation.src.utility.postgres import get_db_connection

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT title FROM notes WHERE id = %s", (note_id,))
                    result = cursor.fetchone()

                    if result is None:
                        return jsonify({"error": "Note not found"}), 404

                    return jsonify({"note_id": note_id, "title": result[0]})

        except Exception as e:
            logger.error(f"Error getting note title: {e}")
            return jsonify({"error": f"Failed to get note title: {str(e)}"}), 500


def register_embedding_endpoints(app):
    """Register URL and admin embedding endpoints."""

    logger.info("🔄 Registering embedding endpoints...")

    # URL Embedding Endpoints
    try:
        logger.info("🔄 Attempting to import URL embedding endpoints...")
        from chat.endpoints.url_embeddings_endpoint import (
            create_url_embedding_endpoint,
            check_url_embedding_endpoint,
            search_url_embeddings_endpoint,
            get_url_embedding_status
        )
        logger.info("✅ Successfully imported URL embedding endpoints")

        app.add_url_rule("/v1/embeddings/url", "create_url_embeddings",
                         create_url_embedding_endpoint, methods=["POST"])
        app.add_url_rule("/v1/embeddings/url/check", "check_url_embeddings",
                         check_url_embedding_endpoint, methods=["POST"])
        app.add_url_rule("/v1/embeddings/url/search", "search_url_embeddings",
                         search_url_embeddings_endpoint, methods=["POST"])
        app.add_url_rule("/v1/embeddings/url/status", "url_embeddings_status",
                         get_url_embedding_status, methods=["GET"])

        logger.info("✅ URL embedding endpoints registered successfully")

    except ImportError as e:
        logger.error(f"❌ URL embedding endpoints import failed: {e}")
        logger.error(
            f"Available files in chat/endpoints/: {os.listdir(os.path.join(current_dir, 'chat', 'endpoints')) if os.path.exists(os.path.join(current_dir, 'chat', 'endpoints')) else 'Directory not found'}")

    # Admin Embedding Endpoints
    try:
        logger.info("🔄 Attempting to import admin embedding endpoints...")
        from chat.endpoints.admin_embedding_endpoints import (
            embed_missing_notes,
            embed_missing_conversations,
            embed_all_missing,
            embedding_status,
            stop_embeddings
        )
        logger.info("✅ Successfully imported admin embedding endpoints")

        app.add_url_rule("/admin/embedding/notes", "embed_missing_notes",
                         embed_missing_notes, methods=["POST"])
        app.add_url_rule("/admin/embedding/conversations", "embed_missing_conversations",
                         embed_missing_conversations, methods=["POST"])
        app.add_url_rule("/admin/embedding/all", "embed_all_missing",
                         embed_all_missing, methods=["POST"])
        app.add_url_rule("/admin/embedding/status", "embedding_status",
                         embedding_status, methods=["GET"])
        app.add_url_rule("/admin/embedding/stop", "stop_embeddings",
                         stop_embeddings, methods=["POST"])

        logger.info("✅ Admin embedding endpoints registered successfully")

    except ImportError as e:
        logger.error(f"❌ Admin embedding endpoints import failed: {e}")

    # V1 Conversation Embedding Endpoint (called by backend)
    @app.route("/v1/embeddings/conversation", methods=["POST"])
    async def v1_conversation_embeddings():
        """Handle conversation embedding requests from backend"""
        try:
            request_data = await request.get_json()
            logger.info(f"🔄 Conversation embedding request: {request_data}")

            conversation_id = request_data.get('conversation_id')
            if not conversation_id:
                return jsonify({"error": "conversation_id is required"}), 400

            # Import the conversation embedder
            # Create and run embedder
            from chat.embedding.conversation_embedder import ConversationEmbedder
            embedder = ConversationEmbedder()
            result = await embedder.bulk_embed_conversations([conversation_id])

            return jsonify({
                "status": "success",
                "conversation_id": conversation_id,
                "embedded": result.get("embedded", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", 0)
            })

        except Exception as e:
            logger.error(f"❌ Conversation embedding error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e), "status": "error"}), 500

    logger.info("✅ Embedding endpoints registration completed")


# Additional cleanup for stderr warnings


class FilteredStderr:
    """Custom stderr that filters out Azure unclosed session warnings"""

    def __init__(self, original_stderr):
        self.original_stderr = original_stderr

    def write(self, text):
        # Filter out specific warnings we don't want
        if text and not any(phrase in text.lower() for phrase in [
            'unclosed client session',
            'unclosed connector',
            'source_traceback: object created at',
            'client_session:',
            'connector:'
        ]):
            self.original_stderr.write(text)

    def flush(self):
        self.original_stderr.flush()

    def __getattr__(self, name):
        return getattr(self.original_stderr, name)


# Override stderr to filter warnings (only in production)
if not os.getenv('DEBUG_AZURE_WARNINGS'):
    sys.stderr = FilteredStderr(sys.stderr)

# Create app instance
app = create_app()

if __name__ == "__main__":
    logger.info("=== YouWoAI ML Server Starting ===")
    logger.info("🚀 MODULAR IMPLEMENTATION V1 - NEW ARCHITECTURE")
    logger.info("📍 This is the NEW modular main.py, NOT the old ai_chat_bot!")
    logger.info("🔥 If you see ai_chat_bot logs, the wrong version is running!")
    logger.info("Server will be available at: http://0.0.0.0:5001")
    logger.info("")
    logger.info("📋 V1 Endpoint Summary:")
    logger.info("✅ CHAT ENDPOINTS:")
    logger.info(
        "   - /v1/chat/completions - Modular chat with citations & streaming")
    logger.info("   - /v1/status - System status")
    logger.info("")
    logger.info("✅ PRESERVED ENDPOINTS:")
    logger.info("   - /analyze_link - Independent link analysis")
    logger.info("   - /note_text/<id> - Essential note operations")
    logger.info("   - /note_title/<id> - Essential note operations")
    logger.info("")
    logger.info("✅ EMBEDDING ENDPOINTS:")
    logger.info("   - /v1/embeddings/url/* - URL embedding operations")
    logger.info("   - /admin/embedding/* - Admin embedding controls")
    logger.info("")
    logger.info("🔄 Migration Status:")
    logger.info("   - ✅ Chat system: Using modular implementation")
    logger.info("   - ✅ Link analyzer: Independent module")
    logger.info("   - ✅ Embeddings: New modular architecture")
    logger.info("   - ✅ Citations: Streaming & non-streaming support")
    logger.info("")
    logger.info("🐳 Docker Check:")
    logger.info("   - If running in Docker, ensure Dockerfile uses: python src/main.py")
    logger.info("   - NOT: python -m src.ai_chat_bot.enhanced_chat_bot")
    logger.info("   - Container should be rebuilt after code changes")
    logger.info("")

    app.run(host="0.0.0.0", port=5001, debug=True)
