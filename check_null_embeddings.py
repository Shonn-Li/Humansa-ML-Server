#!/usr/bin/env python3
"""
Script to check for embeddings with null content in the database
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Check for .env.local
if os.path.exists('.env.local'):
    load_dotenv('.env.local', override=True)
    print("Loaded .env.local configuration")

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USERNAME", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_ACTIVE_DATABASE", "youwoai"),
}

print(f"Connecting to database: {DB_CONFIG['dbname']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")

def check_null_embeddings():
    """Check for embeddings with null content"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n=== Checking for embeddings with NULL content ===\n")
        
        # 1. Check for embeddings where chunk_text is NULL
        cursor.execute("""
            SELECT type, type_id, section_id, source, metadata, last_updated
            FROM embedding_v1
            WHERE chunk_text IS NULL
            ORDER BY type, type_id, section_id
        """)
        
        null_chunk_text = cursor.fetchall()
        
        if null_chunk_text:
            print(f"Found {len(null_chunk_text)} embeddings with NULL chunk_text:")
            for row in null_chunk_text[:10]:  # Show first 10
                print(f"  - Type: {row['type']}, ID: {row['type_id']}, Section: {row['section_id']}, Source: {row['source']}")
            if len(null_chunk_text) > 10:
                print(f"  ... and {len(null_chunk_text) - 10} more")
        else:
            print("No embeddings found with NULL chunk_text ✓")
        
        # 2. Check for embeddings where chunk_text is empty string
        cursor.execute("""
            SELECT type, type_id, section_id, source, metadata, last_updated
            FROM embedding_v1
            WHERE chunk_text = ''
            ORDER BY type, type_id, section_id
        """)
        
        empty_chunk_text = cursor.fetchall()
        
        if empty_chunk_text:
            print(f"\nFound {len(empty_chunk_text)} embeddings with empty chunk_text:")
            for row in empty_chunk_text[:10]:  # Show first 10
                print(f"  - Type: {row['type']}, ID: {row['type_id']}, Section: {row['section_id']}, Source: {row['source']}")
            if len(empty_chunk_text) > 10:
                print(f"  ... and {len(empty_chunk_text) - 10} more")
        else:
            print("\nNo embeddings found with empty chunk_text ✓")
        
        # 3. Check for embeddings where embedding vector is NULL
        cursor.execute("""
            SELECT type, type_id, section_id, chunk_text, source, metadata, last_updated
            FROM embedding_v1
            WHERE embedding IS NULL
            ORDER BY type, type_id, section_id
        """)
        
        null_embedding = cursor.fetchall()
        
        if null_embedding:
            print(f"\nFound {len(null_embedding)} embeddings with NULL embedding vector:")
            for row in null_embedding[:10]:  # Show first 10
                chunk_preview = row['chunk_text'][:50] + '...' if row['chunk_text'] and len(row['chunk_text']) > 50 else row['chunk_text']
                print(f"  - Type: {row['type']}, ID: {row['type_id']}, Section: {row['section_id']}, Chunk: '{chunk_preview}'")
            if len(null_embedding) > 10:
                print(f"  ... and {len(null_embedding) - 10} more")
        else:
            print("\nNo embeddings found with NULL embedding vector ✓")
        
        # 4. Check for special SKIP_EMBEDDING markers
        cursor.execute("""
            SELECT type, type_id, section_id, chunk_text, embedding IS NULL as has_null_embedding
            FROM embedding_v1
            WHERE chunk_text = 'SKIP_EMBEDDING'
            ORDER BY type, type_id
        """)
        
        skip_markers = cursor.fetchall()
        
        if skip_markers:
            print(f"\nFound {len(skip_markers)} SKIP_EMBEDDING markers:")
            for row in skip_markers:
                print(f"  - Type: {row['type']}, ID: {row['type_id']}, Section: {row['section_id']}, Has NULL embedding: {row['has_null_embedding']}")
        else:
            print("\nNo SKIP_EMBEDDING markers found")
        
        # 5. Summary statistics
        cursor.execute("""
            SELECT 
                type,
                COUNT(*) as total_count,
                COUNT(CASE WHEN chunk_text IS NULL THEN 1 END) as null_chunk_count,
                COUNT(CASE WHEN chunk_text = '' THEN 1 END) as empty_chunk_count,
                COUNT(CASE WHEN embedding IS NULL THEN 1 END) as null_embedding_count,
                COUNT(CASE WHEN chunk_text = 'SKIP_EMBEDDING' THEN 1 END) as skip_marker_count
            FROM embedding_v1
            GROUP BY type
            ORDER BY type
        """)
        
        stats = cursor.fetchall()
        
        print("\n=== Summary Statistics ===")
        print("\nType       | Total | NULL chunk | Empty chunk | NULL embedding | Skip markers")
        print("-" * 80)
        for row in stats:
            print(f"{row['type']:10} | {row['total_count']:5} | {row['null_chunk_count']:10} | {row['empty_chunk_count']:11} | {row['null_embedding_count']:14} | {row['skip_marker_count']:12}")
        
        # 6. Check for any other potential issues
        print("\n=== Additional Checks ===")
        
        # Check for very short chunk_text (might indicate issues)
        cursor.execute("""
            SELECT type, type_id, section_id, chunk_text, LENGTH(chunk_text) as text_length
            FROM embedding_v1
            WHERE chunk_text IS NOT NULL 
              AND chunk_text != ''
              AND chunk_text != 'SKIP_EMBEDDING'
              AND LENGTH(chunk_text) < 5
            ORDER BY LENGTH(chunk_text), type, type_id
            LIMIT 20
        """)
        
        short_chunks = cursor.fetchall()
        
        if short_chunks:
            print(f"\nFound {len(short_chunks)} embeddings with very short chunk_text (< 5 chars):")
            for row in short_chunks:
                print(f"  - Type: {row['type']}, ID: {row['type_id']}, Section: {row['section_id']}, Text: '{row['chunk_text']}' (length: {row['text_length']})")
        else:
            print("\nNo embeddings found with suspiciously short chunk_text ✓")
        
        cursor.close()
        conn.close()
        
        print("\n=== Check Complete ===")
        
        # Return summary
        return {
            "null_chunk_text": len(null_chunk_text),
            "empty_chunk_text": len(empty_chunk_text),
            "null_embedding": len(null_embedding),
            "skip_markers": len(skip_markers),
            "short_chunks": len(short_chunks)
        }
        
    except Exception as e:
        print(f"\nError checking embeddings: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    check_null_embeddings()