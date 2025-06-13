# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from src.utility.postgres import get_note_text
from src.ai_chat_bot.chat_bot import (chat_bot, create_and_save_embeddings,
                                      get_most_related_notes)
from quart import Quart, jsonify, request
import os
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


# Chat Bot
@app.route("/chat_bot", methods=["POST"])
async def query():
    data = await request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400

    note_ids = data.get("note_ids", [])
    if len(note_ids) == 0:
        return jsonify({"error": "No note_ids provided"}), 400

    response, top_notes = chat_bot(user_question=question, note_ids=note_ids)
    return jsonify({"answer": response, "used_notes": top_notes})


# Get most related notes
@app.route("/get_related_notes", methods=["POST"])
async def get_related_notes():
    data = await request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400

    note_ids = data.get("note_ids", [])
    if len(note_ids) == 0:
        return jsonify({"error": "No note_ids provided"}), 400

    max_notes = data.get("max_notes", 0)
    if max_notes <= 0:
        return jsonify({"error": "No max_notes provided"}), 400

    response = get_most_related_notes(
        user_question=question, note_ids=note_ids, max_notes=max_notes
    )
    return jsonify({"note_ids": response})


@app.route("/save_note_embedding", methods=["POST"])
async def save_embedding_api():
    """Temporary API to check the formatted note text for a given note ID"""
    data = await request.get_json()
    note_id = data.get("note_id", None)
    if note_id is None:
        return jsonify({"error": "No note_id provided"}), 400

    try:
        create_and_save_embeddings(note_id=note_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/note_text/<int:note_id>", methods=["GET"])
async def get_note_text_api(note_id):
    """Temporary API to check the formatted note text for a given note ID"""
    text = get_note_text(note_id)
    return jsonify({"note_id": note_id, "note_text": text})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
