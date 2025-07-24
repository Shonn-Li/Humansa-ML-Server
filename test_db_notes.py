#!/usr/bin/env python3
"""
Test database note retrieval
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for test database
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

from chat.postgres.db_manager import PostgresManager


def test_db_notes():
    """Check what notes are in the database"""
    
    postgres = PostgresManager()
    
    # Check notes for user 10001
    user_id = 10001
    
    with postgres.get_connection() as conn:
        with conn.cursor() as cursor:
            # Get all notes for user
            cursor.execute("""
                SELECT id, "noteTitle", createdate, deletedat, completed
                FROM note_v1 
                WHERE "ownerId" = %s
                ORDER BY id
            """, (user_id,))
            
            results = cursor.fetchall()
            
            print(f"\nTotal notes for user {user_id}: {len(results)}")
            print("\nNotes:")
            for row in results:
                note_id, title, created, deleted, completed = row
                print(f"  ID: {note_id}")
                print(f"    Title: {title}")
                print(f"    Created: {created}")
                print(f"    Deleted: {deleted}")
                print(f"    Completed: {completed}")
                print()
            
            # Check embeddings
            cursor.execute("""
                SELECT COUNT(*) 
                FROM embedding_v1 
                WHERE type = 'note' 
                AND type_id IN (
                    SELECT id FROM note_v1 WHERE "ownerId" = %s
                )
            """, (user_id,))
            
            count = cursor.fetchone()[0]
            print(f"Total embeddings for user's notes: {count}")


if __name__ == "__main__":
    test_db_notes()