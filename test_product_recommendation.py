#!/usr/bin/env python3
"""Test product recommendation functionality."""
import os
import sys
import asyncio
import aiohttp
import json

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5454'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_NAME'] = 'youwoai_test'

async def test_product_recommendation():
    """Test product recommendation functionality."""
    base_url = "http://localhost:5001"
    
    test_cases = [
        {
            "query": "你们有什么保健品推荐吗？",
            "description": "General product inquiry"
        },
        {
            "query": "我想买维生素D，有什么推荐？",
            "description": "Vitamin recommendation"
        },
        {
            "query": "有500元以下的保健品吗？",
            "description": "Price range filter"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_cases:
            print(f"\n{'='*60}")
            print(f"Testing: {test['description']}")
            print(f"Query: {test['query']}")
            print(f"{'='*60}")
            
            request_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": test['query']
                    }
                ],
                "stream": False,
                "user_id": f"test_product_user",
                "conversation_id": f"test_product_conv"
            }
            
            try:
                async with session.post(
                    f"{base_url}/v2/humansa/chat",
                    json=request_data,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    result = await response.json()
                    
                    print(f"Status: {response.status}")
                    
                    if result.get('choices'):
                        content = result['choices'][0]['message']['content']
                        print(f"Response:\n{content}")
                        
                        # Check if products were mentioned
                        if any(word in content for word in ['维生素', '产品', '胶囊', '价格', '元']):
                            print("\n✅ SUCCESS: Product information found in response")
                        else:
                            print("\n❌ FAILED: No product information in response")
                    else:
                        print(f"Error: {result}")
                        print("\n❌ FAILED: Invalid response format")
                        
            except Exception as e:
                print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_product_recommendation())