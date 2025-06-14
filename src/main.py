# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from quart import Quart, jsonify, request

from src.ai_chat_bot.chat_bot import (chat_bot, create_and_save_embeddings,
                                      get_most_related_notes)
from src.utility.postgres import get_note_text

app = Quart(__name__)


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
    
    platform = data.get("platform")  # Optional, will auto-detect if not provided
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
    app.run(port=5003)
