#!/usr/bin/env python3
"""Verify test database connection and data"""

import os
import sys

# Set test environment BEFORE any imports
os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5454'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_NAME'] = 'youwoai_test'

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import after environment is set
from humansa.postgres.database import db, DB_CONFIG
from chat.postgres.db_manager import PostgresManager

print("="*60)
print("TEST DATABASE CONNECTION VERIFICATION")
print("="*60)

print("\nHumansaDatabase Configuration:")
print(f"  Host: {DB_CONFIG['host']}")
print(f"  Port: {DB_CONFIG['port']}")
print(f"  Database: {DB_CONFIG['dbname']}")
print(f"  User: {DB_CONFIG['user']}")

# Test HumansaDatabase
print("\n1. Testing HumansaDatabase connection...")
try:
    # Test direct query
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM humansa_doctor")
            count = cursor.fetchone()[0]
            print(f"   ✅ Success! Found {count} doctors")
            
            # Test doctor search
            doctors = db.search_doctors_with_fallback(specialty="骨科")
            print(f"   ✅ Search test: Found {len(doctors)} doctors with 骨科")
            if doctors:
                print(f"      - First match: {doctors[0]['name']} - {doctors[0]['expertise']}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test PostgresManager
print("\n2. Testing PostgresManager connection...")
try:
    pm = PostgresManager()
    print(f"   Config: {pm.db_config}")
    with pm.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]
            print(f"   ✅ Connected to database: {db_name}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test product data
print("\n3. Testing product data...")
try:
    # Test direct query for products
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM humansa_products")
            count = cursor.fetchone()[0]
            print(f"   ✅ Found {count} total products in database")
            
            # Check if search_products method exists
            if hasattr(db, 'search_products'):
                products = db.search_products(category="vitamins", limit=5)
                print(f"   ✅ search_products method returned {len(products)} vitamin products")
                if products:
                    print(f"      - Example: {products[0]['name']} - ¥{products[0]['price']}")
            else:
                print("   ⚠️  search_products method not implemented in HumansaDatabase")
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "="*60)
print("✅ Database verification complete!")
print("="*60)