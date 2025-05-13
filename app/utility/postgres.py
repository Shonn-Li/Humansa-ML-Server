import os

import psycopg2
from dotenv import load_dotenv

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
    return psycopg2.connect(**DB_CONFIG)


def get_note(note_id: int) -> str:
    """Fetch a note from the database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT content FROM notes WHERE note_id = %s", (note_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"Note with ID {note_id} not found.")


def save_note(note_id: int, content: str) -> None:
    """Insert or update a note in the database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notes (note_id, content)
                VALUES (%s, %s)
                ON CONFLICT (note_id)
                DO UPDATE SET content = EXCLUDED.content;
            """,
                (note_id, content),
            )
            conn.commit()


# Example usage
if __name__ == "__main__":
    save_note(1, "Trip to Japan: Tokyo and Kyoto. Visit shrines and temples.")
    note_text = get_note(1)
    print(f"Note 1: {note_text}")
