#!/usr/bin/env python3
"""
Check if embeddings exist in test database
"""
import psycopg2

test_config = {
    "host": "localhost",
    "port": 5454,
    "user": "postgres",
    "password": "12931",
    "dbname": "youwoai_test",
}

print("=" * 60)
print("CHECKING EMBEDDINGS IN TEST DATABASE")
print("=" * 60)

try:
    conn = psycopg2.connect(**test_config)
    cursor = conn.cursor()
    
    # Check total embeddings
    cursor.execute("SELECT COUNT(*) FROM embedding_v1")
    total = cursor.fetchone()[0]
    print(f"\nTotal embeddings: {total}")
    
    # Check embeddings by type
    cursor.execute("""
        SELECT type, COUNT(*) 
        FROM embedding_v1 
        GROUP BY type
    """)
    types = cursor.fetchall()
    print("\nEmbeddings by type:")
    for t in types:
        print(f"  - {t[0]}: {t[1]}")
    
    # Check note embeddings for test user
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = 10001 AND n."deletedAt" IS NULL
    """)
    user_notes = cursor.fetchone()[0]
    print(f"\nTest user (10001) notes with embeddings: {user_notes}")
    
    # Sample some embeddings
    cursor.execute("""
        SELECT e.type, e.type_id, n."noteTitle", LENGTH(e.chunk_text) as text_len
        FROM embedding_v1 e
        LEFT JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE e.type = 'note'
        LIMIT 5
    """)
    samples = cursor.fetchall()
    print("\nSample embeddings:")
    for s in samples:
        print(f"  - {s[0]} #{s[1]}: {s[2] or 'Untitled'} ({s[3]} chars)")
    
    # Check if there's an issue with the join
    cursor.execute("""
        SELECT n.id, n."noteTitle", 
               EXISTS(SELECT 1 FROM embedding_v1 e WHERE e.type = 'note' AND e.type_id = n.id) as has_embedding
        FROM note_v1 n
        WHERE n."ownerId" = 10001 AND n."deletedAt" IS NULL
        ORDER BY n."createDate" DESC
    """)
    notes = cursor.fetchall()
    print(f"\nNotes for test user 10001:")
    for note in notes:
        status = "✓" if note[2] else "✗"
        print(f"  - Note #{note[0]}: {note[1] or 'Untitled'} - Embeddings: {status}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()