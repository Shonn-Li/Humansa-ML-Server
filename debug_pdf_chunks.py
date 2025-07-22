#!/usr/bin/env python3
"""
Debug script to check what chunks are stored for a PDF URL
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.chat.postgres.url_embedding_operations import url_embedding_ops

def debug_pdf_chunks():
    url = "https://arxiv.org/pdf/2505.18499.pdf"
    user_id = 10001
    
    print(f"Checking chunks for URL: {url}")
    print(f"User ID: {user_id}")
    print("="*80)
    
    # Get all chunks for this URL
    chunks = url_embedding_ops.get_user_url_embeddings(url, user_id)
    
    if not chunks:
        print("No chunks found!")
        # Check if URL exists in database at all
        print("\nChecking if URL exists without user_id...")
        # Try a direct query
        from src.chat.postgres.connection_manager import connection_manager
        with connection_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count, url 
                    FROM embedding_v1 
                    WHERE url LIKE %s 
                    GROUP BY url
                """, (f"%{url.split('/')[-1]}%",))
                results = cursor.fetchall()
                if results:
                    print("Found URLs in database:")
                    for count, found_url in results:
                        print(f"  - {found_url} ({count} chunks)")
                else:
                    print("No URLs found matching pattern")
        return
    
    print(f"Found {len(chunks)} chunks")
    print()
    
    # Display each chunk
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"  Section ID: {chunk.get('section_id', 'N/A')}")
        print(f"  Source: {chunk.get('source', 'N/A')}")
        print(f"  Text length: {len(chunk.get('chunk_text', ''))}")
        
        # Show first 500 chars of text
        text = chunk.get('chunk_text', '')
        preview = text[:500] + "..." if len(text) > 500 else text
        print(f"  Text preview: {preview}")
        print("-"*40)

if __name__ == "__main__":
    debug_pdf_chunks()