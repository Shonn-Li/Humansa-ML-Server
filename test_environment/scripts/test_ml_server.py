#!/usr/bin/env python3
"""
Test ML server configuration with port 5454
Validates that the ML server can connect to the test database
"""

import os
import sys
import requests
import psycopg2
from datetime import datetime

# Test database configuration
TEST_DB = {
    'host': 'localhost',
    'port': 5454,  # Test port
    'database': 'youwoai_test',
    'user': 'postgres',
    'password': '12931'
}

# ML Server endpoint (assuming it runs on port 5001)
ML_SERVER_URL = "http://localhost:5001"

def test_database_connection():
    """Test direct database connection"""
    print("\n🔍 Testing database connection on port 5454...")
    try:
        conn = psycopg2.connect(**TEST_DB)
        cur = conn.cursor()
        
        # Test basic query
        cur.execute("SELECT COUNT(*) FROM note_v1 WHERE id >= 10001")
        note_count = cur.fetchone()[0]
        print(f"  ✅ Connected to test database")
        print(f"  ✅ Found {note_count} test notes")
        
        # Test embedding table
        cur.execute("SELECT COUNT(*) FROM embedding_v1 WHERE type_id >= 10001")
        embedding_count = cur.fetchone()[0]
        print(f"  ✅ Found {embedding_count} test embeddings")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def test_ml_server_health():
    """Test ML server health endpoint"""
    print("\n🔍 Testing ML server health...")
    try:
        response = requests.get(f"{ML_SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ ML server is healthy")
            return True
        else:
            print(f"  ❌ ML server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ❌ ML server is not running on {ML_SERVER_URL}")
        print("     Start it with: python src/main.py")
        return False
    except Exception as e:
        print(f"  ❌ ML server test failed: {e}")
        return False

def create_test_env_file():
    """Create a test .env file for ML server"""
    print("\n📝 Creating test environment configuration...")
    
    test_env_content = f"""# Test Database Configuration
DB_HOST=localhost
DB_PORT=5454
DB_USERNAME=postgres
DB_PASSWORD=12931
DB_ACTIVE_DATABASE=youwoai_test

# Copy other settings from production .env
# Add your API keys and other configurations here
"""
    
    env_path = "/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/.env.test"
    
    # Check if production .env exists
    prod_env_path = "/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/.env"
    if os.path.exists(prod_env_path):
        print(f"  ℹ️  Found production .env at {prod_env_path}")
        print(f"  ℹ️  You should copy API keys from production to test")
    
    with open(env_path, 'w') as f:
        f.write(test_env_content)
    
    print(f"  ✅ Created {env_path}")
    print(f"     To use: cp .env .env.prod && cp .env.test .env")
    
    return True

def test_vector_search():
    """Test vector similarity search capability"""
    print("\n🔍 Testing vector search capability...")
    try:
        conn = psycopg2.connect(**TEST_DB)
        cur = conn.cursor()
        
        # Get a sample embedding
        cur.execute("""
            SELECT embedding 
            FROM embedding_v1 
            WHERE type_id >= 10001 
            LIMIT 1
        """)
        
        result = cur.fetchone()
        if result:
            # Test similarity search
            cur.execute("""
                SELECT COUNT(*) 
                FROM embedding_v1 
                WHERE type_id >= 10001
                AND embedding <-> %s < 1.0
            """, (result[0],))
            
            similar_count = cur.fetchone()[0]
            print(f"  ✅ Vector similarity search working")
            print(f"  ✅ Found {similar_count} similar embeddings")
            conn.close()
            return True
        else:
            print(f"  ❌ No embeddings found to test")
            conn.close()
            return False
            
    except Exception as e:
        print(f"  ❌ Vector search test failed: {e}")
        return False

def main():
    print("🚀 ML Server Test Environment Validation")
    print("=" * 40)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Run tests
    db_ok = test_database_connection()
    vector_ok = test_vector_search() if db_ok else False
    ml_ok = test_ml_server_health()
    env_ok = create_test_env_file()
    
    # Summary
    print("\n📊 Summary:")
    all_ok = db_ok and vector_ok and env_ok
    
    if all_ok:
        print("✅ Test environment is ready for ML server!")
        print("\n📋 Next steps:")
        print("1. Copy test environment: cp .env .env.prod && cp .env.test .env")
        print("2. Start ML server: python src/main.py")
        print("3. The ML server will use test database on port 5454")
        
        if not ml_ok:
            print("\n⚠️  ML server is not running. Start it to complete the test.")
        
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())