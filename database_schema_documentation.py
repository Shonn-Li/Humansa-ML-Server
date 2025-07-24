#!/usr/bin/env python3
"""
Document the actual database schema to prevent column name issues
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connection parameters
db_params = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5454'),
    'database': os.getenv('DB_ACTIVE_DATABASE', 'youwoai_test'),
    'user': os.getenv('DB_USERNAME', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '12931')
}

print("Documenting Database Schema")
print("=" * 80)

try:
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    
    schema_doc = []
    schema_doc.append("# YouWoAI Database Schema Documentation")
    schema_doc.append("\nGenerated from actual database schema to prevent column name issues.")
    schema_doc.append("\n## Tables and Columns\n")
    
    for (table_name,) in tables:
        print(f"\nTable: {table_name}")
        print("-" * 40)
        
        schema_doc.append(f"\n### {table_name}")
        schema_doc.append("\n| Column Name | Data Type | Nullable | Default |")
        schema_doc.append("|-------------|-----------|----------|---------|")
        
        # Get columns for this table
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        for col_name, data_type, nullable, default in columns:
            print(f"  {col_name:<30} {data_type:<25} {nullable:<8} {default or ''}")
            
            # Clean up default value for markdown
            default_val = default if default else ""
            if len(default_val) > 50:
                default_val = default_val[:47] + "..."
            
            schema_doc.append(f"| {col_name} | {data_type} | {nullable} | {default_val} |")
    
    cursor.close()
    conn.close()
    
    # Write documentation
    with open("DATABASE_SCHEMA.md", "w") as f:
        f.write("\n".join(schema_doc))
    
    print("\n" + "=" * 80)
    print("Schema documentation written to DATABASE_SCHEMA.md")
    
    # Also create a quick reference for commonly used columns
    print("\n" + "=" * 80)
    print("QUICK REFERENCE - Common Column Name Patterns:")
    print("-" * 40)
    print("Date columns: createdate, updatedate, deletedat (all lowercase)")
    print("ID columns: id, ownerId, folderId, noteId, partId, typeId (camelCase)")
    print("Content columns: promptcontent, noteTitle (mixed)")
    print("Type columns: notetype, skipembedding (lowercase)")
    print("URL columns: imageUrl, audioURL (mixed case)")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()