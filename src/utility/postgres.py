import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging

from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

# Set up logging
logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv()

# Read database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USERNAME"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_ACTIVE_DATABASE"),
}


def get_db_connection():
    """Establish a PostgreSQL connection"""
    # print(DB_CONFIG)
    return psycopg2.connect(**DB_CONFIG)


def get_note_text(note_id: int) -> str:
    """Fetch the text representation of a note from Postgres database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Get note and prompt content
            cursor.execute(
                """
                SELECT "promptContent"
                FROM note_v1 
                WHERE id = %s
            """,
                (note_id,),
            )
            result = cursor.fetchone()

            if not result:
                return "Note not found"

            prompt_content = result[0]

            # Extract current prompt content from JSON
            current_prompt = ""
            if prompt_content and isinstance(prompt_content, dict):
                if (
                    "currentPromptContent" in prompt_content
                    and prompt_content["currentPromptContent"]
                ):
                    current_prompt = prompt_content["currentPromptContent"].get(
                        "content", ""
                    )

            # Get prefix images (not associated with any part)
            cursor.execute(
                """
                SELECT "imageURL", "imageText", "latex"
                FROM image_v1
                WHERE "noteId" = %s AND "partId" IS NULL
                ORDER BY id
            """,
                (note_id,),
            )
            prefix_images = cursor.fetchall()

            # Get parts in order
            cursor.execute(
                """
                SELECT id, "text"
                FROM part_v1
                WHERE "noteId" = %s
                ORDER BY "order"
            """,
                (note_id,),
            )
            parts = cursor.fetchall()

    # Assemble transcript
    transcript_parts = []

    # Add prefix images
    for img_url, img_text, is_latex in prefix_images:
        if img_text:
            transcript_parts.append(img_text)

    # Process each part and its images
    for part_id, part_text in parts:
        # Add part text
        transcript_parts.append(part_text)

        # Get images for this part
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT "imageURL", "imageText", "latex"
                    FROM image_v1
                    WHERE "partId" = %s
                    ORDER BY id
                """,
                    (part_id,),
                )
                part_images = cursor.fetchall()

        # Add part's images
        for img_url, img_text, is_latex in part_images:
            if img_text:
                transcript_parts.append(img_text)

    # Combine everything
    assembled_transcript = "\n\n".join(transcript_parts)

    # Format final output
    final_text = (
        f"AI Content:\n{current_prompt}\n\nUserContent:\n{assembled_transcript}"
    )

    return final_text


def get_part_text(note_id: int) -> str:
    """Fetch the text representation of a note from Postgres database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql_command = f"""SELECT "text" FROM part_v1
WHERE "noteId" = {note_id}
ORDER BY "order"
"""
            cursor.execute(sql_command)
            results = cursor.fetchall()  # ← returns a list of all matching rows

    # results is a list of tuples, e.g. [("first text",), ("second text",), ...]
    lst = [text for (text,) in results]
    return "\n".join(lst)


def save_embeddings_with_chunks(note_id: int, embeddings_data: List[tuple]):
    """
    Save embeddings with chunk text and source to embedding_v1 table
    embeddings_data: List of (embedding_vector, chunk_text, source) tuples
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Delete existing embeddings for this note
            cursor.execute(
                "DELETE FROM embedding_v1 WHERE note_id = %s", (note_id,))

            # Insert new embeddings with chunk text and source
            for section_id, (embedding, chunk_text, source) in enumerate(embeddings_data):
                # Convert to pgvector format
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                cursor.execute(
                    """
                    INSERT INTO embedding_v1 (note_id, section_id, embedding, chunk_text, source, last_updated)
                    VALUES (%s, %s, %s::vector, %s, %s, NOW())
                """,
                    (note_id, section_id, embedding_str, chunk_text, source),
                )

            conn.commit()
            logger.info(
                f"Saved {len(embeddings_data)} embeddings with chunks for note {note_id}")
    except Exception as e:
        logger.error(f"Error saving embeddings with chunks: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def save_embeddings(note_id: int, embeddings: List[List[float]]):
    """Save embeddings to embedding_v1 table using pgvector format (legacy function)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Delete existing embeddings for this note
            cursor.execute(
                "DELETE FROM embedding_v1 WHERE note_id = %s", (note_id,))

            # Insert new embeddings with proper vector format
            for section_id, embedding in enumerate(embeddings):
                # Convert to pgvector format
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                cursor.execute(
                    """
                    INSERT INTO embedding_v1 (note_id, section_id, embedding, last_updated)
                    VALUES (%s, %s, %s::vector, NOW())
                """,
                    (note_id, section_id, embedding_str),
                )

            conn.commit()
            logger.info(
                f"Saved {len(embeddings)} embeddings for note {note_id}")
    except Exception as e:
        logger.error(f"Error saving embeddings: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_embeddings(note_id: int) -> Optional[List[List[float]]]:
    """Get embeddings from embedding_v1 table"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT embedding::float[] 
                FROM embedding_v1 
                WHERE note_id = %s 
                ORDER BY section_id
            """,
                (note_id,),
            )

            results = cursor.fetchall()
            if results:
                return [list(row[0]) for row in results]
            return None

    except Exception as e:
        logger.error(f"Error getting embeddings: {e}")
        return None
    finally:
        if conn:
            conn.close()


def vector_similarity_search(query_embedding: List[float], note_ids: List[int], top_k: int = 5) -> List[Tuple[int, float]]:
    """
    Perform similarity search using pgvector's efficient operators
    Returns list of (note_id, max_similarity) tuples
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Convert query embedding to pgvector format
            query_embedding_str = '[' + \
                ','.join(map(str, query_embedding)) + ']'

            # Use pgvector's <=> operator for cosine distance (1 - cosine_similarity)
            query = """
                WITH note_similarities AS (
                    SELECT 
                        note_id,
                        section_id,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM embedding_v1
                    WHERE note_id = ANY(%s)
                ),
                max_similarities AS (
                    SELECT 
                        note_id,
                        MAX(similarity) as max_similarity
                    FROM note_similarities
                    GROUP BY note_id
                )
                SELECT note_id, max_similarity
                FROM max_similarities
                ORDER BY max_similarity DESC
                LIMIT %s
            """

            cursor.execute(query, (query_embedding_str, note_ids, top_k))
            results = cursor.fetchall()

            logger.info(f"Vector search found {len(results)} similar notes")
            return results

    except Exception as e:
        logger.error(f"Error in vector similarity search: {e}")
        return []
    finally:
        if conn:
            conn.close()


def vector_chunk_similarity_search(query_embedding: List[float], note_ids: List[int], top_k: int = 20) -> List[Tuple[int, int, float, str, str]]:
    """
    Perform chunk-level similarity search using pgvector
    Returns list of (note_id, section_id, similarity, chunk_text, source) tuples
    This gets the most relevant CHUNKS across all notes, not just the top notes
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Convert query embedding to pgvector format
            query_embedding_str = '[' + \
                ','.join(map(str, query_embedding)) + ']'

            # Get the top chunks directly with pre-stored chunk text
            query = """
                SELECT 
                    e.note_id,
                    e.section_id,
                    1 - (e.embedding <=> %s::vector) as similarity,
                    COALESCE(e.chunk_text, '') as chunk_text,
                    COALESCE(e.source, 'unknown') as source
                FROM embedding_v1 e
                WHERE e.note_id = ANY(%s)
                  AND e.chunk_text IS NOT NULL  -- Only get chunks with text
                ORDER BY similarity DESC
                LIMIT %s
            """

            cursor.execute(query, (query_embedding_str, note_ids, top_k))
            results = cursor.fetchall()

            logger.info(
                f"Vector chunk search found {len(results)} similar chunks with stored text")
            return results

    except Exception as e:
        logger.error(f"Error in vector chunk similarity search: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_notes_with_embeddings(note_ids: List[int]) -> List[int]:
    """Filter note IDs to only those that have embeddings in embedding_v1"""
    if not note_ids:
        return []

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT DISTINCT note_id 
                FROM embedding_v1 
                WHERE note_id = ANY(%s)
            """
            cursor.execute(query, (note_ids,))
            return [row[0] for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error filtering notes with embeddings: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_embeddings_batch(note_ids: List[int]) -> Dict[int, List[List[float]]]:
    """Retrieve embeddings for multiple notes in a single query"""
    if not note_ids:
        return {}

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT note_id, section_id, embedding::float[]
                FROM embedding_v1 
                WHERE note_id = ANY(%s)
                ORDER BY note_id, section_id
            """
            cursor.execute(query, (note_ids,))

            result = {}
            for note_id, section_id, embedding in cursor.fetchall():
                if note_id not in result:
                    result[note_id] = []
                result[note_id].append(list(embedding))

            return result

    except Exception as e:
        logger.error(f"Error fetching embeddings batch: {e}")
        return {}
    finally:
        if conn:
            conn.close()


# Web Search Cache Functions
def create_search_cache_table():
    """Create the search cache table if it doesn't exist"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    id SERIAL PRIMARY KEY,
                    query_hash VARCHAR(64) UNIQUE NOT NULL,
                    query_text TEXT NOT NULL,
                    results JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_search_cache_hash ON search_cache(query_hash);
                CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at);
            """
            )
            conn.commit()


def get_cached_search_results(query_hash: str) -> Optional[dict]:
    """Get cached search results if not expired"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT results, created_at, access_count
                FROM search_cache 
                WHERE query_hash = %s AND expires_at > NOW()
            """,
                (query_hash,),
            )

            result = cursor.fetchone()
            if result:
                # Update access count and last accessed time
                cursor.execute(
                    """
                    UPDATE search_cache 
                    SET access_count = access_count + 1, last_accessed = NOW()
                    WHERE query_hash = %s
                """,
                    (query_hash,),
                )
                conn.commit()

                return {
                    "results": result[0],
                    "created_at": result[1],
                    "access_count": result[2] + 1,
                    "cached": True,
                }
            return None


def save_search_cache(query_hash: str, query_text: str, results: list, ttl_hours: int = 24):
    """Save search results to cache with TTL"""
    expires_at = datetime.now() + timedelta(hours=ttl_hours)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO search_cache (query_hash, query_text, results, expires_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (query_hash) 
                DO UPDATE SET 
                    results = EXCLUDED.results,
                    expires_at = EXCLUDED.expires_at,
                    access_count = search_cache.access_count + 1,
                    last_accessed = NOW()
            """,
                (query_hash, query_text, json.dumps(results), expires_at),
            )
            conn.commit()


def cleanup_expired_search_cache():
    """Remove expired cache entries"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM search_cache WHERE expires_at < NOW()")
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count


def get_search_cache_stats():
    """Get cache statistics"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
                    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses_per_entry
                FROM search_cache
            """
            )

            result = cursor.fetchone()
            if result:
                return {
                    "total_entries": result[0],
                    "active_entries": result[1],
                    "expired_entries": result[2],
                    "total_accesses": result[3] or 0,
                    "avg_accesses_per_entry": float(result[4] or 0),
                }
            return {}


def get_notes_by_user_and_folders(user_id: int, folder_ids: List[int] = None) -> List[int]:
    """
    Get note IDs based on user ID and optional folder IDs.

    Args:
        user_id: The user ID (mandatory)
        folder_ids: Optional list of folder IDs to filter by

    Returns:
        List of note IDs
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if folder_ids:
                # Get notes from specific folders belonging to the user
                query = """
                    SELECT DISTINCT n.id 
                    FROM note_v1 n
                    INNER JOIN folder_v1 f ON n."folderId" = f.id
                    WHERE f."ownerId" = %s 
                    AND f.id = ANY(%s)
                    AND n.completed = true
                    ORDER BY n.id DESC
                """
                cursor.execute(query, (user_id, folder_ids))
            else:
                # Get all notes belonging to the user
                query = """
                    SELECT DISTINCT id 
                    FROM note_v1 
                    WHERE "ownerId" = %s 
                    AND completed = true
                    ORDER BY id DESC
                """
                cursor.execute(query, (user_id,))

            results = cursor.fetchall()
            return [row[0] for row in results]

    except Exception as e:
        logger.error(f"Error fetching notes for user {user_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def validate_user_exists(user_id: int) -> bool:
    """
    Check if a user exists in the database.

    Args:
        user_id: The user ID to validate

    Returns:
        True if user exists, False otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = 'SELECT EXISTS(SELECT 1 FROM user_v1 WHERE id = %s)'
            cursor.execute(query, (user_id,))
            return cursor.fetchone()[0]

    except Exception as e:
        logger.error(f"Error validating user {user_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def validate_folders_belong_to_user(user_id: int, folder_ids: List[int]) -> bool:
    """
    Validate that all folder IDs belong to the specified user.

    Args:
        user_id: The user ID
        folder_ids: List of folder IDs to validate

    Returns:
        True if all folders belong to the user, False otherwise
    """
    if not folder_ids:
        return True

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT COUNT(*) 
                FROM folder_v1 
                WHERE "ownerId" = %s 
                AND id = ANY(%s)
            """
            cursor.execute(query, (user_id, folder_ids))
            count = cursor.fetchone()[0]
            return count == len(folder_ids)

    except Exception as e:
        logger.error(f"Error validating folders for user {user_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_notes_for_rag(user_id: int, folder_ids: List[int] = None, note_ids: List[int] = None) -> List[int]:
    """
    Get note IDs for RAG search based on the following priority:
    1. If note_ids provided: return only those notes (after validation)
    2. If folder_ids provided: return notes from those folders only
    3. If neither provided: return all notes from user

    Args:
        user_id: The user ID (mandatory)
        folder_ids: Optional list of folder IDs
        note_ids: Optional list of specific note IDs

    Returns:
        List of note IDs
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Case 1: Specific note IDs provided
            if note_ids:
                # Validate that notes belong to the user
                query = """
                    SELECT id 
                    FROM note_v1 
                    WHERE "ownerId" = %s 
                    AND id = ANY(%s)
                    AND completed = true
                    ORDER BY id DESC
                """
                cursor.execute(query, (user_id, note_ids))
                results = cursor.fetchall()
                validated_notes = [row[0] for row in results]

                # Log if some notes were invalid
                if len(validated_notes) < len(note_ids):
                    invalid_notes = set(note_ids) - set(validated_notes)
                    logger.warning(
                        f"Some note IDs do not belong to user {user_id} or are incomplete: {invalid_notes}"
                    )

                return validated_notes

            # Case 2: Folder IDs provided (but no note IDs)
            elif folder_ids:
                # Get notes from specific folders belonging to the user
                query = """
                    SELECT DISTINCT n.id 
                    FROM note_v1 n
                    INNER JOIN folder_v1 f ON n."folderId" = f.id
                    WHERE f."ownerId" = %s 
                    AND f.id = ANY(%s)
                    AND n.completed = true
                    ORDER BY n.id DESC
                """
                cursor.execute(query, (user_id, folder_ids))
                results = cursor.fetchall()
                return [row[0] for row in results]

            # Case 3: No specific notes or folders - get all user notes
            else:
                query = """
                    SELECT id 
                    FROM note_v1 
                    WHERE "ownerId" = %s 
                    AND completed = true
                    ORDER BY id DESC
                """
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                return [row[0] for row in results]

    except Exception as e:
        logger.error(f"Error fetching notes for user {user_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def create_embedding_job_table():
    """Create table to track embedding generation jobs"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embedding_jobs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    total_notes INTEGER DEFAULT 0,
                    processed_notes INTEGER DEFAULT 0,
                    failed_notes INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_embedding_jobs_user_id 
                ON embedding_jobs(user_id);
                
                CREATE INDEX IF NOT EXISTS idx_embedding_jobs_status 
                ON embedding_jobs(status);
            """)
            conn.commit()
            logger.info("Embedding jobs table created successfully")
    except Exception as e:
        logger.error(f"Error creating embedding jobs table: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def get_notes_without_embeddings(note_ids: List[int]) -> List[int]:
    """
    Check which notes from the given list don't have embeddings
    Returns list of note IDs that need embeddings created
    """
    if not note_ids:
        return []

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Find note IDs that don't have any embeddings
            cursor.execute(
                """
                SELECT unnest(%s::int[]) as note_id
                EXCEPT
                SELECT DISTINCT note_id FROM embedding_v1 WHERE note_id = ANY(%s)
                """,
                (note_ids, note_ids)
            )

            results = cursor.fetchall()
            return [row[0] for row in results]

    except Exception as e:
        logger.error(f"Error checking notes without embeddings: {e}")
        return note_ids  # Return all note_ids as a fallback to be safe
    finally:
        if conn:
            conn.close()


def get_note_metadata(note_id: int) -> Dict[str, Any]:
    """Get note metadata including title-like information for citations"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get basic note info
            cursor.execute(
                """
                SELECT id, "createdAt", "updatedAt", "promptContent"
                FROM note_v1 
                WHERE id = %s
            """,
                (note_id,),
            )
            note_result = cursor.fetchone()

            if not note_result:
                return {"note_id": note_id, "title": f"Note {note_id}", "exists": False}

            # Get first part text for title extraction
            cursor.execute(
                """
                SELECT "text"
                FROM part_v1
                WHERE "noteId" = %s
                ORDER BY "order"
                LIMIT 1
            """,
                (note_id,),
            )
            first_part = cursor.fetchone()

            # Extract title from content
            title = f"Note {note_id}"
            if first_part and first_part['text']:
                first_text = first_part['text'].strip()
                # Take first line or first 50 characters as title
                lines = first_text.split('\n')
                if lines and len(lines[0].strip()) > 0:
                    title_candidate = lines[0].strip()
                    if len(title_candidate) <= 80:
                        title = f"Note {note_id}: {title_candidate}"
                    else:
                        title = f"Note {note_id}: {title_candidate[:50]}..."

            return {
                "note_id": note_id,
                "title": title,
                "created_at": note_result['createdAt'],
                "updated_at": note_result['updatedAt'],
                "exists": True
            }


def get_notes_metadata_batch(note_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get metadata for multiple notes in a single query"""
    if not note_ids:
        return {}

    result = {}
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get basic note info
            cursor.execute(
                """
                SELECT id, "createdAt", "updatedAt", "promptContent"
                FROM note_v1 
                WHERE id = ANY(%s)
            """,
                (note_ids,),
            )
            notes = cursor.fetchall()

            # Get first part text for each note
            cursor.execute(
                """
                SELECT DISTINCT ON ("noteId") "noteId", "text"
                FROM part_v1
                WHERE "noteId" = ANY(%s)
                ORDER BY "noteId", "order"
            """,
                (note_ids,),
            )
            parts = cursor.fetchall()

    # Create mapping of note_id to first part text
    parts_map = {part['noteId']: part['text'] for part in parts}

    # Build metadata for each note
    for note in notes:
        note_id = note['id']

        # Extract title from content
        title = f"Note {note_id}"
        if note_id in parts_map and parts_map[note_id]:
            first_text = parts_map[note_id].strip()
            lines = first_text.split('\n')
            if lines and len(lines[0].strip()) > 0:
                title_candidate = lines[0].strip()
                if len(title_candidate) <= 80:
                    title = f"Note {note_id}: {title_candidate}"
                else:
                    title = f"Note {note_id}: {title_candidate[:50]}..."

        result[note_id] = {
            "note_id": note_id,
            "title": title,
            "created_at": note['createdAt'],
            "updated_at": note['updatedAt'],
            "exists": True
        }

    # Add entries for missing notes
    for note_id in note_ids:
        if note_id not in result:
            result[note_id] = {
                "note_id": note_id,
                "title": f"Note {note_id}",
                "exists": False
            }

    return result


def get_note_content_separate(note_id: int) -> tuple[str, str, str]:
    """
    Get note content separated into AI content (summary) and user content
    Returns: (ai_content, user_content, note_type)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Get note basic info and check if it has a noteType field
            cursor.execute(
                """
                SELECT "promptContent", 
                       CASE 
                           WHEN EXISTS(SELECT 1 FROM information_schema.columns 
                                     WHERE table_name = 'note_v1' AND column_name = 'noteType') 
                           THEN "noteType" 
                           ELSE 'text'
                       END as note_type
                FROM note_v1 
                WHERE id = %s
            """,
                (note_id,),
            )
            result = cursor.fetchone()

            if not result:
                return "", "", "text"

            prompt_content, note_type = result

            # Extract AI content (summary) from prompt content
            ai_content = ""
            if prompt_content and isinstance(prompt_content, dict):
                if (
                    "currentPromptContent" in prompt_content
                    and prompt_content["currentPromptContent"]
                ):
                    ai_content = prompt_content["currentPromptContent"].get(
                        "content", ""
                    )

            # Get user content (parts + images)
            user_content_parts = []

            # Get prefix images (not associated with any part)
            cursor.execute(
                """
                SELECT "imageURL", "imageText", "latex"
                FROM image_v1
                WHERE "noteId" = %s AND "partId" IS NULL
                ORDER BY id
            """,
                (note_id,),
            )
            prefix_images = cursor.fetchall()

            # Add prefix images
            for img_url, img_text, is_latex in prefix_images:
                if img_text:
                    user_content_parts.append(img_text)

            # Get parts in order
            cursor.execute(
                """
                SELECT id, "text"
                FROM part_v1
                WHERE "noteId" = %s
                ORDER BY "order"
            """,
                (note_id,),
            )
            parts = cursor.fetchall()

            # Process each part and its images
            for part_id, part_text in parts:
                # Add part text
                if part_text:
                    user_content_parts.append(part_text)

                # Get images for this part
                cursor.execute(
                    """
                    SELECT "imageURL", "imageText", "latex"
                    FROM image_v1
                    WHERE "partId" = %s
                    ORDER BY id
                """,
                    (part_id,),
                )
                part_images = cursor.fetchall()

                # Add part's images
                for img_url, img_text, is_latex in part_images:
                    if img_text:
                        user_content_parts.append(img_text)

            user_content = "\n\n".join(user_content_parts)

            # Determine note type if not available in DB
            if not note_type or note_type == 'text':
                # Try to infer from content or use default
                if 'youtube' in user_content.lower() or 'video' in user_content.lower():
                    note_type = 'youtube'
                elif any(ext in user_content.lower() for ext in ['.pdf', 'document', 'doc']):
                    note_type = 'doc'
                else:
                    note_type = 'text'

    return ai_content.strip(), user_content.strip(), note_type


def keyword_search(query: str, user_id: int, limit: int = 20) -> List[tuple]:
    """
    Perform keyword search on chunk content using PostgreSQL's full-text search
    with tsvector and GIN index for fast BM25-style search.

    Args:
        query: Search query string
        user_id: User ID to filter results
        limit: Maximum number of results to return

    Returns:
        List of (note_id, chunk_text, source, rank) tuples ordered by relevance
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Use PostgreSQL's full-text search with ranking
            cursor.execute(
                """
                SELECT 
                    e.note_id,
                    e.chunk_text,
                    e.source,
                    ts_rank(e.chunk_tsv, to_tsquery('english', %s)) as rank
                FROM embedding_v1 e
                JOIN note_v1 n ON e.note_id = n.id
                WHERE n."ownerId" = %s
                    AND e.chunk_tsv @@ to_tsquery('english', %s)
                    AND e.chunk_text IS NOT NULL
                ORDER BY rank DESC
                LIMIT %s
            """,
                (query, user_id, query, limit),
            )

            results = cursor.fetchall()
            return results

    except Exception as e:
        logger.error(f"Error in keyword search: {e}")
        return []
    finally:
        if conn:
            conn.close()


def advanced_keyword_search(query: str, user_id: int, source_filter: str = None, limit: int = 20) -> List[tuple]:
    """
    Advanced keyword search with source filtering and better query processing.

    Args:
        query: Search query string
        user_id: User ID to filter results  
        source_filter: Optional source filter ('summary', 'youtube', 'doc', 'text', etc.)
        limit: Maximum number of results to return

    Returns:
        List of (note_id, chunk_text, source, rank, note_title) tuples ordered by relevance
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Process query for better full-text search
            # Replace spaces with & for AND operations and handle quotes
            processed_query = query.replace(' ', ' & ')

            # Build the SQL query dynamically based on source filter
            base_query = """
                SELECT 
                    e.note_id,
                    e.chunk_text,
                    e.source,
                    ts_rank_cd(e.chunk_tsv, to_tsquery('english', %s)) as rank,
                    n."noteTitle" as note_title
                FROM embedding_v1 e
                JOIN note_v1 n ON e.note_id = n.id
                WHERE n."ownerId" = %s
                    AND e.chunk_tsv @@ to_tsquery('english', %s)
                    AND e.chunk_text IS NOT NULL
            """

            params = [processed_query, user_id, processed_query]

            if source_filter:
                base_query += " AND e.source = %s"
                params.append(source_filter)

            base_query += " ORDER BY rank DESC LIMIT %s"
            params.append(limit)

            cursor.execute(base_query, params)
            results = cursor.fetchall()
            return results

    except Exception as e:
        logger.error(f"Error in advanced keyword search: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_note_title(note_id: int) -> str:
    """Get just the note title efficiently without loading full content"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Try to get title from noteTitle field first (if it exists)
            cursor.execute(
                """
                SELECT 
                    COALESCE("noteTitle", '') as note_title,
                    EXISTS(SELECT 1 FROM part_v1 WHERE "noteId" = %s LIMIT 1) as has_parts
                FROM note_v1 
                WHERE id = %s
            """,
                (note_id, note_id),
            )
            result = cursor.fetchone()
            
            if not result:
                return f"Note {note_id}"
            
            note_title, has_parts = result
            
            # If we have a proper title, use it
            if note_title and note_title.strip():
                return note_title.strip()
            
            # Otherwise, get first line of first part as title (minimal query)
            if has_parts:
                cursor.execute(
                    """
                    SELECT "text"
                    FROM part_v1
                    WHERE "noteId" = %s
                    ORDER BY "order"
                    LIMIT 1
                """,
                    (note_id,),
                )
                first_part = cursor.fetchone()
                
                if first_part and first_part[0]:
                    first_text = first_part[0].strip()
                    lines = first_text.split('\n')
                    if lines and len(lines[0].strip()) > 0:
                        title_candidate = lines[0].strip()[:80]  # Limit to 80 chars
                        return title_candidate
            
            return f"Note {note_id}"
            
    except Exception as e:
        logger.error(f"Error getting note title for note {note_id}: {e}")
        return f"Note {note_id}"
    finally:
        if conn:
            conn.close()


def get_note_titles_batch(note_ids: List[int]) -> Dict[int, str]:
    """Get titles for multiple notes efficiently"""
    if not note_ids:
        return {}
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get note titles
            cursor.execute(
                """
                SELECT id, COALESCE("noteTitle", '') as note_title
                FROM note_v1 
                WHERE id = ANY(%s)
            """,
                (note_ids,),
            )
            notes = cursor.fetchall()
            
            # Get first part text for notes without titles (single query)
            notes_needing_titles = [note_id for note_id, title in notes if not title.strip()]
            
            titles_map = {}
            
            # Store existing titles
            for note_id, title in notes:
                if title and title.strip():
                    titles_map[note_id] = title.strip()
                else:
                    titles_map[note_id] = f"Note {note_id}"  # Default
            
            # Get first part text for notes without proper titles
            if notes_needing_titles:
                cursor.execute(
                    """
                    SELECT DISTINCT ON ("noteId") "noteId", "text"
                    FROM part_v1
                    WHERE "noteId" = ANY(%s)
                    ORDER BY "noteId", "order"
                """,
                    (notes_needing_titles,),
                )
                parts = cursor.fetchall()
                
                # Update titles with first line of content
                for note_id, text in parts:
                    if text and text.strip():
                        first_line = text.strip().split('\n')[0].strip()[:80]
                        if first_line:
                            titles_map[note_id] = first_line
            
            return titles_map
            
    except Exception as e:
        logger.error(f"Error getting note titles batch: {e}")
        return {note_id: f"Note {note_id}" for note_id in note_ids}
    finally:
        if conn:
            conn.close()


# Example usage
if __name__ == "__main__":
    # save_note(1, "Trip to Japan: Tokyo and Kyoto. Visit shrines and temples.")
    # note_text = get_note_text(5)
    # print(f"Note 1: {note_text}")
    print(get_part_text(8))
    # print(f"Note 1: {note_text}")
    print(get_part_text(8))
