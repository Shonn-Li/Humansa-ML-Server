#!/usr/bin/env python3
"""
Check conversation 648 issue in the actual database being used
"""
import os
import sys
import psycopg2
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import to get actual database config
from chat.postgres.db_manager import DB_CONFIG

print("=" * 60)
print("INVESTIGATING CONVERSATION 648 ISSUE")
print("=" * 60)
print(f"Using database: {DB_CONFIG['dbname']} on port {DB_CONFIG['port']}")
print("=" * 60)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. Check if conversation 648 exists
    cursor.execute("""
        SELECT id, "ownerId", title, "createDate", "deletedAt", 
               messages IS NOT NULL as has_messages,
               pg_typeof(messages) as msg_type,
               jsonb_typeof(messages) as json_type
        FROM conversation_v1
        WHERE id = 648
    """)
    conv = cursor.fetchone()
    
    if conv:
        print(f"\n1. Conversation Details:")
        print(f"   ID: {conv[0]}")
        print(f"   Owner ID: {conv[1]}")
        print(f"   Title: {conv[2] or 'Untitled'}")
        print(f"   Created: {conv[3]}")
        print(f"   Deleted: {'Yes' if conv[4] else 'No'}")
        print(f"   Has messages: {conv[5]}")
        print(f"   Messages type: {conv[6]}")
        print(f"   JSON type: {conv[7]}")
        
        # 2. Get the actual messages content
        cursor.execute("""
            SELECT messages
            FROM conversation_v1
            WHERE id = 648
        """)
        msg_result = cursor.fetchone()
        
        if msg_result and msg_result[0]:
            messages = msg_result[0]
            print(f"\n2. Messages Analysis:")
            print(f"   Python type: {type(messages)}")
            
            if isinstance(messages, str):
                print(f"   String length: {len(messages)}")
                print(f"   First 200 chars: {messages[:200]}...")
                try:
                    messages = json.loads(messages)
                    print(f"   Parsed successfully!")
                except:
                    print(f"   Failed to parse as JSON")
                    
            if isinstance(messages, (list, dict)):
                if isinstance(messages, list):
                    print(f"   Message count: {len(messages)}")
                    for i, msg in enumerate(messages[:3]):
                        print(f"   Message {i+1}: {msg}")
                elif isinstance(messages, dict):
                    print(f"   Dict keys: {list(messages.keys())}")
                    if 'messages' in messages:
                        print(f"   Has 'messages' key with {len(messages['messages'])} items")
        else:
            print(f"\n2. No messages found or NULL")
    else:
        print("\n❌ Conversation 648 not found in database")
        
    # 3. Check embeddings
    print(f"\n3. Checking Embeddings:")
    cursor.execute("""
        SELECT COUNT(*), 
               COUNT(DISTINCT section_id) as unique_sections,
               MIN(section_id) as min_section,
               MAX(section_id) as max_section
        FROM embedding_v1
        WHERE type = 'conversation' AND type_id = 648
    """)
    emb = cursor.fetchone()
    print(f"   Total embeddings: {emb[0]}")
    print(f"   Unique sections: {emb[1]}")
    if emb[0] > 0:
        print(f"   Section range: {emb[2]} to {emb[3]}")
        
        # Check for skip markers
        cursor.execute("""
            SELECT COUNT(*)
            FROM embedding_v1
            WHERE type = 'conversation' 
            AND type_id = 648 
            AND chunk_text = 'SKIP_EMBEDDING'
        """)
        skip_count = cursor.fetchone()[0]
        print(f"   Skip markers: {skip_count}")
        
    # 4. Check how the conversation embedder is querying
    print(f"\n4. Testing Query Methods:")
    
    # The query that's failing in conversation_embedder
    cursor.execute("""
        SELECT messages
        FROM conversation_v1
        WHERE id = %s
    """, (648,))
    result = cursor.fetchone()
    
    if result and result[0]:
        messages = result[0]
        print(f"   Query returned: {type(messages)}")
        
        # Try to extract messages array
        if isinstance(messages, dict) and 'messages' in messages:
            msg_array = messages['messages']
            print(f"   Found nested messages array with {len(msg_array)} items")
        elif isinstance(messages, list):
            print(f"   Direct message array with {len(messages)} items")
        else:
            print(f"   Unexpected format: {str(messages)[:100]}...")
    else:
        print(f"   Query returned None or empty")
        
    # 5. Check if there's a column name issue
    print(f"\n5. Checking Column Names:")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'conversation_v1'
        AND column_name IN ('messages', 'Messages')
    """)
    cols = cursor.fetchall()
    for col in cols:
        print(f"   Column: {col[0]}, Type: {col[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    if conv and emb[0] > 0:
        print("✅ Conversation 648 EXISTS and HAS embeddings")
        print("⚠️  The issue is with message extraction in conversation_embedder.py")
        print("   Possible causes:")
        print("   1. Messages might be nested in a 'messages' key")
        print("   2. Messages might be in unexpected format")
        print("   3. Query might be failing due to permissions or connection issues")
    else:
        print("❌ Either conversation doesn't exist or has no embeddings")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()