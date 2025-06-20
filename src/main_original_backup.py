# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from src.utility.postgres import get_note_text
from quart import Quart, jsonify, request, Response
import os
import json
import base64
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from enum import Enum

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
            # NEW: Citations enable deep search
            enable_citations=data.get("enable_citations", False),
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
    
    Returns immediately with a job_id. Use /jobs/{job_id} to check progress.
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

        # Create background job
        job_id = create_background_job("embed_user_notes", user_id)
        
        # Start background task
        asyncio.create_task(run_embedding_job(
            job_id=job_id,
            job_type="embed_user_notes",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        return jsonify({
            "message": f"Embedding job started for user {user_id}",
            "job_id": job_id,
            "user_id": user_id,
            "total_notes": len(note_ids),
            "notes_to_embed": len(notes_without_embeddings),
            "status_url": f"/jobs/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error in embed_user_notes: {e}")
        return jsonify({
            "error": f"Failed to start embedding job: {str(e)}"
        }), 500


@app.route("/admin/embed-all-notes", methods=["POST"])
async def embed_all_notes():
    """
    Admin endpoint to create embeddings for all notes in the system
    Use with caution - this can be expensive and time-consuming
    
    Returns immediately with a job_id. Use /jobs/{job_id} to check progress.
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

        # Create background job
        job_id = create_background_job("embed_all_notes")
        
        # Start background task
        asyncio.create_task(run_embedding_job(
            job_id=job_id,
            job_type="embed_all_notes",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        return jsonify({
            "message": "System-wide embedding job started",
            "job_id": job_id,
            "total_notes": len(all_notes),
            "notes_to_embed": len(notes_without_embeddings),
            "status_url": f"/jobs/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error in embed_all_notes: {e}")
        return jsonify({
            "error": f"Failed to embed all notes: {str(e)}"
        }), 500


@app.route("/admin/re-embed-all-notes", methods=["POST"])
async def re_embed_all_notes():
    """
    Admin endpoint to RE-EMBED all notes with the new optimized 1024-token chunks
    This will delete existing embeddings and create new ones with better settings
    Use this after updating the embedding pipeline
    
    Returns immediately with a job_id. Use /jobs/{job_id} to check progress.
    """
    try:
        data = await request.get_json()
        # Safety check - require explicit confirmation
        confirm = data.get("confirm_re_embed_all", False)

        if not confirm:
            return jsonify({
                "error": "This operation will delete existing embeddings and recreate them. Set 'confirm_re_embed_all': true to proceed"
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
                "re_embedded_notes": 0
            })

        # Force delete ALL existing embeddings first
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM embedding_v1")
                conn.commit()
                logger.info("Deleted all existing embeddings")

        # Create background job
        job_id = create_background_job("re_embed_all_notes")
        
        # Start background task
        asyncio.create_task(run_embedding_job(
            job_id=job_id,
            job_type="re_embed_all_notes", 
            note_ids=all_notes,
            batch_size=5
        ))

        return jsonify({
            "message": "Re-embedding job started in background",
            "job_id": job_id,
            "total_notes": len(all_notes),
            "status_url": f"/jobs/{job_id}",
            "optimization_applied": {
                "chunk_size": 1024,
                "chunk_overlap": 100,
                "separate_ai_user_content": True,
                "source_tagging": True
            }
        })

    except Exception as e:
        logger.error(f"Error in re_embed_all_notes: {e}")
        return jsonify({
            "error": f"Failed to start re-embedding job: {str(e)}"
        }), 500
        return jsonify({
            "error": f"Failed to re-embed all notes: {str(e)}"
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


@app.route("/search/keyword", methods=["POST"])
async def keyword_search_endpoint():
    """
    Keyword search endpoint using PostgreSQL full-text search on chunk content.
    Fast BM25-style search using tsvector and GIN index.
    """
    try:
        request_data = await request.get_json()

        if not request_data:
            return jsonify({"error": "Request body is required"}), 400

        query = request_data.get("query", "").strip()
        user_id = request_data.get("user_id")
        limit = request_data.get("limit", 20)

        if not query:
            return jsonify({"error": "Query is required"}), 400

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            limit = 20

        logger.info(
            f"Keyword search for user {user_id}: '{query}' (limit: {limit})")

        from src.utility.postgres import keyword_search
        results = keyword_search(query, user_id, limit)

        # Format results
        formatted_results = []
        for note_id, chunk_text, source, rank in results:
            formatted_results.append({
                "note_id": note_id,
                "chunk_text": chunk_text,
                "source": source,
                "relevance_score": float(rank),
                "preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            })

        return jsonify({
            "query": query,
            "user_id": user_id,
            "total_results": len(formatted_results),
            "results": formatted_results
        })

    except Exception as e:
        logger.error(f"Error in keyword search endpoint: {e}")
        return jsonify({
            "error": f"Search failed: {str(e)}"
        }), 500


@app.route("/search/advanced", methods=["POST"])
async def advanced_search_endpoint():
    """
    Advanced keyword search endpoint with source filtering and better query processing.
    """
    try:
        request_data = await request.get_json()

        if not request_data:
            return jsonify({"error": "Request body is required"}), 400

        query = request_data.get("query", "").strip()
        user_id = request_data.get("user_id")
        # Optional: 'summary', 'youtube', 'doc', etc.
        source_filter = request_data.get("source_filter")
        limit = request_data.get("limit", 20)

        if not query:
            return jsonify({"error": "Query is required"}), 400

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            limit = 20

        logger.info(
            f"Advanced search for user {user_id}: '{query}' (source: {source_filter}, limit: {limit})")

        from src.utility.postgres import advanced_keyword_search
        results = advanced_keyword_search(query, user_id, source_filter, limit)

        # Format results with grouping by note
        note_groups = {}
        for note_id, chunk_text, source, rank, note_title in results:
            if note_id not in note_groups:
                note_groups[note_id] = {
                    "note_id": note_id,
                    "note_title": note_title,
                    "chunks": [],
                    "max_relevance": 0.0
                }

            chunk_info = {
                "chunk_text": chunk_text,
                "source": source,
                "relevance_score": float(rank),
                "preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            }

            note_groups[note_id]["chunks"].append(chunk_info)
            note_groups[note_id]["max_relevance"] = max(
                note_groups[note_id]["max_relevance"], float(rank))

        # Sort notes by maximum relevance
        sorted_notes = sorted(note_groups.values(),
                              key=lambda x: x["max_relevance"], reverse=True)

        return jsonify({
            "query": query,
            "user_id": user_id,
            "source_filter": source_filter,
            "total_notes": len(sorted_notes),
            "total_chunks": len(results),
            "results": sorted_notes
        })

    except Exception as e:
        logger.error(f"Error in advanced search endpoint: {e}")
        return jsonify({
            "error": f"Advanced search failed: {str(e)}"
        }), 500


# Background job system
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundJob:
    def __init__(self, job_id: str, job_type: str, user_id: int = None):
        self.job_id = job_id
        self.job_type = job_type
        self.user_id = user_id
        self.status = JobStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.total_items = 0
        self.processed_items = 0
        self.failed_items = 0
        self.error_message = None
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "error_message": self.error_message,
            "result": self.result
        }

# Global job storage (in production, use Redis or database)
background_jobs: Dict[str, BackgroundJob] = {}

def create_background_job(job_type: str, user_id: int = None) -> str:
    """Create a new background job and return its ID"""
    job_id = str(uuid.uuid4())
    job = BackgroundJob(job_id, job_type, user_id)
    background_jobs[job_id] = job
    return job_id

async def run_embedding_job(job_id: str, job_type: str, note_ids: list, **kwargs):
    """Run embedding job in background"""
    job = background_jobs.get(job_id)
    if not job:
        return
    
    try:
        job.status = JobStatus.RUNNING  
        job.started_at = datetime.now(timezone.utc)
        job.total_items = len(note_ids)
        
        logger.info(f"Starting background job {job_id}: {job_type} for {len(note_ids)} notes")
        
        successfully_processed = 0
        failed_notes = []
        batch_size = kwargs.get('batch_size', 5)
        
        # Import the embedding function
        from src.utility.note_utils import create_and_save_embeddings_separate
        
        for i in range(0, len(note_ids), batch_size):
            batch = note_ids[i:i + batch_size]
            logger.info(f"Job {job_id}: Processing batch {i//batch_size + 1}: notes {batch}")
            
            for note_id in batch:
                try:
                    create_and_save_embeddings_separate(note_id)
                    successfully_processed += 1
                    job.processed_items = successfully_processed
                    job.progress = int((successfully_processed / len(note_ids)) * 100)
                    logger.info(f"Job {job_id}: Processed note {note_id}")
                except Exception as e:
                    logger.error(f"Job {job_id}: Failed to process note {note_id}: {e}")
                    failed_notes.append({
                        "note_id": note_id,
                        "error": str(e)
                    })
                    job.failed_items = len(failed_notes)
            
            # Small delay between batches
            await asyncio.sleep(2)
        
        # Job completed
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.result = {
            "total_notes": len(note_ids),
            "successfully_processed": successfully_processed,
            "failed_notes": failed_notes,
            "job_type": job_type
        }
        
        logger.info(f"Background job {job_id} completed: {successfully_processed}/{len(note_ids)} notes processed")
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        logger.error(f"Background job {job_id} failed: {e}")


@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    """Get the status of a background job"""
    job = background_jobs.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job.to_dict())


@app.route("/jobs", methods=["GET"])
async def list_jobs():
    """List all background jobs (for debugging)"""
    return jsonify({
        "jobs": [job.to_dict() for job in background_jobs.values()],
        "total": len(background_jobs)
    })


@app.route("/admin/resume-embeddings", methods=["POST"])
async def resume_embeddings():
    """
    Resume embedding creation for notes that don't have embeddings yet.
    This is useful for continuing after a failed embedding job.
    
    Returns immediately with a job_id. Use /jobs/{job_id} to check progress.
    """
    try:
        data = await request.get_json()
        user_id = data.get("user_id")  # Optional: limit to specific user
        
        # Get all note IDs (optionally filtered by user)
        from src.utility.postgres import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if user_id:
                    cursor.execute("""
                        SELECT id FROM note_v1 
                        WHERE completed = true 
                        AND "ownerId" = %s
                        ORDER BY id
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT id FROM note_v1 
                        WHERE completed = true 
                        AND "ownerId" IS NOT NULL
                        ORDER BY id
                    """)
                all_notes = [row[0] for row in cursor.fetchall()]

        if not all_notes:
            return jsonify({
                "message": "No notes found",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        from src.utility.postgres import get_notes_without_embeddings
        notes_without_embeddings = get_notes_without_embeddings(all_notes)

        if not notes_without_embeddings:
            return jsonify({
                "message": f"All notes already have embeddings",
                "total_notes": len(all_notes),
                "embedded_notes": 0
            })

        # Create background job
        job_id = create_background_job("resume_embeddings", user_id)
        
        # Start background task
        asyncio.create_task(run_embedding_job(
            job_id=job_id,
            job_type="resume_embeddings",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        return jsonify({
            "message": "Resume embedding job started",
            "job_id": job_id,
            "user_id": user_id,
            "total_notes": len(all_notes),
            "notes_to_embed": len(notes_without_embeddings),
            "status_url": f"/jobs/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error in resume_embeddings: {e}")
        return jsonify({
            "error": f"Failed to start resume embedding job: {str(e)}"
        }), 500


if __name__ == "__main__":
    logger.info("Starting YouWoAI ML Server...")
    logger.info("Server will be available at: http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
