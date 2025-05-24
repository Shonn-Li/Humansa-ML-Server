import math
from typing import List, Tuple

from llama_index.core import Document, Settings
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import RouterRetriever
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.tools import RetrieverTool
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from src.utility.postgres import get_embeddings, get_note_text, save_embeddings


def create_and_save_embeddings(note_id: int):
    splitter = SentenceSplitter(chunk_size=7000, chunk_overlap=200)
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    text = get_note_text(note_id)
    if not text:
        raise ValueError(f"No text for note {note_id}")

    # 1) split into chunks
    chunks = splitter.split_text(text)

    # 2) embed all chunks at once
    vectors = embedder._get_text_embeddings(chunks)  # returns List[List[float]]

    # 3) persist
    save_embeddings(note_id, vectors)
    return vectors


def retrieve_embedding(note_id: int):
    embedding = get_embeddings(note_id=note_id)
    if embedding is not None:
        return embedding

    # do not have the embedding stored, creating one now
    return create_and_save_embeddings(note_id=note_id)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_most_related_notes(
    user_question: str, note_ids: List[int], max_notes: int
) -> List[int]:
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    query_vec = embedder._get_text_embeddings([user_question])[0]

    scores = []
    for nid in note_ids:
        sections = retrieve_embedding(nid)
        sims = [_cosine_similarity(query_vec, sec) for sec in sections]
        scores.append((nid, max(sims)))

    # 4) pick top notes
    top_notes = [
        nid for nid, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:max_notes]
    ]
    return top_notes


def chat_bot(
    user_question: str,
    note_ids: List[int],
    max_notes: int = 3,  # only consider top 3 notes
    top_k_chunks: int = 2,  # only pull 1 chunk per note
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> str:
    """
    1) Ensure each note has a stored embedding via retrieve_embedding()
    2) Embed the question and rank notes by cosine similarity
    3) Load & chunk only the top notes, build on‐the‐fly vector stores
    4) Retrieve the top chunk per note and query the LLM
    """

    top_notes = get_most_related_notes(
        user_question=user_question, note_ids=note_ids, max_notes=max_notes
    )

    # 4) Fetch texts and run chunk‐and‐retrieve RAG on those top notes
    texts = [get_note_text(nid) for nid in top_notes]

    # 5) Configure LLM + embedder + chunker
    Settings.llm = OpenAI(model="gpt-4.1-mini")
    embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.embed_model = embed_model
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # 6) Build a retriever tool per top note
    retriever_tools = []
    for nid, text in zip(top_notes, texts):
        chunks = splitter.split_text(text)
        docs = [Document(text=chunk, metadata={"note_id": nid}) for chunk in chunks]
        index = VectorStoreIndex.from_documents(docs)
        retriever = index.as_retriever(similarity_top_k=top_k_chunks)
        tool = RetrieverTool.from_defaults(
            retriever=retriever,
            name=f"note_{nid}",
            description=f"Retriever for note {nid}",
        )
        retriever_tools.append(tool)

    # 7) Route + query
    selector = LLMSingleSelector.from_defaults()
    router = RouterRetriever(retriever_tools=retriever_tools, selector=selector)
    query_engine = RetrieverQueryEngine.from_args(retriever=router)
    response = query_engine.query(user_question)

    return str(response)


# Example usage
if __name__ == "__main__":

    answer = chat_bot("Where am I planning to travel?", [1, 2, 4, 5, 6, 7])
    print("Bot:", answer)
    # create_embedding(3)
