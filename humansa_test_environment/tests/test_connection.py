#!/usr/bin/env python3
"""
Test connection to Humansa test database.
"""

import psycopg2
import sys

# Humansa test database configuration
db_config = {
    'host': 'localhost',
    'port': 5456,  # Humansa-specific port
    'database': 'youwoai',
    'user': 'youwo',
    'password': 'youwo123'
}

print("🏥 Testing Humansa Test Database Connection")
print("=" * 50)
print(f"Connecting to: {db_config['host']}:{db_config['port']}/{db_config['database']}")

try:
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    print("✅ Connected successfully!")
    
    # Check Humansa-specific tables
    humansa_tables = [
        'humansa_users',
        'humansa_doctors',
        'humansa_clinics',
        'humansa_appointments',
        'humansa_patient_profile'
    ]
    
    print("\n📊 Checking Humansa tables:")
    for table in humansa_tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  - {table}: {count} records")
    
    # Show some doctors
    print("\n👨‍⚕️ Sample doctors:")
    cur.execute("SELECT name, specialty FROM humansa_doctors LIMIT 3")
    for row in cur.fetchall():
        print(f"  - {row[0]} ({row[1]})")
    
    conn.close()
    print("\n✅ Humansa test environment is working correctly!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nMake sure Humansa test database is running:")
    print("  cd humansa_test_environment")
    print("  ./setup.sh")
    sys.exit(1)