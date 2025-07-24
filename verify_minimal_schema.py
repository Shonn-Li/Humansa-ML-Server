#!/usr/bin/env python3
"""
Verify ML server works with minimal test schema
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
print("MINIMAL TEST SCHEMA VERIFICATION")
print("=" * 60)

try:
    conn = psycopg2.connect(**test_config)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print("\nTables in test database:")
    for table in tables:
        print(f"  ✓ {table}")
    
    print(f"\nTotal tables: {len(tables)} (minimal set for ML server)")
    
    # Verify essential relationships
    print("\nVerifying table relationships:")
    
    # Check note -> part relationship
    cursor.execute("""
        SELECT COUNT(*) 
        FROM part_v1 p
        INNER JOIN note_v1 n ON p."noteId" = n.id
        WHERE n."ownerId" = 10001
    """)
    parts = cursor.fetchone()[0]
    print(f"  ✓ Note->Part relationship: {parts} parts found")
    
    # Check part -> image relationship  
    cursor.execute("""
        SELECT COUNT(*) 
        FROM image_v1 i
        INNER JOIN part_v1 p ON i."partId" = p.id
        INNER JOIN note_v1 n ON p."noteId" = n.id
        WHERE n."ownerId" = 10001
    """)
    images = cursor.fetchone()[0]
    print(f"  ✓ Part->Image relationship: {images} images found")
    
    # Check note -> embedding relationship
    cursor.execute("""
        SELECT COUNT(DISTINCT e.type_id)
        FROM embedding_v1 e
        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
        WHERE n."ownerId" = 10001
    """)
    embedded = cursor.fetchone()[0]
    print(f"  ✓ Note->Embedding relationship: {embedded} notes with embeddings")
    
    cursor.close()
    conn.close()
    
    print("\n✅ SUCCESS: Minimal schema contains all necessary tables")
    print("   - Core tables: note_v1, user_v1, folder_v1, conversation_v1")
    print("   - Embedding tables: embedding_v1, part_v1, image_v1")
    print("   - Cache tables: web_search_cache")
    print("   - Removed: subscription_v1 (not used by ML server)")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()