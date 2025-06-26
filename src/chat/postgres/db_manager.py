"""
Postgres Module - Clean database operations for chat system

This module handles:
- ID resolution (notes, folders, conversations)
- Mixed vector search on embedding_v1 table
- URL-based chunk lookup
- Database connection management
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USERNAME"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_ACTIVE_DATABASE"),
}


@dataclass
class ResolvedIDs:
    """Container for resolved IDs"""
    notes: List[int]
    conversations: List[int]


@dataclass
class ChunkResult:
    """Container for chunk search results"""
    type_id: int
    type: str  # 'note' or 'conversation'
    chunk_text: str
    similarity: float
    section_id: int
    metadata: Optional[Dict[str, Any]] = None


class PostgresManager:
    """Clean database operations manager"""

    def __init__(self):
        self.db_config = DB_CONFIG
        logger.info("PostgresManager initialized")

    @contextmanager
    def get_connection(self):
        """Database connection context manager"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def resolve_note_ids(self, user_id: int, note_ids: Optional[List[int]] = None,
                         folder_ids: Optional[List[int]] = None) -> List[int]:
        """
        Resolve note IDs based on priority:
        1. If note_ids provided: use them (validate ownership)
        2. If folder_ids provided: get notes from folders
        3. If neither: get all user notes
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Case 1: Specific note IDs provided
                if note_ids:
                    cursor.execute("""
                        SELECT id 
                        FROM note_v1 
                        WHERE "ownerId" = %s 
                        AND id = ANY(%s)
                        AND completed = true
                        ORDER BY id DESC
                    """, (user_id, note_ids))

                    results = cursor.fetchall()
                    validated_notes = [row[0] for row in results]

                    if len(validated_notes) < len(note_ids):
                        invalid_notes = set(note_ids) - set(validated_notes)
                        logger.warning(
                            f"Invalid note IDs for user {user_id}: {invalid_notes}")

                    logger.info(
                        f"Resolved {len(validated_notes)} specific note IDs")
                    return validated_notes

                # Case 2: Folder IDs provided
                elif folder_ids:
                    cursor.execute("""
                        SELECT DISTINCT n.id 
                        FROM note_v1 n
                        INNER JOIN folder_v1 f ON n."folderId" = f.id
                        WHERE f."ownerId" = %s 
                        AND f.id = ANY(%s)
                        AND n.completed = true
                        ORDER BY n.id DESC
                    """, (user_id, folder_ids))

                    results = cursor.fetchall()
                    folder_notes = [row[0] for row in results]
                    logger.info(
                        f"Resolved {len(folder_notes)} notes from folders")
                    return folder_notes

                # Case 3: All user notes
                else:
                    cursor.execute("""
                        SELECT id 
                        FROM note_v1 
                        WHERE "ownerId" = %s 
                        AND completed = true
                        ORDER BY id DESC
                    """, (user_id,))

                    results = cursor.fetchall()
                    all_notes = [row[0] for row in results]
                    logger.info(f"Resolved {len(all_notes)} total user notes")
                    return all_notes

    def resolve_conversation_ids(self, user_id: int,
                                 conversation_ids: Optional[List[int]] = None) -> List[int]:
        """
        Resolve conversation IDs:
        - If conversation_ids is None: get ALL user conversations (for embedding check)
        - If conversation_ids is provided: use them (could be empty list)
        """
        if conversation_ids is not None:
            logger.info(
                f"Using provided conversation IDs: {len(conversation_ids)}")
            return conversation_ids

        # Get ALL user conversations (not just ones with embeddings)
        # The embedding check happens later in the flow
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id
                    FROM conversation_v1
                    WHERE "ownerId" = %s
                    ORDER BY id DESC
                """, (user_id,))

                results = cursor.fetchall()
                conversation_ids = [row[0] for row in results]
                logger.info(
                    f"Resolved {len(conversation_ids)} total user conversations")
                return conversation_ids

    def resolve_all_ids(self, user_id: int, note_ids: Optional[List[int]] = None,
                        folder_ids: Optional[List[int]] = None,
                        conversation_ids: Optional[List[int]] = None) -> ResolvedIDs:
        """Resolve all IDs in one call"""
        resolved_notes = self.resolve_note_ids(user_id, note_ids, folder_ids)
        resolved_conversations = self.resolve_conversation_ids(
            user_id, conversation_ids)

        return ResolvedIDs(
            notes=resolved_notes,
            conversations=resolved_conversations
        )

    def mixed_vector_search(self, query_embedding: List[float], resolved_ids: ResolvedIDs,
                            top_k: int = 20) -> List[ChunkResult]:
        """
        Unified vector search across notes and conversations
        Single query to embedding_v1 table using type and type_id
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Convert embedding to pgvector format
                query_vector = '[' + ','.join(map(str, query_embedding)) + ']'

                # Build the WHERE clause dynamically
                where_conditions = []
                params = [query_vector]

                if resolved_ids.notes:
                    where_conditions.append(
                        "(type = 'note' AND type_id = ANY(%s))")
                    params.append(resolved_ids.notes)

                if resolved_ids.conversations:
                    where_conditions.append(
                        "(type = 'conversation' AND type_id = ANY(%s))")
                    params.append(resolved_ids.conversations)

                if not where_conditions:
                    logger.warning(
                        "No IDs to search - returning empty results")
                    return []

                where_clause = " OR ".join(where_conditions)
                params.extend([query_vector, top_k])

                query = f"""
                    SELECT 
                        type_id,
                        type,
                        chunk_text,
                        1 - (embedding <=> %s::vector) as similarity,
                        section_id
                    FROM embedding_v1 
                    WHERE {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """

                logger.info(
                    f"Mixed vector search - notes: {len(resolved_ids.notes)}, conversations: {len(resolved_ids.conversations)}")
                cursor.execute(query, params)
                results = cursor.fetchall()

                chunks = []
                for row in results:
                    chunk = ChunkResult(
                        type_id=row[0],
                        type=row[1],
                        chunk_text=row[2],
                        similarity=row[3],
                        section_id=row[4]
                    )
                    chunks.append(chunk)

                logger.info(
                    f"Mixed vector search found {len(chunks)} relevant chunks")
                return chunks

    def get_chunks_by_url(self, url: str) -> List[Dict[str, Any]]:
        """Get all chunks that belong to a specific URL"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        chunk_text,
                        section_id,
                        embedding,
                        url,
                        metadata
                    FROM embedding_v1
                    WHERE url = %s AND type = 'user'
                    ORDER BY section_id
                """, (url,))

                results = cursor.fetchall()
                chunks = [dict(row) for row in results]
                logger.info(f"Found {len(chunks)} chunks for URL: {url}")
                return chunks

    def similarity_search_within_url_chunks(self, query_embedding: List[float],
                                            url_chunks: List[Dict[str, Any]],
                                            top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform similarity search within chunks from a specific URL
        This is done in-memory since we already have the embeddings
        """
        if not url_chunks:
            return []

        import math

        def cosine_similarity(a: List[float], b: List[float]) -> float:
            """Calculate cosine similarity between two vectors"""
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

        def parse_vector(vector_text: str) -> List[float]:
            """Parse pgvector format to list of floats"""
            if vector_text.startswith('[') and vector_text.endswith(']'):
                vector_content = vector_text[1:-1]
                return [float(x.strip()) for x in vector_content.split(',')]
            return []

        # Calculate similarities
        scored_chunks = []
        for chunk in url_chunks:
            try:
                chunk_embedding = parse_vector(chunk['embedding'])
                if chunk_embedding:
                    similarity = cosine_similarity(
                        query_embedding, chunk_embedding)
                    scored_chunks.append((chunk, similarity))
            except Exception as e:
                logger.warning(f"Error processing chunk embedding: {e}")
                continue

        # Sort by similarity and return top k
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        top_chunks = scored_chunks[:top_k]

        logger.info(
            f"URL similarity search found {len(top_chunks)} relevant chunks")
        return top_chunks

    def get_note_text(self, note_id: int) -> str:
        """Get full text content of a note - for reference/debugging"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT "promptContent"
                    FROM note_v1 
                    WHERE id = %s
                """, (note_id,))

                result = cursor.fetchone()
                if not result:
                    return ""

                prompt_content = result[0]
                if prompt_content and isinstance(prompt_content, dict):
                    if "currentPromptContent" in prompt_content:
                        return prompt_content["currentPromptContent"].get("content", "")

                return ""

    def health_check(self) -> bool:
        """Simple database health check"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
