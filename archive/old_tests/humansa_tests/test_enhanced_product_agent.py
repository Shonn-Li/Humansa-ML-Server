#!/usr/bin/env python3
"""
Test script for Enhanced Product Agent with database connection
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["HUMANSA_USE_WORKFLOW_ORCHESTRATOR"] = "true"

from test_environment.unified_test_config import TEST_DB_CONFIG, setup_test_environment
from src.humansa.v2.agents.product_agent_enhanced import EnhancedProductAgent
from llama_index.llms.azure_openai import AzureOpenAI

# Test queries
TEST_QUERIES = [
    {
        "name": "General Product Search",
        "query": "我最近失眠很严重，有什么产品可以帮助改善睡眠吗？",
        "expected": ["褪黑素", "薰衣草", "助眠"]
    },
    {
        "name": "Specific Category Search",
        "query": "推荐一些适合孕妇的营养品",
        "expected": ["孕妇", "DHA", "叶酸", "母婴"]
    },
    {
        "name": "Multi-product Recommendation",
        "query": "我想买一套完整的血压血糖监测设备",
        "expected": ["血压计", "血糖仪", "套餐"]
    },
    {
        "name": "Budget-conscious Search",
        "query": "有什么200元以内的保健品推荐吗？",
        "expected": ["价格", "优惠", "套餐"]
    },
    {
        "name": "Symptom-based Recommendation",
        "query": "最近总是感觉疲劳，免疫力也下降了，需要补充什么？",
        "expected": ["维生素", "免疫", "保健品"]
    }
]


async def test_agent_initialization(agent):
    """Test agent initialization and cache loading."""
    print("\n=== Testing Agent Initialization ===")
    
    # Check cache
    await agent.ensure_fresh_cache()
    
    stats = agent.get_statistics()
    print(f"✅ Loaded {stats['total_products']} products")
    print(f"✅ Categories: {', '.join(stats['categories'])}")
    print(f"✅ Category counts: {json.dumps(stats['category_counts'], ensure_ascii=False)}")
    print(f"✅ Last refresh: {stats['last_refresh']}")
    
    return stats['total_products'] > 0


async def test_product_search(agent):
    """Test product search functionality."""
    print("\n=== Testing Product Search ===")
    
    # Test basic search
    results = await agent._search_products("维生素")
    print(f"\n搜索 '维生素' 找到 {len(results)} 个产品:")
    for r in results[:3]:
        print(f"  - {r['name']} (¥{r['price']}) - 相关度: {r['relevance_score']}")
    
    # Test category search
    results = await agent._search_products("", category="保健品")
    print(f"\n类别 '保健品' 找到 {len(results)} 个产品")
    
    # Test symptom search
    results = await agent._search_products("失眠")
    print(f"\n症状 '失眠' 找到 {len(results)} 个相关产品")
    
    return len(results) > 0


async def test_product_details(agent):
    """Test getting product details."""
    print("\n=== Testing Product Details ===")
    
    # Get a product from cache
    product_id = None
    for pid, product in agent.products_cache.items():
        product_id = pid
        break
    
    if product_id:
        details = await agent._get_product_details(product_id)
        print(f"\n产品详情 (ID: {product_id}):")
        print(f"  名称: {details['name']}")
        print(f"  价格: ¥{details['price']}")
        print(f"  库存: {details['stock_status']}")
        print(f"  类别: {details.get('category_name', 'N/A')}")
        
        return True
    return False


async def test_packages(agent):
    """Test product packages."""
    print("\n=== Testing Product Packages ===")
    
    packages = await agent._get_product_packages()
    print(f"\n找到 {len(packages)} 个产品套餐:")
    
    for pkg in packages[:3]:
        print(f"\n套餐: {pkg['name']}")
        print(f"  描述: {pkg['description']}")
        print(f"  原价: ¥{pkg['total_price']}")
        print(f"  折扣: {pkg['discount_percentage']}%")
        if 'items' in pkg:
            print(f"  包含 {len(pkg['items'])} 个产品")
    
    return len(packages) > 0


async def test_query_processing(agent):
    """Test full query processing with streaming."""
    print("\n=== Testing Query Processing ===")
    
    for test_case in TEST_QUERIES:
        print(f"\n测试: {test_case['name']}")
        print(f"查询: {test_case['query']}")
        print("响应:")
        print("-" * 50)
        
        response_text = ""
        async for chunk in agent.process_query(test_case['query'], {}, stream=True):
            if chunk['type'] == 'content':
                response_text += chunk['chunk']
                print(chunk['chunk'], end='', flush=True)
            elif chunk['type'] == 'error':
                print(f"\n❌ Error: {chunk['chunk']}")
        
        print("\n" + "-" * 50)
        
        # Check if expected terms appear in response
        found = []
        missing = []
        for expected in test_case['expected']:
            if expected.lower() in response_text.lower():
                found.append(expected)
            else:
                missing.append(expected)
        
        if found:
            print(f"✅ 找到预期内容: {', '.join(found)}")
        if missing:
            print(f"⚠️  缺少预期内容: {', '.join(missing)}")
        
        print()
        await asyncio.sleep(1)  # Avoid rate limiting


async def main():
    """Main test function."""
    print("=" * 60)
    print("Enhanced Product Agent Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup test environment
    setup_test_environment()
    
    # Initialize LLM
    try:
        llm = AzureOpenAI(
            deployment_name="gpt-4.1",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version="2023-05-15"
        )
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        print("Using mock LLM for testing...")
        from unittest.mock import MagicMock
        llm = MagicMock()
        llm.acomplete = MagicMock(return_value=MagicMock(text="Mock response"))
    
    # Create agent
    agent = EnhancedProductAgent(llm=llm, db_config=TEST_DB_CONFIG)
    
    # Run tests
    tests = [
        ("Initialization", test_agent_initialization),
        ("Product Search", test_product_search),
        ("Product Details", test_product_details),
        ("Product Packages", test_packages),
        ("Query Processing", test_query_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            result = await test_func(agent)
            results.append((test_name, result))
            if result:
                print(f"\n✅ {test_name} PASSED")
            else:
                print(f"\n❌ {test_name} FAILED")
        except Exception as e:
            print(f"\n❌ {test_name} ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())