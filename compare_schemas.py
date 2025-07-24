#!/usr/bin/env python3
"""
Compare schemas between production and test databases
"""
import psycopg2
from collections import defaultdict

def get_table_schema(conn, table_name):
    """Get column information for a table"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = {}
    for row in cursor.fetchall():
        columns[row[0]] = {
            'data_type': row[1],
            'is_nullable': row[2],
            'column_default': row[3],
            'max_length': row[4]
        }
    cursor.close()
    return columns

def get_all_tables(conn):
    """Get all tables in the public schema"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def compare_databases():
    """Compare production and test database schemas"""
    
    # Production database
    prod_config = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "031203",
        "dbname": "active",
    }
    
    # Test database
    test_config = {
        "host": "localhost",
        "port": 5454,
        "user": "postgres",
        "password": "12931",
        "dbname": "youwoai_test",
    }
    
    print("=" * 80)
    print("DATABASE SCHEMA COMPARISON")
    print("=" * 80)
    print(f"Production: {prod_config['dbname']} (port {prod_config['port']})")
    print(f"Test: {test_config['dbname']} (port {test_config['port']})")
    print("=" * 80)
    
    try:
        # Connect to both databases
        prod_conn = psycopg2.connect(**prod_config)
        test_conn = psycopg2.connect(**test_config)
        
        # Get tables from both databases
        prod_tables = set(get_all_tables(prod_conn))
        test_tables = set(get_all_tables(test_conn))
        
        # Find common tables to compare
        common_tables = prod_tables & test_tables
        prod_only = prod_tables - test_tables
        test_only = test_tables - prod_tables
        
        if prod_only:
            print("\n❌ Tables only in PRODUCTION:")
            for table in sorted(prod_only):
                print(f"   - {table}")
        
        if test_only:
            print("\n❌ Tables only in TEST:")
            for table in sorted(test_only):
                print(f"   - {table}")
        
        # Compare schemas for common tables
        differences = defaultdict(list)
        
        for table in sorted(common_tables):
            if table in ['note_v1', 'folder_v1', 'conversation_v1', 'user_v1']:  # Focus on key tables
                prod_schema = get_table_schema(prod_conn, table)
                test_schema = get_table_schema(test_conn, table)
                
                # Find column differences
                prod_cols = set(prod_schema.keys())
                test_cols = set(test_schema.keys())
                
                # Columns only in prod
                prod_only_cols = prod_cols - test_cols
                if prod_only_cols:
                    differences[table].append(f"Columns only in PRODUCTION: {', '.join(prod_only_cols)}")
                
                # Columns only in test
                test_only_cols = test_cols - prod_cols
                if test_only_cols:
                    differences[table].append(f"Columns only in TEST: {', '.join(test_only_cols)}")
                
                # Check column name differences (case sensitivity)
                prod_lower = {col.lower(): col for col in prod_cols}
                test_lower = {col.lower(): col for col in test_cols}
                
                case_diffs = []
                for lower_name in prod_lower:
                    if lower_name in test_lower:
                        if prod_lower[lower_name] != test_lower[lower_name]:
                            case_diffs.append(f"{prod_lower[lower_name]} (prod) vs {test_lower[lower_name]} (test)")
                
                if case_diffs:
                    differences[table].append(f"Column name case differences: {', '.join(case_diffs)}")
        
        # Print differences
        if differences:
            print("\n🔴 SCHEMA DIFFERENCES:")
            for table, diffs in differences.items():
                print(f"\n{table}:")
                for diff in diffs:
                    print(f"   - {diff}")
        else:
            print("\n✅ No schema differences found in key tables")
        
        # Check specific columns we care about
        print("\n📊 KEY COLUMN COMPARISON:")
        for table in ['note_v1', 'folder_v1', 'conversation_v1']:
            if table in common_tables:
                print(f"\n{table}:")
                prod_schema = get_table_schema(prod_conn, table)
                test_schema = get_table_schema(test_conn, table)
                
                # Check for date columns
                for col_type in ['created', 'updated', 'deleted']:
                    prod_col = None
                    test_col = None
                    
                    for col in prod_schema:
                        if col_type in col.lower():
                            prod_col = col
                            break
                    
                    for col in test_schema:
                        if col_type in col.lower():
                            test_col = col
                            break
                    
                    if prod_col or test_col:
                        print(f"   {col_type}: prod='{prod_col}' vs test='{test_col}'")
        
        prod_conn.close()
        test_conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_databases()