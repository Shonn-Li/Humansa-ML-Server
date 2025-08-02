"""
Simple Product Agent Test
Direct test without SSE parsing complexity
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

API_URL = "http://localhost:6001/v2/humansa/chat"

async def test_product_query():
    """Test a simple product query"""
    
    async with aiohttp.ClientSession() as session:
        # Test 1: DHA Product Query
        print("\n=== Test 1: DHA Product Query ===")
        request_data = {
            "user_id": "test_user_001", 
            "messages": [
                {"role": "user", "content": "给孩子补充DHA，有什么推荐的产品？"}
            ],
            "stream": False  # Non-streaming for simplicity
        }
        
        try:
            start_time = time.time()
            async with session.post(API_URL, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    print(f"Status: {response.status}")
                    print(f"Duration: {duration:.2f}s")
                    
                    # Extract response content
                    if 'response' in result:
                        content = result['response']
                    elif 'output' in result and len(result['output']) > 0:
                        content = result['output'][0].get('content', '')
                    else:
                        content = str(result)
                    
                    print(f"Response length: {len(content)} chars")
                    print(f"Response preview: {content[:500]}...")
                    
                    # Check for product mentions
                    product_keywords = ['DHA', '藻油', '童年故事', '产品', '推荐']
                    found_keywords = [kw for kw in product_keywords if kw in content]
                    print(f"Found keywords: {found_keywords}")
                    
                    # Check for tool usage (from debug info if available)
                    if 'debug' in result:
                        print(f"Debug info available: {list(result['debug'].keys())}")
                        
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Error text: {error_text[:200]}")
                    
        except asyncio.TimeoutError:
            print("Request timed out after 30 seconds")
        except Exception as e:
            print(f"Exception: {e}")
            
        # Test 2: Sleep Product Query
        print("\n\n=== Test 2: Sleep Product Query ===")
        request_data = {
            "user_id": "test_user_002",
            "messages": [
                {"role": "user", "content": "最近失眠严重，有什么保健品可以帮助改善睡眠？"}
            ],
            "stream": False
        }
        
        try:
            start_time = time.time()
            async with session.post(API_URL, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    print(f"Status: {response.status}")
                    print(f"Duration: {duration:.2f}s")
                    
                    # Extract response
                    if 'response' in result:
                        content = result['response']
                    elif 'output' in result and len(result['output']) > 0:
                        content = result['output'][0].get('content', '')
                    else:
                        content = str(result)
                        
                    print(f"Response length: {len(content)} chars")
                    print(f"Response preview: {content[:500]}...")
                    
                    # Check for sleep-related products
                    sleep_keywords = ['失眠', '睡眠', '褪黑素', '安神', '助眠']
                    found_keywords = [kw for kw in sleep_keywords if kw in content]
                    print(f"Found keywords: {found_keywords}")
                    
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Error text: {error_text[:200]}")
                    
        except Exception as e:
            print(f"Exception: {e}")
            
        # Test 3: Specific Product Query
        print("\n\n=== Test 3: Specific Product Query ===")
        request_data = {
            "user_id": "test_user_003",
            "messages": [
                {"role": "user", "content": "童年故事DHA藻油的具体信息"}
            ],
            "stream": False
        }
        
        try:
            start_time = time.time()
            async with session.post(API_URL, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    print(f"Status: {response.status}")
                    print(f"Duration: {duration:.2f}s")
                    
                    # Extract response
                    if 'response' in result:
                        content = result['response']
                    elif 'output' in result and len(result['output']) > 0:
                        content = result['output'][0].get('content', '')
                    else:
                        content = str(result)
                        
                    print(f"Response length: {len(content)} chars")
                    
                    # Check for product details
                    detail_keywords = ['童年故事', 'DHA', '藻油', '用法', '成分']
                    found_keywords = [kw for kw in detail_keywords if kw in content]
                    print(f"Found keywords: {found_keywords}")
                    
                    # Check for URL
                    if 'youzan.com' in content:
                        print("✓ Product URL found")
                    else:
                        print("✗ No product URL found")
                        
                    print(f"\nFull response:\n{content}")
                    
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Error text: {error_text[:200]}")
                    
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    print(f"Starting Product Agent Simple Test")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_URL}")
    
    asyncio.run(test_product_query())