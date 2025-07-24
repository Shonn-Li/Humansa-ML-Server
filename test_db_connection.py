#!/usr/bin/env python3
"""
Test database connection
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connection parameters
db_params = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5454'),
    'database': os.getenv('DB_ACTIVE_DATABASE', 'youwoai_test'),
    'user': os.getenv('DB_USERNAME', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '031203')
}

print("Testing database connection...")
print(f"Connection parameters: {db_params}")

try:
    # Connect to the database
    conn = psycopg2.connect(**db_params)
    print("✅ Connected successfully!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM note_v1 WHERE \"ownerId\" = 10001")
    count = cursor.fetchone()[0]
    print(f"✅ Found {count} notes for test user 10001")
    
    # Check embeddings
    cursor.execute("SELECT COUNT(*) FROM embedding_v1 WHERE source LIKE 'note:%' AND type_id IN (SELECT id FROM note_v1 WHERE \"ownerId\" = 10001)")
    embedding_count = cursor.fetchone()[0]
    print(f"✅ Found {embedding_count} note embeddings for test user 10001")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    import traceback
    traceback.print_exc()