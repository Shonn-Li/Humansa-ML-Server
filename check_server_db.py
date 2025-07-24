#!/usr/bin/env python3
"""
Check what database the server is actually using
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import after path is set
from chat.postgres.db_manager import DB_CONFIG

print("=" * 60)
print("Server Database Configuration")
print("=" * 60)
print(f"Host: {DB_CONFIG.get('host')}")
print(f"Port: {DB_CONFIG.get('port')}")
print(f"Database: {DB_CONFIG.get('dbname')}")
print(f"User: {DB_CONFIG.get('user')}")
print("=" * 60)

# Now check the database
import psycopg2

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check for user_id=1
    print("\nChecking user_id=1 in production database:")
    
    cursor.execute("""
        SELECT COUNT(*) FROM note_v1 WHERE "ownerId" = 1
    """)
    total = cursor.fetchone()[0]
    print(f"Total notes: {total}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM note_v1 WHERE "ownerId" = 1 AND deletedat IS NULL
    """)
    active = cursor.fetchone()[0]
    print(f"Active notes: {active}")
    
    # Check embeddings
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = 1 AND n.deletedat IS NULL
    """)
    embedded = cursor.fetchone()[0]
    print(f"Notes with embeddings: {embedded}")
    
    # Get sample notes if any
    if active > 0:
        cursor.execute("""
            SELECT id, "noteTitle", createdate
            FROM note_v1 
            WHERE "ownerId" = 1 AND deletedat IS NULL
            ORDER BY createdate DESC
            LIMIT 3
        """)
        notes = cursor.fetchall()
        print("\nSample active notes:")
        for note in notes:
            print(f"  - Note #{note[0]}: {note[1] or 'Untitled'} (created: {note[2]})")
            
            # Check if this note has embeddings
            cursor.execute("""
                SELECT COUNT(*) FROM embedding_v1 
                WHERE type = 'note' AND type_id = %s
            """, (note[0],))
            chunks = cursor.fetchone()[0]
            print(f"    Embeddings: {chunks} chunks")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()