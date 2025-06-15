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
    if not LINK_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Link analyzer not available",
            "details": LINK_ANALYZER_ERROR if 'LINK_ANALYZER_ERROR' in globals() else "Import failed"
        }), 500

    data = await request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Optional, will auto-detect if not provided
    platform = data.get("platform")
    options = data.get("options", {})  # Optional parameters

    try:
        result = analyze_link(url, platform=platform, options=options)
        return jsonify(result)
    except Exception as e:
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
            note_ids=data.get("note_ids"),
            enable_web_search=data.get("enable_web_search", False),
            enable_image_analysis=data.get("enable_image_analysis", False),
            search_query=data.get("search_query"),
            attachments=data.get("attachments")
        )

        # Generate response
        if chat_request.stream:
            async def generate():
                async for chunk in await enhanced_chat_bot.chat_completion(chat_request):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return Response(generate(), mimetype="text/plain")
        else:
            response = await enhanced_chat_bot.chat_completion(chat_request)
            return jsonify(response.__dict__)

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
            note_ids=data.get("note_ids", []),
            enable_web_search=data.get("enable_web_search", False),
            search_query=data.get("search_query"),
            attachments=data.get("attachments"),
            stream=data.get("stream", False)
        )

        if chat_request.stream:
            async def generate():
                async for chunk in await enhanced_chat_bot.chat_completion(chat_request):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return Response(generate(), mimetype="text/event-stream")
        else:
            response = await enhanced_chat_bot.chat_completion(chat_request)

            # Format response for backward compatibility
            return jsonify({
                "answer": response.choices[0]["message"]["content"],
                "provider": response.provider,
                "model": response.model,
                "used_notes": response.used_notes,
                "search_results": response.search_results,
                "usage": response.usage.__dict__ if response.usage else None
            })

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
