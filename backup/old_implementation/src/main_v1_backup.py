"""
YouWoAI ML Server - Main Application Entry Point (Fixed Version)

This version PROPERLY preserves ALL original chat endpoints exactly as they are
and ONLY modularizes the embedding and search operations that we've been working on.

FILE ORGANIZATION:
- main.py (this file) - Current modular version with background jobs
- main_original_backup.py - Original working version (safe backup)

PRESERVED EXACTLY:
- ALL /v1/* chat endpoints (no changes whatsoever)
- /analyze_link endpoint (original implementation)
- /note_text/* endpoint (original implementation)  
- /search_cache_stats endpoint (original implementation)

MODULARIZED (NEW):
- /admin/embed-* endpoints (background jobs)
- /search/* endpoints (tsvector search)
- /jobs/* endpoints (job management)
- /health, /ping endpoints (health checks)

To rollback: mv main_original_backup.py main.py
"""

import os
import json
import base64
import logging
from quart import Quart, jsonify, request, Response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Print environment variables at startup
logger.info("=== Environment Variables Debug ===")
logger.info(f"DB_HOST: {os.getenv('DB_HOST', 'NOT SET')}")
logger.info(f"DB_PORT: {os.getenv('DB_PORT', 'NOT SET')}")
logger.info(f"DB_USERNAME: {os.getenv('DB_USERNAME', 'NOT SET')}")
logger.info(
    f"DB_ACTIVE_DATABASE: {os.getenv('DB_ACTIVE_DATABASE', 'NOT SET')}")
logger.info(
    f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
logger.info(
    f"EMBEDDING_DEV: {'SET' if os.getenv('EMBEDDING_DEV') else 'NOT SET'}")
logger.info("================================")


def create_app():
    """Application factory pattern"""
    app = Quart(__name__)

    # Register NEW modularized blueprints (ONLY for embedding/search/jobs)
    register_modular_routes(app)

    # Register ALL original endpoints EXACTLY as they were
    register_original_endpoints(app)

    return app


def register_modular_routes(app):
    """Register ONLY the new modularized routes"""
    try:
        from src.routes.health import health_bp
        from src.routes.jobs import jobs_bp
        from src.routes.embeddings import embeddings_bp
        from src.routes.search import search_bp
        from src.endpoints.url_embeddings import url_embeddings_bp

        app.register_blueprint(health_bp)
        app.register_blueprint(jobs_bp)
        app.register_blueprint(embeddings_bp)
        app.register_blueprint(search_bp)
        app.register_blueprint(url_embeddings_bp)

        logger.info("✅ Modular routes registered successfully")
    except Exception as e:
        logger.error(f"❌ Error registering modular routes: {e}")
        # Continue without modular routes if they fail


def register_original_endpoints(app):
    """Register ALL original endpoints EXACTLY as they were in main.py"""

    from src.utility.postgres import get_note_text

    # Import link analyzer - EXACTLY as in original
    try:
        from src.ai_chat_bot.link_analyzer import analyze_link
        LINK_ANALYZER_AVAILABLE = True
    except ImportError:
        logger.warning("Link analyzer not available")
        LINK_ANALYZER_AVAILABLE = False

    # Import enhanced chat bot - EXACTLY as in original
    try:
        from src.ai_chat_bot.enhanced_chat_bot import (
            EnhancedChatBot,
            ChatCompletionRequest,
            ChatMessage,
            MessageRole
        )
        enhanced_chat_bot = EnhancedChatBot()
        ENHANCED_CHAT_BOT_AVAILABLE = True
    except ImportError as e:
        ENHANCED_CHAT_BOT_AVAILABLE = False
        ENHANCED_CHAT_BOT_ERROR = str(e)

    # =====================================================================
    # ALL ORIGINAL ENDPOINTS - COPIED EXACTLY FROM MAIN.PY
    # =====================================================================

    @app.route("/analyze_link", methods=["POST"])
    async def analyze_link_endpoint():
        """Link analysis endpoint - ENHANCED WITH OPTIONS SUPPORT"""
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

    @app.route("/note_text/<int:note_id>", methods=["GET"])
    async def get_note_text_endpoint(note_id: int):
        """Get note text by ID - ORIGINAL IMPLEMENTATION"""
        try:
            note_text = get_note_text(note_id)

            if not note_text:
                return jsonify({
                    "error": f"Note {note_id} not found or has no content"
                }), 404

            return jsonify({
                "note_id": note_id,
                "text": note_text
            })

        except Exception as e:
            logger.error(f"Error getting note text: {e}")
            return jsonify({
                "error": f"Failed to get note text: {str(e)}"
            }), 500

    @app.route("/note_title/<int:note_id>", methods=["GET"])
    async def get_note_title_endpoint(note_id: int):
        """Get note title by ID - lightweight endpoint"""
        try:
            from src.utility.postgres import get_note_title
            title = get_note_title(note_id)

            return jsonify({
                "note_id": note_id,
                "title": title
            })

        except Exception as e:
            logger.error(f"Error getting note title: {e}")
            return jsonify({
                "error": f"Failed to get note title: {str(e)}"
            }), 500

    @app.route("/note_titles", methods=["POST"])
    async def get_note_titles_batch_endpoint():
        """Get titles for multiple notes - batch endpoint"""
        try:
            data = await request.get_json()
            note_ids = data.get("note_ids", [])

            if not note_ids:
                return jsonify({"error": "note_ids array is required"}), 400

            from src.utility.postgres import get_note_titles_batch
            titles = get_note_titles_batch(note_ids)

            return jsonify({
                "titles": titles,
                "count": len(titles)
            })

        except Exception as e:
            logger.error(f"Error getting note titles batch: {e}")
            return jsonify({
                "error": f"Failed to get note titles: {str(e)}"
            }), 500

    # =====================================================================
    # CHAT ENDPOINTS - COPIED EXACTLY FROM ORIGINAL MAIN.PY
    # =====================================================================

    @app.route("/v1/chat/completions", methods=["POST"])
    async def chat_completions():
        """OpenAI-compatible chat completions endpoint with enhanced features - ORIGINAL"""
        if not ENHANCED_CHAT_BOT_AVAILABLE:
            return jsonify({
                "error": "Enhanced chat bot not available",
                "details": ENHANCED_CHAT_BOT_ERROR if 'ENHANCED_CHAT_BOT_ERROR' in globals() else "Import failed"
            }), 500

        try:
            data = await request.get_json()
            logger.info("request data, with the message truncated: " +
                        json.dumps(data, indent=2, ensure_ascii=False)[:1000]
                        )

            # Validate user_id - it's always required for verification purposes
            if not data.get("user_id"):
                return jsonify({
                    "error": {
                        "message": "user_id is always required for verification purposes",
                        "type": "invalid_request_error",
                        "code": "missing_required_parameter"
                    }
                }, 400)

            # Get enable_rag flag
            enable_rag = data.get("enable_rag", True)

            # Convert request to our format
            messages = []
            for msg in data.get("messages", []):
                messages.append(ChatMessage(
                    role=msg["role"],
                    content=msg["content"],
                    name=msg.get("name"),
                    function_call=msg.get("function_call"),
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id")
                ))

            chat_request = ChatCompletionRequest(
                messages=messages,
                model=data.get("model"),
                provider=data.get("provider"),
                temperature=data.get("temperature"),
                max_tokens=data.get("max_tokens"),
                top_p=data.get("top_p"),
                frequency_penalty=data.get("frequency_penalty"),
                presence_penalty=data.get("presence_penalty"),
                stop=data.get("stop"),
                stream=data.get("stream", False),
                user_id=data.get("user_id"),
                folder_ids=data.get("folder_ids"),
                note_ids=data.get("note_ids"),
                enable_rag=enable_rag,
                # NEW: Citations enable deep search
                enable_citations=data.get("enable_citations", False),
                enable_web_search=data.get("enable_web_search", False),
                enable_image_analysis=data.get("enable_image_analysis", False),
                search_query=data.get("search_query"),
                attachments=data.get("attachments"),
                generate_title=data.get("enable_title_generation", False)
            )

            # Generate response
            if chat_request.stream:
                async def generate():
                    # Restore await here: chat_completion returns a coroutine that resolves to an async generator
                    async for chunk in await enhanced_chat_bot.chat_completion(chat_request):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return Response(generate(), mimetype="text/event-stream")
            else:
                response = await enhanced_chat_bot.chat_completion(chat_request)
                # Convert the response to a proper dict, ensuring citations are serialized
                response_dict = response.__dict__.copy()
                if response_dict.get('citations'):
                    # Citations are already dictionaries from _extract_citations_from_response
                    response_dict['citations'] = response_dict['citations']
                return jsonify(response_dict)

        except ValueError as e:
            return jsonify({
                "error": {
                    "message": str(e),
                    "type": "invalid_request_error",
                    "code": "invalid_request"
                }
            }), 400
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            return jsonify({
                "error": {
                    "message": str(e),
                    "type": "internal_error",
                    "code": "internal_error"
                }
            }), 500

    @app.route("/v1/models", methods=["GET"])
    async def list_models():
        """List available models and providers - ORIGINAL IMPLEMENTATION"""
        if not ENHANCED_CHAT_BOT_AVAILABLE:
            return jsonify({
                "error": "Enhanced chat bot not available"
            }), 500

        try:
            providers = enhanced_chat_bot.list_providers()
            models = []

            for provider, provider_models in providers.items():
                for model in provider_models:
                    models.append({
                        "id": model,
                        "object": "model",
                        "provider": provider,
                        "created": 1677610602,
                        "owned_by": provider
                    })

            return jsonify({
                "object": "list",
                "data": models
            })

        except Exception as e:
            logger.error(f"List models error: {e}")
            return jsonify({
                "error": {
                    "message": str(e),
                    "type": "internal_error"
                }
            }), 500

    @app.route("/v1/chat", methods=["POST"])
    async def enhanced_chat():
        """Enhanced chat endpoint with context and multi-provider support - ORIGINAL"""
        if not ENHANCED_CHAT_BOT_AVAILABLE:
            return jsonify({
                "error": "Enhanced chat bot not available",
                "details": ENHANCED_CHAT_BOT_ERROR if 'ENHANCED_CHAT_BOT_ERROR' in globals() else "Import failed"
            }), 500

        try:
            data = await request.get_json()

            # Extract parameters
            question = data.get("question", "")
            if not question:
                return jsonify({"error": "No question provided"}), 400

            # Validate user_id if enable_rag is not explicitly False
            enable_rag = data.get("enable_rag", True)
            if enable_rag and not data.get("user_id"):
                return jsonify({"error": "user_id is required when RAG is enabled"}), 400

            # Create messages format
            messages = [ChatMessage(
                role=MessageRole.USER.value, content=question)]

            # Add system message if provided
            if data.get("system_message"):
                messages.insert(0, ChatMessage(
                    role=MessageRole.SYSTEM.value, content=data["system_message"]))

            chat_request = ChatCompletionRequest(
                messages=messages,
                model=data.get("model"),
                provider=data.get("provider"),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens"),
                user_id=data.get("user_id"),
                folder_ids=data.get("folder_ids"),
                note_ids=data.get("note_ids"),
                enable_rag=enable_rag,
                # NEW: Enable citations for deep search
                enable_citations=data.get("enable_citations", False),
                enable_web_search=data.get("enable_web_search", False),
                search_query=data.get("search_query"),
                attachments=data.get("attachments"),
                stream=data.get("stream", False)
            )

            if chat_request.stream:
                async def generate():
                    # Restore await here as well
                    async for chunk in await enhanced_chat_bot.chat_completion(chat_request):
                        yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return Response(generate(), mimetype="text/event-stream")
            else:
                response = await enhanced_chat_bot.chat_completion(chat_request)

                # Format response for backward compatibility
                citations_serialized = response.citations if response.citations else None
                return jsonify({
                    "answer": response.choices[0]["message"]["content"],
                    "provider": response.provider,
                    "model": response.model,
                    "used_notes": response.used_notes,
                    "search_results": response.search_results,
                    "citations": citations_serialized,
                    "usage": response.usage.__dict__ if response.usage else None
                })

        except ValueError as e:
            return jsonify({
                "error": str(e),
                "type": "invalid_request_error"
            }), 400
        except Exception as e:
            logger.error(f"Enhanced chat error: {e}")
            return jsonify({
                "error": str(e),
                "type": "internal_error"
            }), 500

    @app.route("/v1/analyze_and_chat", methods=["POST"])
    async def analyze_and_chat():
        """Analyze a link and chat about its content - ORIGINAL IMPLEMENTATION"""
        if not ENHANCED_CHAT_BOT_AVAILABLE or not LINK_ANALYZER_AVAILABLE:
            return jsonify({
                "error": "Required components not available"
            }), 500

        try:
            data = await request.get_json()
            url = data.get("url", "")
            question = data.get("question", "")

            if not url or not question:
                return jsonify({"error": "Both URL and question are required"}), 400

            # Analyze the link first
            link_result = analyze_link(url,
                                       platform=data.get("platform"),
                                       options=data.get("link_options", {}))

            if not link_result.get("success"):
                return jsonify({
                    "error": "Link analysis failed",
                    "details": link_result.get("error")
                }), 400

            # Create attachment from link content
            attachments = [{
                "type": "text/plain",
                "content": base64.b64encode(link_result["data"]["content"].encode()).decode(),
                "filename": f"content_{link_result['data']['title']}.txt",
                "metadata": link_result["data"]["metadata"]
            }]

            # Create chat request
            messages = [ChatMessage(
                role=MessageRole.USER.value, content=question)]

            chat_request = ChatCompletionRequest(
                messages=messages,
                model=data.get("model"),
                provider=data.get("provider"),
                temperature=data.get("temperature", 0.7),
                attachments=attachments,
                enable_web_search=data.get("enable_web_search", False),
                stream=data.get("stream", False)
            )

            response = await enhanced_chat_bot.chat_completion(chat_request)

            return jsonify({
                "answer": response.choices[0]["message"]["content"],
                "link_analysis": link_result,
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage.__dict__ if response.usage else None
            })

        except Exception as e:
            logger.error(f"Analyze and chat error: {e}")
            return jsonify({
                "error": str(e),
                "type": "internal_error"
            }), 500

    @app.route("/search_cache_stats", methods=["GET"])
    async def get_search_cache_stats():
        """Get web search cache statistics - ORIGINAL IMPLEMENTATION"""
        try:
            from src.utility.postgres import get_search_cache_stats, cleanup_expired_search_cache

            # Clean up expired entries first
            deleted = cleanup_expired_search_cache()

            # Get current stats
            stats = get_search_cache_stats()
            stats['deleted_expired'] = deleted

            return jsonify(stats)

        except Exception as e:
            logger.error(f"Error getting search cache stats: {e}")
            return jsonify({
                "error": f"Failed to get search cache stats: {str(e)}"
            }), 500

    @app.route("/notes/create-embeddings", methods=["POST"])
    async def create_note_embeddings():
        """Create embeddings for specific notes - ORIGINAL IMPLEMENTATION"""
        try:
            data = await request.get_json()
            note_ids = data.get("note_ids", [])

            if not note_ids:
                return jsonify({"error": "note_ids array is required"}), 400

            results = []
            for note_id in note_ids:
                try:
                    from src.utility.note_utils import create_and_save_embeddings_separate
                    embeddings = create_and_save_embeddings_separate(note_id)

                    results.append({
                        "note_id": note_id,
                        "status": "success",
                        "embedding_sections": len(embeddings)
                    })

                except Exception as e:
                    results.append({
                        "note_id": note_id,
                        "status": "error",
                        "message": str(e)
                    })

            return jsonify({
                "message": f"Processed {len(note_ids)} notes",
                "results": results
            })

        except Exception as e:
            logger.error(f"Error in create_note_embeddings: {e}")
            return jsonify({
                "error": f"Failed to create embeddings: {str(e)}"
            }), 500


# Create app instance
app = create_app()


if __name__ == "__main__":
    logger.info("Starting YouWoAI ML Server...")
    logger.info("Server will be available at: http://0.0.0.0:5001")
    logger.info("")
    logger.info("📋 Endpoint Summary:")
    logger.info("✅ PRESERVED (Original implementation):")
    logger.info("   - ALL /v1/* chat endpoints")
    logger.info("   - /analyze_link endpoint (enhanced with options)")
    logger.info("   - /note_text/* endpoint")
    logger.info("   - /search_cache_stats endpoint")
    logger.info("   - /notes/create-embeddings endpoint")
    logger.info("")
    logger.info("🆕 NEW (Modularized with background jobs):")
    logger.info("   - /health, /ping - Health checks")
    logger.info("   - /jobs/* - Job management")
    logger.info("   - /admin/embed-* - Background embedding operations")
    logger.info("   - /search/* - tsvector search operations")
    logger.info("")
    app.run(host="0.0.0.0", port=5001, debug=True)
