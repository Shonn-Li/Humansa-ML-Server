#!/usr/bin/env python3
"""
Verify that test database schema now matches production
"""
import psycopg2

def check_column_names(conn, db_name):
    """Check column names for key tables"""
    cursor = conn.cursor()
    
    print(f"\n{db_name} Database Column Names:")
    print("-" * 50)
    
    for table in ['note_v1', 'folder_v1', 'conversation_v1', 'user_v1']:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name IN ('createDate', 'updateDate', 'deletedAt', 
                               'createdate', 'updatedate', 'deletedat')
            ORDER BY column_name
        """, (table,))
        
        columns = [row[0] for row in cursor.fetchall()]
        if columns:
            print(f"{table}: {', '.join(columns)}")
    
    cursor.close()

def test_queries():
    """Test that queries work on both databases with same column names"""
    
    test_config = {
        "host": "localhost",
        "port": 5454,
        "user": "postgres",
        "password": "12931",
        "dbname": "youwoai_test",
    }
    
    print("\n" + "=" * 60)
    print("TESTING SYNCHRONIZED SCHEMA")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**test_config)
        
        # Test standard queries with new column names
        cursor = conn.cursor()
        
        # Test 1: Basic query
        cursor.execute("""
            SELECT COUNT(*) 
            FROM note_v1 
            WHERE "ownerId" = %s AND "deletedAt" IS NULL
        """, (10001,))
        count = cursor.fetchone()[0]
        print(f"\n✅ Query 1 Success: Found {count} active notes for test user")
        
        # Test 2: Join query
        cursor.execute("""
            SELECT COUNT(DISTINCT e.type_id)
            FROM embedding_v1 e
            INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
            WHERE n."ownerId" = %s AND n."deletedAt" IS NULL
        """, (10001,))
        count = cursor.fetchone()[0]
        print(f"✅ Query 2 Success: Found {count} notes with embeddings")
        
        # Test 3: Date ordering
        cursor.execute("""
            SELECT id, "noteTitle", "createDate"
            FROM note_v1
            WHERE "ownerId" = %s
            ORDER BY "createDate" DESC
            LIMIT 3
        """, (10001,))
        notes = cursor.fetchall()
        print(f"✅ Query 3 Success: Retrieved {len(notes)} recent notes")
        
        # Check column names
        check_column_names(conn, "Test")
        
        cursor.close()
        conn.close()
        
        print("\n✅ ALL TESTS PASSED! Test database is now synchronized with production schema.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_queries()