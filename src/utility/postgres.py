import os
from typing import List, Optional

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

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


def save_embeddings(note_id: int, embeddings: List[List[float]]) -> None:
    """
    Upsert a note's embeddings (one per section) into embedding_v1.
    """
    conn = get_db_connection()
    register_vector(conn)
    try:
        with conn:
            with conn.cursor() as cur:
                for sec_id, vec in enumerate(embeddings):
                    cur.execute(
                        """
                        INSERT INTO embedding_v1 (note_id, section_id, embedding, last_updated)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (note_id, section_id)
                          DO UPDATE SET
                            embedding    = EXCLUDED.embedding,
                            last_updated = NOW();
                        """,
                        (note_id, sec_id, vec),
                    )
    finally:
        conn.close()


def get_embeddings(note_id: int) -> Optional[List[List[float]]]:
    """
    Returns list of section embeddings for a note, or None if none stored.
    """
    conn = get_db_connection()
    register_vector(conn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT section_id, embedding FROM embedding_v1 WHERE note_id = %s ORDER BY section_id",
                (note_id,),
            )
            rows = cur.fetchall()
            if not rows:
                return None
            return [row[1] for row in rows]
    finally:
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
    import json
    from datetime import datetime, timedelta

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


# Example usage
if __name__ == "__main__":
    # save_note(1, "Trip to Japan: Tokyo and Kyoto. Visit shrines and temples.")
    # note_text = get_note_text(5)
    # print(f"Note 1: {note_text}")
    print(get_part_text(8))
