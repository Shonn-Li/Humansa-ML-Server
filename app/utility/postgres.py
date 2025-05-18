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
    # print(DB_CONFIG)
    return psycopg2.connect(**DB_CONFIG)


def get_note_text(note_id: int) -> str:
    """Fetch the text representation of a note from Postgres database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql_command = f"""SELECT "noteTitle", "promptContent", "conversationId", "quizContent", "flashcardContent", "aiNoteContent", "noteContent"
FROM note_v1 WHERE id = {note_id}"""
            cursor.execute(sql_command)
            result = cursor.fetchone()
            (
                noteTitle,
                promptContent,
                conversationId,
                quizContent,
                flashcardContent,
                aiNoteContent,
                noteContent,
            ) = result
            print(type(result))
            for i in result:
                print(f"{type(i)}: {i}")
            return result


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


# def save_note(note_id: int, content: str) -> None:
#     """Insert or update a note in the database"""
#     with get_db_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(
#                 """
#                 INSERT INTO notes (note_id, content)
#                 VALUES (%s, %s)
#                 ON CONFLICT (note_id)
#                 DO UPDATE SET content = EXCLUDED.content;
#             """,
#                 (note_id, content),
#             )
#             conn.commit()


# Example usage
if __name__ == "__main__":
    # save_note(1, "Trip to Japan: Tokyo and Kyoto. Visit shrines and temples.")
    # note_text = get_note_text(5)
    # print(f"Note 1: {note_text}")
    print(get_part_text(8))
