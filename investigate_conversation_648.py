#!/usr/bin/env python3
"""
Investigate conversation 648 to see if it has messages and embeddings
"""
import psycopg2
import json

# Production database config
prod_config = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres", 
    "password": "031203",
    "dbname": "active",
}

print("=" * 60)
print("INVESTIGATING CONVERSATION 648")
print("=" * 60)

try:
    conn = psycopg2.connect(**prod_config)
    cursor = conn.cursor()
    
    # 1. Check if conversation exists
    cursor.execute("""
        SELECT id, "ownerId", title, "createDate", "deletedAt", messages
        FROM conversation_v1
        WHERE id = 648
    """)
    conv = cursor.fetchone()
    
    if conv:
        print(f"\n1. Conversation found:")
        print(f"   ID: {conv[0]}")
        print(f"   Owner: {conv[1]}")
        print(f"   Title: {conv[2] or 'Untitled'}")
        print(f"   Created: {conv[3]}")
        print(f"   Deleted: {conv[4] or 'No'}")
        
        # Check messages
        messages = conv[5]
        if messages:
            if isinstance(messages, str):
                try:
                    messages = json.loads(messages)
                except:
                    pass
            
            if isinstance(messages, list):
                print(f"   Messages count: {len(messages)}")
                print("\n   Sample messages:")
                for i, msg in enumerate(messages[:3]):
                    print(f"     {i+1}. Role: {msg.get('role', 'unknown')}, Content: {str(msg.get('content', ''))[:100]}...")
            else:
                print(f"   Messages type: {type(messages)}")
                print(f"   Messages content: {str(messages)[:200]}...")
        else:
            print(f"   Messages: None or empty")
    else:
        print("❌ Conversation 648 not found")
    
    # 2. Check embeddings for this conversation
    print("\n2. Checking embeddings:")
    cursor.execute("""
        SELECT COUNT(*), MIN(section_id), MAX(section_id)
        FROM embedding_v1
        WHERE type = 'conversation' AND type_id = 648
    """)
    emb = cursor.fetchone()
    print(f"   Embedding count: {emb[0]}")
    if emb[0] > 0:
        print(f"   Section IDs: {emb[1]} to {emb[2]}")
        
        # Get sample embeddings
        cursor.execute("""
            SELECT section_id, LENGTH(chunk_text) as text_len, 
                   SUBSTRING(chunk_text, 1, 100) as preview
            FROM embedding_v1
            WHERE type = 'conversation' AND type_id = 648
            ORDER BY section_id
            LIMIT 3
        """)
        samples = cursor.fetchall()
        print("\n   Sample embeddings:")
        for s in samples:
            print(f"     Section {s[0]}: {s[1]} chars - {s[2]}...")
    
    # 3. Check what the query is looking for
    print("\n3. Debugging the messages query issue:")
    
    # Check the exact structure of messages column
    cursor.execute("""
        SELECT 
            pg_typeof(messages) as data_type,
            messages IS NULL as is_null,
            messages = '[]' as is_empty_array,
            messages = '{}' as is_empty_object,
            CASE 
                WHEN messages IS NULL THEN 'NULL'
                WHEN messages::text = '[]' THEN 'Empty array'
                WHEN messages::text = '{}' THEN 'Empty object'
                ELSE 'Has content'
            END as status
        FROM conversation_v1
        WHERE id = 648
    """)
    msg_check = cursor.fetchone()
    if msg_check:
        print(f"   Messages data type: {msg_check[0]}")
        print(f"   Is NULL: {msg_check[1]}")
        print(f"   Is empty array: {msg_check[2]}")
        print(f"   Is empty object: {msg_check[3]}")
        print(f"   Status: {msg_check[4]}")
    
    # 4. Try different message extraction methods
    print("\n4. Testing message extraction methods:")
    
    # Method 1: Direct JSONB
    cursor.execute("""
        SELECT jsonb_array_length(messages) as msg_count
        FROM conversation_v1
        WHERE id = 648 AND messages IS NOT NULL
    """)
    result = cursor.fetchone()
    if result:
        print(f"   JSONB array length: {result[0]}")
    
    # Method 2: Extract messages with different approaches
    cursor.execute("""
        SELECT 
            messages,
            jsonb_typeof(messages) as json_type
        FROM conversation_v1
        WHERE id = 648
    """)
    result = cursor.fetchone()
    if result and result[0]:
        print(f"   JSONB type: {result[1]}")
        messages = result[0]
        if isinstance(messages, dict) and 'messages' in messages:
            print(f"   Messages might be nested in 'messages' key")
            print(f"   Content: {str(messages)[:200]}...")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    if conv and emb[0] > 0:
        print("✅ Conversation 648 HAS embeddings")
        print("⚠️  The issue is likely with how messages are being extracted")
        print("   The query might be looking in the wrong place or format")
    else:
        print("❌ Conversation 648 either doesn't exist or has no embeddings")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()