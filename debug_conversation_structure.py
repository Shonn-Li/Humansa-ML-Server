#!/usr/bin/env python3
"""
Debug conversation message structure
"""
import os
import sys
import psycopg2
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Create a test conversation to investigate
print("=" * 60)
print("DEBUGGING CONVERSATION MESSAGE STRUCTURE")
print("=" * 60)

# Use test database
test_config = {
    "host": "localhost",
    "port": 5454,
    "user": "postgres",
    "password": "12931",
    "dbname": "youwoai_test",
}

try:
    conn = psycopg2.connect(**test_config)
    cursor = conn.cursor()
    
    # Get a sample conversation with messages
    cursor.execute("""
        SELECT id, "ownerId", messages, 
               jsonb_typeof(messages) as json_type,
               jsonb_array_length(messages) as array_length
        FROM conversation_v1
        WHERE messages IS NOT NULL
        AND jsonb_typeof(messages) = 'array'
        ORDER BY "createDate" DESC
        LIMIT 5
    """)
    
    conversations = cursor.fetchall()
    
    if conversations:
        print("\nSample conversations with array messages:")
        for conv in conversations:
            print(f"\n  Conversation {conv[0]} (Owner: {conv[1]})")
            print(f"  - JSON type: {conv[3]}")
            print(f"  - Array length: {conv[4]}")
            
            # Get the actual messages
            cursor.execute("""
                SELECT messages
                FROM conversation_v1
                WHERE id = %s
            """, (conv[0],))
            
            msg_result = cursor.fetchone()
            if msg_result and msg_result[0]:
                messages = msg_result[0]
                print(f"  - First message: {messages[0] if messages else 'None'}")
    
    # Check if any conversations have object-type messages
    cursor.execute("""
        SELECT id, "ownerId", messages
        FROM conversation_v1
        WHERE messages IS NOT NULL
        AND jsonb_typeof(messages) = 'object'
        LIMIT 3
    """)
    
    obj_conversations = cursor.fetchall()
    
    if obj_conversations:
        print("\n\nConversations with object messages:")
        for conv in obj_conversations:
            print(f"\n  Conversation {conv[0]} (Owner: {conv[1]})")
            messages = conv[2]
            if isinstance(messages, dict):
                print(f"  - Object keys: {list(messages.keys())}")
                if 'messages' in messages:
                    print(f"  - Has 'messages' key with {len(messages['messages'])} items")
                    print(f"  - First message in array: {messages['messages'][0] if messages['messages'] else 'None'}")
    
    # Create a test conversation with the structure we expect
    print("\n\nCreating test conversation 9999:")
    
    # First check if it exists
    cursor.execute("SELECT id FROM conversation_v1 WHERE id = 9999")
    if cursor.fetchone():
        cursor.execute("DELETE FROM conversation_v1 WHERE id = 9999")
        conn.commit()
    
    # Create with proper structure
    test_messages = [
        {
            "role": "user",
            "content": "Test message from user"
        },
        {
            "role": "assistant", 
            "content": "Test response from assistant"
        }
    ]
    
    cursor.execute("""
        INSERT INTO conversation_v1 (id, "ownerId", title, messages, "createDate", "updateDate")
        VALUES (9999, 10001, 'Test Conversation', %s::jsonb, NOW(), NOW())
    """, (json.dumps(test_messages),))
    
    conn.commit()
    
    # Now test the embedding operations query
    print("\nTesting embedding operations query:")
    cursor.execute("""
        SELECT c.id, c.messages, c."createDate"
        FROM conversation_v1 c
        WHERE c.id = 9999
    """)
    
    result = cursor.fetchone()
    if result:
        print(f"  Query returned: {result[0]}")
        print(f"  Messages type: {type(result[1])}")
        print(f"  Messages content: {result[1]}")
        
        # Try to process like the embedding code does
        messages_data = result[1] if result[1] else []
        print(f"\n  Processing messages:")
        for idx, msg in enumerate(messages_data):
            print(f"    Message {idx}: {msg}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()