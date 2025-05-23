import os
from typing import List

from llama_index.core import Document, Settings
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import RouterRetriever
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.tools import RetrieverTool
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from app.utility.postgres import get_note_text

# Global settings config
Settings.llm = OpenAI(model="gpt-3.5-turbo")  # Optional:  configure LLM
Settings.chunk_size = 512


def save_note(note_id: int, note: str) -> None:
    """Create a vector representation of the note and save it to the disk"""
    # Create chunks with metadata
    splitter = SentenceSplitter(chunk_size=512)
    chunks = splitter.split_text(note)
    documents = [
        Document(text=chunk, metadata={"note_id": note_id}) for chunk in chunks
    ]

    # Create index and persist it to ./vector_store/{note_id}
    persist_dir = f"./vector_store/{note_id}"
    os.makedirs(persist_dir, exist_ok=True)

    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=persist_dir)


def chat_bot(user_question: str, note_ids: List[int]) -> str:
    """Answer the question based on very long notes via in-memory RAG."""

    # 1) Load raw texts
    texts = [get_note_text(i) for i in note_ids]

    # 2) Set global settings (replaces ServiceContext)
    Settings.llm = OpenAI(model="gpt-3.5-turbo")
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    # 3) Build one tiny vector index per note
    retriever_tools = []
    for note_id, text in zip(note_ids, texts):
        doc = Document(text=text, doc_id=str(note_id))

        index = VectorStoreIndex.from_documents([doc])  # now uses global Settings

        retriever = index.as_retriever(similarity_top_k=3)

        tool = RetrieverTool.from_defaults(
            retriever=retriever,
            name=f"note_{note_id}",
            description=f"Retriever for note {note_id}",
        )
        retriever_tools.append(tool)

    # 4) Build router + query engine
    selector = LLMSingleSelector.from_defaults()
    router = RouterRetriever(retriever_tools=retriever_tools, selector=selector)
    query_engine = RetrieverQueryEngine.from_args(retriever=router)

    # 5) Issue the query
    response = query_engine.query(user_question)
    return str(response)


# Example usage
if __name__ == "__main__":

    answer = chat_bot("Where am I planning to travel?", [1, 2, 4, 5, 6, 7, 10, 12, 15])
    print("Bot:", answer)
