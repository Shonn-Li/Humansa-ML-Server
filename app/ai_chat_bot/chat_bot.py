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

from app.utility.postgres import get_embedding, get_note_text, save_embedding

# Global settings config
Settings.llm = OpenAI(model="gpt-4o")  # Optional:  configure LLM
Settings.chunk_size = 512


def create_embedding(note_id: int):
    """
    Create an OpenAI embedding for the note and persist it via save_embedding().
    """
    # 1) Fetch the note text
    note = get_note_text(note_id)
    if not note:
        raise ValueError(f"No text found for note {note_id}")

    # 2) Generate embedding
    embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    # get_embeddings returns List[List[float]]; we take the first vector
    vector = embed_model._get_text_embeddings([note])[0]

    # 3) Persist via our helper
    save_embedding(note_id, vector)
    return vector


def retrieve_embedding(note_id: int):
    embedding = get_embedding(note_id=note_id)
    if embedding is not None:
        return embedding

    # do not have the embedding stored, creating one now
    return create_embedding(note_id=note_id)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_most_related_notes(
    user_question: str,
    note_ids: List[int],
    max_notes: int,  # only consider top 3 notes
) -> List[int]:
    """
    1) Ensure each note has a stored embedding via retrieve_embedding()
    2) Embed the question and rank notes by cosine similarity
    3) Load & chunk only the top notes, build on‐the‐fly vector stores
    4) Retrieve the top chunk per note and query the LLM
    """

    # 1) Ensure embeddings exist and collect them
    note_vecs: List[Tuple[int, List[float]]] = []
    for nid in note_ids:
        vec = retrieve_embedding(nid)
        note_vecs.append((nid, vec))

    # 2) Embed the question
    embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    query_vec = embed_model._get_text_embeddings([user_question])[0]

    # 3) Rank notes in Python
    ranked = sorted(
        note_vecs, key=lambda t: _cosine_similarity(query_vec, t[1]), reverse=True
    )
    top_notes = [nid for nid, _ in ranked[:max_notes]]
    return top_notes


def chat_bot(
    user_question: str,
    note_ids: List[int],
    max_notes: int = 3,  # only consider top 3 notes
    top_k_chunks: int = 1,  # only pull 1 chunk per note
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
    Settings.llm = OpenAI(model="gpt-4o")
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
