"""
Test Product Agent with WorkflowOrchestrator
Uses more specific queries to trigger product agent
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

API_URL = "http://localhost:6001/v2/humansa/chat"

async def test_product_workflow():
    """Test product queries through workflow orchestrator"""
    
    test_queries = [
        {
            "name": "Health Mall Query",
            "query": "我想买保健品，健康商城有什么推荐？",
            "expected": ["健康商城", "产品", "保健品"]
        },
        {
            "name": "Product List Query", 
            "query": "诺亚新舟健康商城有哪些DHA产品？列出具体的产品名称和价格",
            "expected": ["DHA", "产品", "价格", "童年故事"]
        },
        {
            "name": "Specific Product Query",
            "query": "童年故事复合磷脂酰丝氨酸凝胶糖果的详细信息和购买链接",
            "expected": ["童年故事", "磷脂酰丝氨酸", "youzan.com", "链接"]
        },
        {
            "name": "Children Nutrition Query",
            "query": "给5岁孩子提高免疫力的保健品推荐，要诺亚新舟商城的产品",
            "expected": ["免疫", "儿童", "产品", "推荐"]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_queries:
            print(f"\n{'='*60}")
            print(f"Test: {test['name']}")
            print(f"Query: {test['query']}")
            print(f"{'='*60}")
            
            request_data = {
                "user_id": f"test_product_{int(time.time())}",
                "messages": [
                    {"role": "user", "content": test['query']}
                ],
                "stream": False
            }
            
            try:
                start_time = time.time()
                async with session.post(
                    API_URL, 
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        duration = time.time() - start_time
                        
                        # Extract content
                        content = ""
                        if 'choices' in result and len(result['choices']) > 0:
                            content = result['choices'][0]['message']['content']
                        elif 'response' in result:
                            content = result['response']
                        elif 'output' in result and len(result['output']) > 0:
                            content = result['output'][0].get('content', '')
                        
                        print(f"\nStatus: {response.status}")
                        print(f"Duration: {duration:.2f}s")
                        print(f"Response length: {len(content)} chars")
                        
                        # Check for expected keywords
                        found = []
                        missing = []
                        for keyword in test['expected']:
                            if keyword in content:
                                found.append(keyword)
                            else:
                                missing.append(keyword)
                        
                        print(f"Found keywords: {found}")
                        print(f"Missing keywords: {missing}")
                        
                        # Check for product details
                        if 'youzan.com' in content:
                            print("✓ Product URL found")
                            # Extract URLs
                            import re
                            urls = re.findall(r'https://shop\d+\.m\.youzan\.com/v2/goods/\w+', content)
                            if urls:
                                print(f"URLs: {urls[:3]}")  # Show first 3
                        
                        # Check usage info
                        usage = result.get('usage', {})
                        if usage:
                            print(f"\nUsage info:")
                            print(f"  Agents used: {usage.get('agents_used', [])}")
                            print(f"  Total agents: {usage.get('total_agents', 0)}")
                        
                        print(f"\nResponse preview:")
                        print(content[:800] + "..." if len(content) > 800 else content)
                        
                    else:
                        error_text = await response.text()
                        print(f"Error: HTTP {response.status}")
                        print(f"Error text: {error_text[:200]}")
                        
            except asyncio.TimeoutError:
                print("Request timed out after 60 seconds")
            except Exception as e:
                print(f"Exception: {e}")
            
            # Small delay between tests
            await asyncio.sleep(2)

if __name__ == "__main__":
    print("Testing Product Agent with WorkflowOrchestrator")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_URL}")
    print("\nNote: WorkflowOrchestrator should route product queries to ProductAgent")
    
    asyncio.run(test_product_workflow())