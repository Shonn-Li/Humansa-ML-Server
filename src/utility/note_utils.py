"""
Utility functions for note processing and embeddings
"""
import math
from typing import List
import tiktoken
from llama_index.embeddings.openai import OpenAIEmbedding
from src.utility.postgres import get_embeddings, save_embeddings, get_note_text
from llama_index.core.text_splitter import SentenceSplitter
import logging

logger = logging.getLogger(__name__)

# OpenAI's embedding model token limits
EMBEDDING_MODEL_TOKEN_LIMIT = 8191  # For text-embedding-3-small
MAX_BATCH_TOKENS = 300000  # OpenAI's batch limit


def _count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """Count tokens for the embedding model"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by text-embedding-3-small)
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def create_and_save_embeddings(note_id: int):
    """Create and save embeddings for a note with proper token handling"""
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    text = get_note_text(note_id)
    if not text:
        raise ValueError(f"No text for note {note_id}")

    # First, split by sentences to maintain coherence
    splitter = SentenceSplitter(chunk_size=7000, chunk_overlap=200)
    initial_chunks = splitter.split_text(text)

    # Then, ensure each chunk fits within token limits
    final_chunks = []
    for chunk in initial_chunks:
        token_count = _count_tokens(chunk)

        if token_count <= EMBEDDING_MODEL_TOKEN_LIMIT:
            final_chunks.append(chunk)
        else:
            # Further split large chunks
            logger.warning(
                f"Chunk for note {note_id} has {token_count} tokens, splitting further"
            )

            # Split by approximate character count based on token ratio
            chars_per_token = len(chunk) / token_count
            target_chunk_size = int(
                EMBEDDING_MODEL_TOKEN_LIMIT * chars_per_token * 0.9
            )  # 90% to be safe

            sub_splitter = SentenceSplitter(
                chunk_size=target_chunk_size,
                chunk_overlap=min(200, target_chunk_size // 10),
            )
            sub_chunks = sub_splitter.split_text(chunk)

            # Verify each sub-chunk fits
            for sub_chunk in sub_chunks:
                sub_token_count = _count_tokens(sub_chunk)
                if sub_token_count <= EMBEDDING_MODEL_TOKEN_LIMIT:
                    final_chunks.append(sub_chunk)
                else:
                    # If still too large, do hard truncation
                    logger.error(
                        f"Sub-chunk still has {sub_token_count} tokens, truncating"
                    )
                    encoding = tiktoken.get_encoding("cl100k_base")
                    tokens = encoding.encode(sub_chunk)
                    truncated_tokens = tokens[:EMBEDDING_MODEL_TOKEN_LIMIT]
                    truncated_text = encoding.decode(truncated_tokens)
                    final_chunks.append(truncated_text)

    if not final_chunks:
        raise ValueError(f"No valid chunks generated for note {note_id}")

    logger.info(
        f"Note {note_id}: {len(initial_chunks)} initial chunks -> {len(final_chunks)} final chunks"
    )

    # Process embeddings in batches to respect API limits
    all_embeddings = []
    batch_chunks = []
    batch_token_count = 0

    for chunk in final_chunks:
        chunk_tokens = _count_tokens(chunk)

        # Check if adding this chunk would exceed batch limit
        if batch_chunks and (
            batch_token_count +
                chunk_tokens > MAX_BATCH_TOKENS or len(batch_chunks) >= 50
        ):
            # Process current batch
            logger.info(
                f"Processing batch of {len(batch_chunks)} chunks with {batch_token_count} total tokens"
            )
            batch_embeddings = embedder._get_text_embeddings(batch_chunks)
            all_embeddings.extend(batch_embeddings)

            # Reset batch
            batch_chunks = [chunk]
            batch_token_count = chunk_tokens
        else:
            batch_chunks.append(chunk)
            batch_token_count += chunk_tokens

    # Process remaining chunks
    if batch_chunks:
        logger.info(
            f"Processing final batch of {len(batch_chunks)} chunks with {batch_token_count} total tokens"
        )
        batch_embeddings = embedder._get_text_embeddings(batch_chunks)
        all_embeddings.extend(batch_embeddings)

    # Save embeddings
    save_embeddings(note_id, all_embeddings)
    return all_embeddings


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


def get_most_related_notes_pgvector(
    user_question: str, note_ids: List[int], max_notes: int
) -> List[int]:
    """
    Ultra-fast similarity search using pgvector
    This is what big companies use - let the database do the heavy lifting!
    Automatically creates embeddings for notes that don't have them.
    """
    logger.info(
        f"Starting pgvector similarity search for {len(note_ids)} notes")

    # Check which notes don't have embeddings and create them
    from src.utility.postgres import get_notes_without_embeddings
    notes_without_embeddings = get_notes_without_embeddings(note_ids)

    if notes_without_embeddings:
        logger.info(
            f"Found {len(notes_without_embeddings)} notes without embeddings, creating them...")
        for note_id in notes_without_embeddings:
            try:
                create_and_save_embeddings(note_id)
                logger.info(f"Created embeddings for note {note_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create embeddings for note {note_id}: {e}")
                # Continue with other notes
                continue

    # Generate query embedding
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    query_embedding = embedder._get_text_embeddings([user_question])[0]

    # Use pgvector for similarity search
    from src.utility.postgres import vector_similarity_search

    results = vector_similarity_search(query_embedding, note_ids, max_notes)

    # Extract note IDs
    top_notes = [note_id for note_id, similarity in results]

    logger.info(
        f"Pgvector search completed in milliseconds, found {len(top_notes)} similar notes"
    )
    return top_notes


def get_most_related_notes(
    user_question: str, note_ids: List[int], max_notes: int
) -> List[int]:
    """Get the most related notes based on embedding similarity"""
    # Try pgvector first (this is the fast path)
    try:
        return get_most_related_notes_pgvector(user_question, note_ids, max_notes)
    except Exception as e:
        logger.warning(
            f"Pgvector search failed, falling back to slow method: {e}")
        # Fallback to the existing slow implementation
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
