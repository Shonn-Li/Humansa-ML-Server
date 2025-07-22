#!/usr/bin/env python3
"""
Verify test environment setup
Connects to test database and checks all components
"""

import psycopg2
import sys

# Test database configuration
TEST_DB = {
    'host': 'localhost',
    'port': 5454,  # Test port
    'database': 'youwoai_test',
    'user': 'postgres',
    'password': '12931'
}

def connect_to_test_db():
    """Connect to test database"""
    try:
        conn = psycopg2.connect(**TEST_DB)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to test database: {e}")
        print(f"   Make sure the test database is running on port {TEST_DB['port']}")
        return None

def verify_extensions(conn):
    """Verify required extensions are installed"""
    cur = conn.cursor()
    cur.execute("""
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname IN ('vector', 'pg_trgm')
        ORDER BY extname
    """)
    
    extensions = cur.fetchall()
    print("\n📦 Extensions:")
    for ext in extensions:
        print(f"  ✅ {ext[0]} v{ext[1]}")
    
    return len(extensions) == 2

def verify_tables(conn):
    """Verify all required tables exist"""
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name IN (
            'user_v1', 'folder_v1', 'note_v1', 'part_v1', 
            'image_v1', 'conversation_v1', 'embedding_v1'
        )
        ORDER BY table_name
    """)
    
    tables = [row[0] for row in cur.fetchall()]
    print("\n📊 Tables:")
    for table in tables:
        print(f"  ✅ {table}")
    
    return len(tables) == 7

def verify_test_data(conn):
    """Verify test data is loaded"""
    cur = conn.cursor()
    
    # Check counts
    checks = [
        ("Test users", "SELECT COUNT(*) FROM user_v1 WHERE id >= 10001"),
        ("Test folders", "SELECT COUNT(*) FROM folder_v1 WHERE id >= 10001"),
        ("Test notes", "SELECT COUNT(*) FROM note_v1 WHERE id >= 10001"),
        ("Test parts", "SELECT COUNT(*) FROM part_v1 WHERE \"noteId\" >= 10001"),
        ("Test embeddings", "SELECT COUNT(*) FROM embedding_v1 WHERE type_id >= 10001")
    ]
    
    print("\n📝 Test Data:")
    all_good = True
    for name, query in checks:
        cur.execute(query)
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  ✅ {name}: {count}")
        else:
            print(f"  ❌ {name}: {count}")
            all_good = False
    
    return all_good

def verify_embeddings(conn):
    """Verify embeddings are properly loaded"""
    cur = conn.cursor()
    
    # Check embedding dimensions
    cur.execute("""
        SELECT 
            type_id,
            COUNT(*) as embedding_count,
            vector_dims(embedding) as dimensions
        FROM embedding_v1
        WHERE type_id >= 10001
        GROUP BY type_id, vector_dims(embedding)
        ORDER BY type_id
        LIMIT 5
    """)
    
    print("\n🔍 Embedding Verification:")
    results = cur.fetchall()
    if results:
        for row in results:
            print(f"  Note {row[0]}: {row[1]} embeddings, {row[2]} dimensions")
        
        # Test similarity search
        cur.execute("""
            SELECT COUNT(*) 
            FROM embedding_v1 e1, embedding_v1 e2
            WHERE e1.type_id = 10001 
            AND e2.type_id = 10002
            AND e1.embedding <-> e2.embedding < 1.0
            LIMIT 1
        """)
        
        if cur.fetchone()[0] > 0:
            print("  ✅ Vector similarity search working")
            return True
    
    return False

def main():
    print("🔍 YouWoAI Test Environment Verification")
    print("=====================================")
    
    # Connect to test database
    conn = connect_to_test_db()
    if not conn:
        sys.exit(1)
    
    try:
        # Run verifications
        ext_ok = verify_extensions(conn)
        tables_ok = verify_tables(conn)
        data_ok = verify_test_data(conn)
        embeddings_ok = verify_embeddings(conn)
        
        # Summary
        print("\n📊 Summary:")
        all_ok = ext_ok and tables_ok and data_ok and embeddings_ok
        
        if all_ok:
            print("✅ All checks passed! Test environment is ready.")
            sys.exit(0)
        else:
            print("❌ Some checks failed. Please review the output above.")
            sys.exit(1)
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()