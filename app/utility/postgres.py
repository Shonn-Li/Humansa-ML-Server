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


def save_embedding(note_id: int, embedding: List[float]) -> None:
    """
    Upsert a note's embedding into embedding_v1, updating last_updated.
    """
    conn = get_db_connection()
    register_vector(conn)
    try:
        with conn:
            with conn.cursor() as cur:
                # (Re)create table if you like—optional after first run
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS embedding_v1 (
                      note_id      INT PRIMARY KEY,
                      embedding    VECTOR,
                      last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """
                )
                # Upsert the embedding
                cur.execute(
                    """
                    INSERT INTO embedding_v1 (note_id, embedding, last_updated)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (note_id)
                      DO UPDATE SET 
                        embedding = EXCLUDED.embedding,
                        last_updated = NOW();
                    """,
                    (note_id, embedding),
                )
    finally:
        conn.close()


def get_embedding(note_id: int) -> Optional[List[float]]:
    """
    Retrieve the stored embedding for a note_id, or None if missing.
    """
    conn = get_db_connection()
    register_vector(conn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT embedding FROM embedding_v1 WHERE note_id = %s",
                (note_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


# Example usage
if __name__ == "__main__":
    # save_note(1, "Trip to Japan: Tokyo and Kyoto. Visit shrines and temples.")
    # note_text = get_note_text(5)
    # print(f"Note 1: {note_text}")
    print(get_part_text(8))
