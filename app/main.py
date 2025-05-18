# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from quart import Quart, jsonify, request

from app.ai_chat_bot.chat_bot import chat_bot
from app.utility.postgres import get_note_text

app = Quart(__name__)


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

    response = chat_bot(user_question=question, note_ids=note_ids)
    return jsonify({"answer": response})


@app.route("/note_text/<int:note_id>", methods=["GET"])
async def get_note_text_api(note_id):
    """Temporary API to check the formatted note text for a given note ID"""
    text = get_note_text(note_id)
    return jsonify({
        "note_id": note_id,
        "note_text": text
    })

if __name__ == "__main__":
    app.run(port=5001)
