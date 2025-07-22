#!/usr/bin/env python3
"""
Simple debug script to check PDF chunks in database
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration for test environment
DB_CONFIG = {
    'host': os.getenv('TEST_POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('TEST_POSTGRES_PORT', 5454)),
    'database': os.getenv('TEST_POSTGRES_DB', 'youwoai_test'),
    'user': os.getenv('TEST_POSTGRES_USER', 'postgres'),
    'password': os.getenv('TEST_POSTGRES_PASSWORD', '12931'),
}

def debug_pdf_chunks():
    url = "https://arxiv.org/pdf/2505.18499.pdf"
    user_id = 10001
    
    print(f"Checking chunks for URL: {url}")
    print(f"User ID: {user_id}")
    print("="*80)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if URL exists at all
        cursor.execute("""
            SELECT COUNT(*) as count, url, type_id 
            FROM embedding_v1 
            WHERE url LIKE %s 
            GROUP BY url, type_id
            ORDER BY count DESC
        """, (f"%2505.18499%",))
        
        results = cursor.fetchall()
        if results:
            print("Found URLs in database:")
            for row in results:
                print(f"  - URL: {row['url']}")
                print(f"    User ID: {row['type_id']}")
                print(f"    Chunks: {row['count']}")
            print()
        else:
            print("No URLs found matching pattern '2505.18499'")
            return
        
        # Now get chunks for our specific URL and user
        # Try both normalized and non-normalized versions
        urls_to_try = [
            url,
            url.split('?')[0],  # Remove query params
            "https://arxiv.org/pdf/2505.18499"  # Without .pdf
        ]
        
        chunks_found = False
        for test_url in urls_to_try:
            cursor.execute("""
                SELECT chunk_text, source, section_id, metadata
                FROM embedding_v1 
                WHERE type = 'user' AND type_id = %s AND url = %s
                ORDER BY section_id
            """, (user_id, test_url))
            
            chunks = cursor.fetchall()
            if chunks:
                chunks_found = True
                print(f"Found {len(chunks)} chunks for URL: {test_url}")
                print()
                
                # Display each chunk
                for i, chunk in enumerate(chunks):
                    print(f"Chunk {i+1}:")
                    print(f"  Section ID: {chunk['section_id']}")
                    print(f"  Source: {chunk['source']}")
                    
                    text = chunk['chunk_text']
                    print(f"  Text length: {len(text)}")
                    
                    # Show first 500 chars of text
                    preview = text[:500] + "..." if len(text) > 500 else text
                    print(f"  Text preview: {preview}")
                    print("-"*40)
                break
        
        if not chunks_found:
            print("No chunks found for any URL variation with user_id 10001")
            
            # Check what user IDs have this URL
            cursor.execute("""
                SELECT DISTINCT type_id 
                FROM embedding_v1 
                WHERE url LIKE %s AND type = 'user'
            """, (f"%2505.18499%",))
            
            user_ids = [row['type_id'] for row in cursor.fetchall()]
            if user_ids:
                print(f"\nURL exists for user IDs: {user_ids}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pdf_chunks()