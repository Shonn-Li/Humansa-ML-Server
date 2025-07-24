#!/usr/bin/env python3
"""
Check production database for user_id=1
"""
import psycopg2

# Production database config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "031203",
    "dbname": "youwoai",
}

print("=" * 60)
print("Checking Production Database: youwoai")
print("=" * 60)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check user_id=1
    print("\nUser ID 1 Analysis:")
    print("-" * 30)
    
    cursor.execute("""
        SELECT COUNT(*) FROM note_v1 WHERE "ownerId" = 1
    """)
    total = cursor.fetchone()[0]
    print(f"Total notes: {total}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM note_v1 WHERE "ownerId" = 1 AND deletedat IS NULL
    """)
    active = cursor.fetchone()[0]
    print(f"Active notes (not deleted): {active}")
    
    # Check embeddings
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = 1
    """)
    total_embedded = cursor.fetchone()[0]
    print(f"Total notes with embeddings: {total_embedded}")
    
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = 1 AND n.deletedat IS NULL
    """)
    active_embedded = cursor.fetchone()[0]
    print(f"Active notes with embeddings: {active_embedded}")
    
    # Get some sample notes
    print("\nSample notes for user_id=1:")
    cursor.execute("""
        SELECT n.id, n."noteTitle", n.createdate, n.deletedat,
               EXISTS(SELECT 1 FROM embedding_v1 e WHERE e.type = 'note' AND e.type_id = n.id) as has_embedding
        FROM note_v1 n
        WHERE n."ownerId" = 1
        ORDER BY n.createdate DESC
        LIMIT 5
    """)
    notes = cursor.fetchall()
    
    if notes:
        for note in notes:
            status = "DELETED" if note[3] else "ACTIVE"
            embedding = "✓" if note[4] else "✗"
            print(f"  - Note #{note[0]}: {note[1] or 'Untitled'}")
            print(f"    Status: {status}, Embeddings: {embedding}, Created: {note[2]}")
    else:
        print("  No notes found")
    
    # Check other users for comparison
    print("\nChecking other users for comparison:")
    cursor.execute("""
        SELECT "ownerId", COUNT(*) as note_count
        FROM note_v1
        WHERE deletedat IS NULL
        GROUP BY "ownerId"
        ORDER BY note_count DESC
        LIMIT 5
    """)
    users = cursor.fetchall()
    for user in users:
        print(f"  User {user[0]}: {user[1]} active notes")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    if active == 0:
        print("❌ User 1 has NO active notes in production")
        print("   This is why RAG search returns 0 results")
    elif active_embedded == 0:
        print("❌ User 1 has notes but NO embeddings")
        print("   Notes must be embedded for RAG to work")
    else:
        print(f"✅ User 1 has {active} active notes with {active_embedded} embedded")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()