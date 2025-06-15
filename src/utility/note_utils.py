"""
Utility functions for note processing and embeddings
"""
import math
from typing import List
from llama_index.embeddings.openai import OpenAIEmbedding
from src.utility.postgres import get_embeddings, save_embeddings, get_note_text
from llama_index.core.text_splitter import SentenceSplitter


def create_and_save_embeddings(note_id: int):
    """Create and save embeddings for a note"""
    splitter = SentenceSplitter(chunk_size=7000, chunk_overlap=200)
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    text = get_note_text(note_id)
    if not text:
        raise ValueError(f"No text for note {note_id}")

    # 1) split into chunks
    chunks = splitter.split_text(text)

    # 2) embed all chunks at once
    vectors = embedder._get_text_embeddings(
        chunks)  # returns List[List[float]]

    # 3) persist
    save_embeddings(note_id, vectors)
    return vectors


def retrieve_embedding(note_id: int):
    """Retrieve or create embeddings for a note"""
    embedding = get_embeddings(note_id=note_id)
    if embedding is not None:
        return embedding

    # do not have the embedding stored, creating one now
    return create_and_save_embeddings(note_id=note_id)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_most_related_notes(
    user_question: str, note_ids: List[int], max_notes: int
) -> List[int]:
    """Get the most related notes based on embedding similarity"""
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    query_vec = embedder._get_text_embeddings([user_question])[0]

    scores = []
    for nid in note_ids:
        sections = retrieve_embedding(nid)
        sims = [_cosine_similarity(query_vec, sec) for sec in sections]
        scores.append((nid, max(sims)))

    # pick top notes
    top_notes = [
        nid for nid, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:max_notes]
    ]
    return top_notes
