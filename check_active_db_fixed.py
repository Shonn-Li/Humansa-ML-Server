#!/usr/bin/env python3
"""
Check production database (active) for user_id=1
Using correct column name: deletedAt
"""
import psycopg2

# Production database config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "031203",
    "dbname": "active",
}

print("=" * 60)
print("Checking Production Database: active")
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
        SELECT COUNT(*) FROM note_v1 WHERE "ownerId" = 1 AND "deletedAt" IS NULL
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
        WHERE n."ownerId" = 1 AND n."deletedAt" IS NULL
    """)
    active_embedded = cursor.fetchone()[0]
    print(f"Active notes with embeddings: {active_embedded}")
    
    # Get some sample notes
    print("\nSample notes for user_id=1:")
    cursor.execute("""
        SELECT n.id, n."noteTitle", n."createdAt", n."deletedAt",
               EXISTS(SELECT 1 FROM embedding_v1 e WHERE e.type = 'note' AND e.type_id = n.id) as has_embedding
        FROM note_v1 n
        WHERE n."ownerId" = 1
        ORDER BY n."createdAt" DESC
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
        print("  No notes found for user_id=1")
    
    # Check column names to confirm the issue
    print("\nChecking column names in note_v1 table:")
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'note_v1' 
        AND column_name LIKE '%delete%' OR column_name LIKE '%create%'
        ORDER BY column_name
    """)
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[0]}")
    
    # Check other users
    print("\nChecking other users for comparison:")
    cursor.execute("""
        SELECT "ownerId", COUNT(*) as note_count
        FROM note_v1
        WHERE "deletedAt" IS NULL
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
    print("=" * 60)
    if total == 0:
        print("❌ User 1 has NO notes at all in the production database")
        print("   This user has never created any notes")
        print("   RAG search returns 0 because there's nothing to search")
    elif active == 0:
        print("❌ User 1 has notes but they are ALL deleted")
        print(f"   Total notes: {total}, Active: 0")
    elif active_embedded == 0:
        print("❌ User 1 has active notes but NO embeddings")
        print(f"   Active notes: {active}, With embeddings: 0")
        print("   Notes must be embedded for RAG to work")
    else:
        print(f"✅ User 1 has {active} active notes with {active_embedded} embedded")
        print("   The issue might be in the search logic")
    
    print("\n🔴 CRITICAL FINDING:")
    print("   Production DB uses 'deletedAt' (camelCase)")
    print("   Test DB uses 'deletedat' (lowercase)")
    print("   The code was updated for lowercase but needs to handle both!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()