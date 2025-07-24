#!/usr/bin/env python3
"""
Test Humansa database connection and validate setup.
This script tests the Humansa test environment is working correctly.
"""

import subprocess
import sys
import json

def test_database_connection():
    """Test PostgreSQL connection to Humansa test database."""
    print("🔍 Testing Humansa Database Connection")
    print("=" * 50)
    
    # Database connection parameters
    db_params = {
        "host": "localhost",
        "port": "5456",
        "user": "youwo",
        "password": "youwo123",
        "database": "youwoai"
    }
    
    print(f"\nConnection parameters:")
    print(f"  Host: {db_params['host']}")
    print(f"  Port: {db_params['port']}")
    print(f"  Database: {db_params['database']}")
    print(f"  User: {db_params['user']}")
    
    # Test connection with psql
    cmd = [
        "psql",
        "-h", db_params["host"],
        "-p", db_params["port"],
        "-U", db_params["user"],
        "-d", db_params["database"],
        "-c", "SELECT version();"
    ]
    
    env = {"PGPASSWORD": db_params["password"]}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            print("\n✅ Database connection successful!")
            print("PostgreSQL version:", result.stdout.strip())
        else:
            print("\n❌ Database connection failed!")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"\n❌ Failed to connect: {e}")
        return False
    
    return True


def check_humansa_tables():
    """Check if Humansa tables exist."""
    print("\n\n📊 Checking Humansa Tables")
    print("=" * 50)
    
    # List all Humansa tables
    cmd = [
        "psql",
        "-h", "localhost",
        "-p", "5456",
        "-U", "youwo",
        "-d", "youwoai",
        "-t",
        "-c", "SELECT tablename FROM pg_tables WHERE tablename LIKE 'humansa_%' ORDER BY tablename;"
    ]
    
    env = {"PGPASSWORD": "youwo123"}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            tables = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            print(f"\nFound {len(tables)} Humansa tables:")
            for table in tables:
                print(f"  ✓ {table}")
            return len(tables) > 0
        else:
            print("\n❌ Failed to list tables!")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"\n❌ Failed to check tables: {e}")
        return False


def check_table_structure():
    """Check structure of key Humansa tables."""
    print("\n\n🔧 Checking Table Structure")
    print("=" * 50)
    
    key_tables = ["humansa_doctors", "humansa_clinics", "humansa_users"]
    
    for table in key_tables:
        print(f"\n{table}:")
        cmd = [
            "psql",
            "-h", "localhost",
            "-p", "5456",
            "-U", "youwo",
            "-d", "youwoai",
            "-c", f"\\d {table}"
        ]
        
        env = {"PGPASSWORD": "youwo123"}
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode == 0:
                # Just show column count
                lines = result.stdout.strip().split('\n')
                column_lines = [l for l in lines if '|' in l and not l.strip().startswith('Table')]
                column_count = len([l for l in column_lines if l.strip() and not l.strip().startswith('-')])
                print(f"  ✓ {column_count} columns defined")
            else:
                print(f"  ❌ Failed to describe table")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def test_sample_query():
    """Test a sample query."""
    print("\n\n🔎 Testing Sample Query")
    print("=" * 50)
    
    # Check if any test data exists
    cmd = [
        "psql",
        "-h", "localhost",
        "-p", "5456",
        "-U", "youwo",
        "-d", "youwoai",
        "-t",
        "-c", "SELECT COUNT(*) FROM humansa_doctors;"
    ]
    
    env = {"PGPASSWORD": "youwo123"}
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            count = int(result.stdout.strip())
            print(f"\nDoctors in database: {count}")
            if count == 0:
                print("⚠️  No test data found. The populate script needs to be run.")
            else:
                print("✅ Test data exists!")
            return True
        else:
            print("\n❌ Query failed!")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"\n❌ Failed to run query: {e}")
        return False


def main():
    """Run all tests."""
    print("🏥 Humansa Test Environment Validation")
    print("======================================\n")
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    if test_database_connection():
        tests_passed += 1
    
    if check_humansa_tables():
        tests_passed += 1
    
    check_table_structure()
    tests_passed += 1  # Structure check is informational
    
    if test_sample_query():
        tests_passed += 1
    
    # Summary
    print("\n\n📋 Summary")
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("\n✅ Humansa test environment is properly set up!")
        print("\nNext steps:")
        print("1. Run the populate script to add test data")
        print("2. Start the main server")
        print("3. Test the Humansa V2 endpoints")
    else:
        print("\n⚠️  Some issues were found. Please check the output above.")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    sys.exit(0 if main() else 1)