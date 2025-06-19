# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from src.utility.postgres import get_note_text
from quart import Quart, jsonify, request, Response
import os
import json
import base64
import logging

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


app = Quart(__name__)


# Health check route for Docker/ALB
@app.route("/health", methods=["GET"])
async def health():
    """Health check endpoint for ALB and Docker"""
    return jsonify({
        "status": "healthy",
        "service": "ml-server",
        "port": 5001
    })


# Health check route
@app.route("/ping", methods=["GET"])
async def ping():
    return jsonify({"message": "Hi from YouWoAI"})


# Import link analyzer
try:
    from src.ai_chat_bot.link_analyzer import analyze_link
    LINK_ANALYZER_AVAILABLE = True
except ImportError as e:
    LINK_ANALYZER_AVAILABLE = False
    LINK_ANALYZER_ERROR = str(e)


# Link Analysis endpoint
@app.route("/analyze_link", methods=["POST"])
async def analyze_link_api():
    """API endpoint to analyze YouTube, Bilibili, or web links"""
    logger.info("\n" + "="*80)
    logger.info("NEW REQUEST: /analyze_link")
    logger.info("="*80)

    if not LINK_ANALYZER_AVAILABLE:
        logger.error("Link analyzer module not available!")
        return jsonify({
            "error": "Link analyzer not available",
            "details": LINK_ANALYZER_ERROR if 'LINK_ANALYZER_ERROR' in globals() else "Import failed"
        }), 500

    data = await request.get_json()
    url = data.get("url", "")

    logger.info(f"Requested URL: {url}")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Optional, will auto-detect if not provided
    platform = data.get("platform")
    options = data.get("options", {})  # Optional parameters

    logger.info(f"Platform: {platform or 'auto-detect'}")
    logger.info(f"Options: {options}")

    try:
        result = analyze_link(url, platform=platform, options=options)

        return jsonify(result)
    except Exception as e:
        logger.error(
            f"Unexpected error in analyze_link_api: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "analysis_failed",
            "message": str(e)
        }), 500


@app.route("/note_text/<int:note_id>", methods=["GET"])
async def get_note_text_api(note_id):
    """API to get the formatted note text for a given note ID"""
    text = get_note_text(note_id)
    return jsonify({"note_id": note_id, "note_text": text})


# Enhanced Chat Bot with GPT-level API
try:
    from src.ai_chat_bot.enhanced_chat_bot import (
        enhanced_chat_bot,
        ChatCompletionRequest,
        ChatMessage,
        MessageRole
    )
    ENHANCED_CHAT_BOT_AVAILABLE = True
except ImportError as e:
    ENHANCED_CHAT_BOT_AVAILABLE = False
    ENHANCED_CHAT_BOT_ERROR = str(e)

# OpenAI-compatible Chat Completions endpoint


@app.route("/v1/chat/completions", methods=["POST"])
async def chat_completions():
    """OpenAI-compatible chat completions endpoint with enhanced features"""
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
            }), 400

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
            enable_web_search=data.get("enable_web_search", False),
            enable_image_analysis=data.get("enable_image_analysis", False),
            search_query=data.get("search_query"),
            attachments=data.get("attachments")
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


# List available models and providers
@app.route("/v1/models", methods=["GET"])
async def list_models():
    """List available models and providers"""
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


# Enhanced chat bot endpoint (backward compatible)
@app.route("/v1/chat", methods=["POST"])
async def enhanced_chat():
    """Enhanced chat endpoint with context and multi-provider support"""
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
        messages = [ChatMessage(role=MessageRole.USER.value, content=question)]

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


# Link analysis with AI processing
@app.route("/v1/analyze_and_chat", methods=["POST"])
async def analyze_and_chat():
    """Analyze a link and chat about its content"""
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
        messages = [ChatMessage(role=MessageRole.USER.value, content=question)]

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
    """Get web search cache statistics"""
    try:
        from src.utility.postgres import get_search_cache_stats, cleanup_expired_search_cache

        # Clean up expired entries first
        deleted = cleanup_expired_search_cache()

        # Get current stats
        stats = get_search_cache_stats()
        stats['deleted_expired'] = deleted

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/embed-user-notes", methods=["POST"])
async def embed_user_notes():
    """
    Admin endpoint to create embeddings for all notes of a user
    Useful for legacy users who don't have embeddings yet
    """
    try:
        data = await request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({
                "error": "user_id is required"
            }), 400

        # Get all note IDs for the user
        from src.utility.postgres import get_notes_for_rag
        note_ids = get_notes_for_rag(user_id, folder_ids=None, note_ids=None)

        if not note_ids:
            return jsonify({
                "message": f"No notes found for user {user_id}",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        from src.utility.postgres import get_notes_without_embeddings
        notes_without_embeddings = get_notes_without_embeddings(note_ids)

        if not notes_without_embeddings:
            return jsonify({
                "message": f"All {len(note_ids)} notes for user {user_id} already have embeddings",
                "embedded_notes": 0
            })

        # Create embeddings for notes that don't have them
        successfully_embedded = 0
        failed_notes = []

        for note_id in notes_without_embeddings:
            try:
                from src.utility.note_utils import create_and_save_embeddings
                create_and_save_embeddings(note_id)
                successfully_embedded += 1
                logger.info(f"Created embeddings for note {note_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create embeddings for note {note_id}: {e}")
                failed_notes.append(note_id)

        return jsonify({
            "message": f"Embedding process completed for user {user_id}",
            "total_notes": len(note_ids),
            "notes_needing_embeddings": len(notes_without_embeddings),
            "successfully_embedded": successfully_embedded,
            "failed_notes": failed_notes
        })

    except Exception as e:
        logger.error(f"Error in embed_user_notes: {e}")
        return jsonify({
            "error": f"Failed to embed user notes: {str(e)}"
        }), 500


@app.route("/admin/embed-all-notes", methods=["POST"])
async def embed_all_notes():
    """
    Admin endpoint to create embeddings for all notes in the system
    Use with caution - this can be expensive and time-consuming
    """
    try:
        data = await request.get_json()
        # Safety check - require explicit confirmation
        confirm = data.get("confirm_embed_all", False)

        if not confirm:
            return jsonify({
                "error": "This operation can be expensive. Set 'confirm_embed_all': true to proceed"
            }), 400

        # Get all note IDs in the system
        from src.utility.postgres import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM note_v1 
                    WHERE completed = true 
                    AND "ownerId" IS NOT NULL
                    ORDER BY id
                """)
                all_notes = [row[0] for row in cursor.fetchall()]

        if not all_notes:
            return jsonify({
                "message": "No notes found in the system",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        from src.utility.postgres import get_notes_without_embeddings
        notes_without_embeddings = get_notes_without_embeddings(all_notes)

        if not notes_without_embeddings:
            return jsonify({
                "message": f"All {len(all_notes)} notes in the system already have embeddings",
                "embedded_notes": 0
            })

        # Create embeddings in batches to avoid overwhelming the system
        successfully_embedded = 0
        failed_notes = []
        batch_size = 10  # Process 10 notes at a time

        for i in range(0, len(notes_without_embeddings), batch_size):
            batch = notes_without_embeddings[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: notes {batch}")

            for note_id in batch:
                try:
                    from src.utility.note_utils import create_and_save_embeddings
                    create_and_save_embeddings(note_id)
                    successfully_embedded += 1
                    logger.info(f"Created embeddings for note {note_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to create embeddings for note {note_id}: {e}")
                    failed_notes.append(note_id)

            # Small delay between batches to avoid rate limiting
            import asyncio
            await asyncio.sleep(1)

        return jsonify({
            "message": "System-wide embedding process completed",
            "total_notes": len(all_notes),
            "notes_needing_embeddings": len(notes_without_embeddings),
            "successfully_embedded": successfully_embedded,
            "failed_notes": failed_notes
        })

    except Exception as e:
        logger.error(f"Error in embed_all_notes: {e}")
        return jsonify({
            "error": f"Failed to embed all notes: {str(e)}"
        }), 500


@app.route("/notes/create-embeddings", methods=["POST"])
async def create_note_embeddings():
    """
    Create embeddings for one or more notes
    This endpoint should be called by the backend when notes are completed
    """
    try:
        data = await request.get_json()
        note_ids = data.get("note_ids", [])

        # Support both single note_id and note_ids array for flexibility
        if "note_id" in data and not note_ids:
            note_ids = [data["note_id"]]

        if not note_ids:
            return jsonify({
                "error": "Either 'note_id' or 'note_ids' array is required"
            }), 400

        results = []
        for note_id in note_ids:
            try:
                from src.utility.postgres import get_note_text
                note_text = get_note_text(note_id)

                if not note_text:
                    results.append({
                        "note_id": note_id,
                        "status": "error",
                        "message": "Note not found or has no content"
                    })
                    continue

                from src.utility.note_utils import create_and_save_embeddings
                embeddings = create_and_save_embeddings(note_id)

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


if __name__ == "__main__":
    logger.info("Starting YouWoAI ML Server...")
    logger.info("Server will be available at: http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
