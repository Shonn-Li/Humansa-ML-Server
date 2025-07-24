#!/usr/bin/env python3
"""
Check production database directly for user_id=1
"""
import psycopg2
import os

# Production database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USERNAME", "postgres"),
    "password": os.getenv("DB_PASSWORD", "031203"),
    "dbname": os.getenv("DB_ACTIVE_DATABASE", "youwoai_active"),
}

print("=" * 60)
print("Checking Production Database")
print("=" * 60)
print(f"Database: {DB_CONFIG['dbname']}")
print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
print("=" * 60)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check notes for user_id=1
    print("\n1. Checking notes for user_id=1:")
    
    # Total notes
    cursor.execute("""
        SELECT COUNT(*) 
        FROM note_v1 
        WHERE "ownerId" = %s
    """, (1,))
    total = cursor.fetchone()[0]
    print(f"   Total notes: {total}")
    
    # Active notes (not deleted)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM note_v1 
        WHERE "ownerId" = %s AND deletedat IS NULL
    """, (1,))
    active = cursor.fetchone()[0]
    print(f"   Active notes: {active}")
    
    # Get sample notes
    cursor.execute("""
        SELECT id, "noteTitle", createdate, deletedat
        FROM note_v1 
        WHERE "ownerId" = %s
        ORDER BY createdate DESC
        LIMIT 5
    """, (1,))
    notes = cursor.fetchall()
    
    if notes:
        print(f"\n   Sample notes:")
        for note in notes:
            deleted = " (DELETED)" if note[3] else ""
            print(f"   - Note #{note[0]}: {note[1] or 'Untitled'} - Created: {note[2]}{deleted}")
    
    # Check embeddings
    print("\n2. Checking embeddings for user_id=1:")
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = %s
    """, (1,))
    embedded_total = cursor.fetchone()[0]
    print(f"   Total notes with embeddings: {embedded_total}")
    
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = %s AND n.deletedat IS NULL
    """, (1,))
    embedded_active = cursor.fetchone()[0]
    print(f"   Active notes with embeddings: {embedded_active}")
    
    # Check if there are any embeddings at all
    cursor.execute("""
        SELECT e.type_id, n."noteTitle", COUNT(e.id) as chunk_count
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = %s
        GROUP BY e.type_id, n."noteTitle"
        LIMIT 5
    """, (1,))
    embedded_notes = cursor.fetchall()
    
    if embedded_notes:
        print(f"\n   Sample embedded notes:")
        for note in embedded_notes:
            print(f"   - Note #{note[0]}: {note[1] or 'Untitled'} ({note[2]} chunks)")
    else:
        print(f"\n   ⚠️  No embeddings found for user_id=1")
    
    # Check a different user for comparison
    print("\n3. Checking a different user for comparison (user_id=2):")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM note_v1 
        WHERE "ownerId" = %s AND deletedat IS NULL
    """, (2,))
    user2_notes = cursor.fetchone()[0]
    print(f"   User 2 active notes: {user2_notes}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    if active == 0:
        print("❌ User 1 has NO active notes in the production database")
        print("   This explains why context search returns 0 results")
    elif embedded_active == 0:
        print("❌ User 1 has active notes but NO embeddings")
        print("   Notes need to be embedded for RAG search to work")
    else:
        print("✅ User 1 has active notes with embeddings")
        print("   The issue might be in the search logic")
        
except Exception as e:
    print(f"❌ Database error: {e}")
    import traceback
    traceback.print_exc()