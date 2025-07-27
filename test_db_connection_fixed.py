#!/usr/bin/env python3
"""Quick test to verify database connection with proper env vars"""

import os

# Set ALL test environment variables BEFORE any imports
os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5454'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '031203'
os.environ['DB_NAME'] = 'youwoai_test'

# Now import after setting environment
import psycopg2
from psycopg2.extras import RealDictCursor
from src.humansa.postgres.database import db, DB_CONFIG

print("Database configuration:")
print(f"  Host: {DB_CONFIG['host']}")
print(f"  Port: {DB_CONFIG['port']}")  
print(f"  Database: {DB_CONFIG['dbname']}")
print(f"  User: {DB_CONFIG['user']}")

# Test direct connection
try:
    print("\nTesting direct connection to test database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT COUNT(*) as count FROM humansa_doctor")
    result = cursor.fetchone()
    print(f"✅ Direct connection successful. Doctor count: {result['count']}")
    
    cursor.execute("SELECT name, expertise FROM humansa_doctor WHERE expertise ILIKE '%骨科%'")
    doctors = cursor.fetchall()
    print(f"\n骨科 doctors found: {len(doctors)}")
    for doc in doctors:
        print(f"  - {doc['name']}: {doc['expertise']}")
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Direct connection failed: {e}")

# Test using db instance
print("\n\nTesting db instance...")
try:
    doctors = db.search_doctors_with_fallback(specialty="骨科")
    print(f"✅ db instance search successful. Found {len(doctors)} doctors")
    for doc in doctors[:3]:  # Show first 3
        print(f"  - {doc['name']}: {doc['expertise']}")
except Exception as e:
    print(f"❌ db instance search failed: {e}")