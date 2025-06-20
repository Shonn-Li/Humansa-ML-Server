"""
Utility functions for note processing and embeddings
"""
import math
from typing import List, Tuple
from llama_index.embeddings.openai import OpenAIEmbedding
from src.utility.postgres import get_embeddings, save_embeddings, get_note_text
from llama_index.core.text_splitter import SentenceSplitter
import logging

logger = logging.getLogger(__name__)


def create_and_save_embeddings(note_id: int):
    """Create and save embeddings for a note with optimized 1024-token chunks"""
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    text = get_note_text(note_id)
    if not text:
        raise ValueError(f"No text for note {note_id}")

    # Split using optimized chunk size for better retrieval
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=100)
    chunks = splitter.split_text(text)

    if not chunks:
        raise ValueError(f"No valid chunks generated for note {note_id}")

    logger.info(
        f"Note {note_id}: Generated {len(chunks)} chunks with 1024-token size")

    # Process embeddings in batches to respect API limits
    all_embeddings = []
    batch_chunks = []
    batch_size = 50  # Process 50 chunks at a time

    for chunk in chunks:
        batch_chunks.append(chunk)

        # Process batch when full or at the end
        if len(batch_chunks) >= batch_size:
            logger.info(f"Processing batch of {len(batch_chunks)} chunks")
            batch_embeddings = embedder._get_text_embeddings(batch_chunks)
            all_embeddings.extend(batch_embeddings)
            batch_chunks = []

    # Process remaining chunks
    if batch_chunks:
        logger.info(f"Processing final batch of {len(batch_chunks)} chunks")
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
    return create_and_save_embeddings_separate(note_id=note_id)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def get_most_related_notes_pgvector(
    user_question: str, note_ids: List[int], max_notes: int = 8
) -> List[int]:
    """
    Ultra-fast similarity search using pgvector with optimized retrieval for 1024-token chunks
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
                create_and_save_embeddings_separate(note_id)
                logger.info(f"Created embeddings for note {note_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create embeddings for note {note_id}: {e}")
                # Continue with other notes
                continue

    # Generate query embedding
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    query_embedding = embedder._get_text_embeddings([user_question])[0]

    # Use pgvector for similarity search with higher top_k for smaller chunks
    from src.utility.postgres import vector_similarity_search

    # Use higher similarity search to compensate for smaller chunks
    results = vector_similarity_search(
        query_embedding, note_ids, max_notes * 2)

    # Extract note IDs
    top_notes = [note_id for note_id, similarity in results[:max_notes]]

    logger.info(
        f"Pgvector search completed, found {len(top_notes)} similar notes from {len(results)} candidates"
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


def get_most_related_chunks_pgvector(
    user_question: str, note_ids: List[int], max_chunks: int = 20
) -> List[Tuple[int, str, float]]:
    """
    Ultra-fast CHUNK-level similarity search using pgvector
    Returns the most relevant chunks across ALL notes, not just top notes.
    
    Returns:
        List of (note_id, chunk_text, similarity_score) tuples
    """
    logger.info(
        f"Starting pgvector chunk-level similarity search for {len(note_ids)} notes")

    # Check which notes don't have embeddings and create them
    from src.utility.postgres import get_notes_without_embeddings
    notes_without_embeddings = get_notes_without_embeddings(note_ids)

    if notes_without_embeddings:
        logger.info(
            f"Found {len(notes_without_embeddings)} notes without embeddings, creating them...")
        for note_id in notes_without_embeddings:
            try:
                create_and_save_embeddings_separate(note_id)
                logger.info(f"Created embeddings for note {note_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create embeddings for note {note_id}: {e}")
                # Continue with other notes
                continue

    # Generate query embedding
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    query_embedding = embedder._get_text_embeddings([user_question])[0]

    # Use pgvector for chunk-level similarity search
    from src.utility.postgres import vector_chunk_similarity_search

    # Get the most relevant chunks directly (note_id, section_id, similarity)
    chunk_results = vector_chunk_similarity_search(
        query_embedding, note_ids, max_chunks)

    # Now extract the chunk text directly from the results (no need to reconstruct)
    final_chunks = []
    
    for note_id, section_id, similarity, chunk_text, source in chunk_results:
        # Use the pre-stored chunk text directly
        if chunk_text and chunk_text.strip():
            final_chunks.append((note_id, chunk_text, similarity))
            logger.info(f"Found chunk from note {note_id} section {section_id} (similarity: {similarity:.3f}, source: {source})")
        else:
            logger.warning(f"Empty chunk text for note {note_id} section {section_id}")

    logger.info(
        f"Pgvector chunk search completed, found {len(final_chunks)} relevant chunks"
    )
    return final_chunks


def create_and_save_embeddings_separate(note_id: int):
    """
    Create and save embeddings for a note with separate AI and user content
    This prevents mixed chunks that contain both AI summaries and user content
    """
    from src.utility.postgres import get_note_content_separate, save_embeddings_with_chunks
    
    embedder = OpenAIEmbedding(model="text-embedding-3-small")
    
    # Get separated content
    ai_content, user_content, note_type = get_note_content_separate(note_id)
    
    if not ai_content and not user_content:
        raise ValueError(f"No content found for note {note_id}")

    logger.info(f"Note {note_id}: Processing AI content ({len(ai_content)} chars) and user content ({len(user_content)} chars) separately")

    # Split using optimized chunk size for better retrieval
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=100)
    
    embeddings_data = []  # List of (embedding_vector, chunk_text, source) tuples
    all_chunks_for_embedding = []  # For batch processing
    chunk_metadata = []  # Track source info for each chunk

    # Process AI content (summaries) separately
    if ai_content.strip():
        ai_chunks = splitter.split_text(ai_content)
        logger.info(f"Note {note_id}: Generated {len(ai_chunks)} AI content chunks")
        
        for chunk in ai_chunks:
            all_chunks_for_embedding.append(chunk)
            chunk_metadata.append((chunk, "summary"))  # source = "summary" for AI content

    # Process user content separately
    if user_content.strip():
        user_chunks = splitter.split_text(user_content)
        logger.info(f"Note {note_id}: Generated {len(user_chunks)} user content chunks ({note_type})")
        
        for chunk in user_chunks:
            all_chunks_for_embedding.append(chunk)
            chunk_metadata.append((chunk, note_type))  # source = note_type for user content

    if not all_chunks_for_embedding:
        raise ValueError(f"No valid chunks generated for note {note_id}")

    # Process embeddings in batches to respect API limits
    batch_size = 50
    all_embeddings = []
    
    for i in range(0, len(all_chunks_for_embedding), batch_size):
        batch_chunks = all_chunks_for_embedding[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} with {len(batch_chunks)} chunks")
        batch_embeddings = embedder._get_text_embeddings(batch_chunks)
        all_embeddings.extend(batch_embeddings)

    # Combine embeddings with metadata
    for i, (embedding, (chunk_text, source)) in enumerate(zip(all_embeddings, chunk_metadata)):
        embeddings_data.append((embedding, chunk_text, source))

    # Save embeddings with chunk text and source
    save_embeddings_with_chunks(note_id, embeddings_data)
    
    logger.info(f"Note {note_id}: Saved {len(embeddings_data)} embeddings with separate content")
    return embeddings_data
