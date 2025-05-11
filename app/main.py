from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from quart import Quart, jsonify, request

app = Quart(__name__)


# Load LlamaIndex model on startup
@app.before_serving
async def load_model():
    global index
    documents = SimpleDirectoryReader("data").load_data()
    index = GPTVectorStoreIndex.from_documents(documents)


# Health check route
@app.route("/ping", methods=["GET"])
async def ping():
    return jsonify({"message": "Hi from YouWoAI"})


# Inference route
@app.route("/query", methods=["POST"])
async def query():
    data = await request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400

    query_engine = index.as_query_engine()
    response = query_engine.query(question)
    return jsonify({"answer": str(response)})


if __name__ == "__main__":
    app.run()
