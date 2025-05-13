import os
from typing import List

from llama_index.core import (Document, Settings, StorageContext,
                              VectorStoreIndex, load_index_from_storage)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import RouterRetriever
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.tools import RetrieverTool
from llama_index.llms.openai import OpenAI

# Global settings config
Settings.llm = OpenAI(model="gpt-3.5-turbo")  # Optional: configure LLM
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
    """Answer the question based on the notes of the users"""

    indexes = []

    for note_id in note_ids:
        persist_dir = f"./vector_store/{note_id}"
        if not os.path.exists(persist_dir):
            raise ValueError(f"Note ID {note_id} has not been saved yet.")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
        indexes.append(index)

    # Step 1: Create retriever tools with tool names
    retriever_tools = [
        RetrieverTool.from_defaults(
            retriever=r,
            name=f"note_{i}",  # tool name must be unique
            description=f"Retriever for note {note_ids[i]}",
        )
        for i, r in enumerate([idx.as_retriever() for idx in indexes])
    ]

    # Step 2: Use default selector
    selector = LLMSingleSelector.from_defaults()

    # Step 3: Construct router
    router = RouterRetriever(retriever_tools=retriever_tools, selector=selector)

    # Step 4: Query
    query_engine = RetrieverQueryEngine.from_args(retriever=router)
    response = query_engine.query(user_question)
    return str(response)


# Example usage
if __name__ == "__main__":
    save_note(1, "Japan trip: Book flights to Tokyo. Visit Kyoto. Pack warm clothes.")
    save_note(2, "Shopping list: apples, bananas, oranges, and oat milk.")

    answer = chat_bot("Where am I planning to travel?", [1, 2])
    print("Bot:", answer)
