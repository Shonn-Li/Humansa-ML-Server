#!/usr/bin/env python3
"""
Test script for CSV-based Product Agent
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock LlamaIndex if needed
try:
    from llama_index.core.llms import LLM
    from llama_index.core.tools import FunctionTool
    from llama_index.core.agent import ReActAgent
except ImportError:
    print("Warning: LlamaIndex not available, using mocks")
    
    class LLM:
        pass
    
    class FunctionTool:
        @staticmethod
        def from_defaults(fn, name, description):
            return {'fn': fn, 'name': name, 'description': description}
    
    class ReActAgent:
        @classmethod
        def from_tools(cls, tools, llm, system_prompt, verbose=True):
            return cls()
        
        def chat(self, query):
            return type('obj', (), {'response': 'Mock response'})()
        
        def stream_chat(self, query):
            class AsyncGen:
                async def async_response_gen(self):
                    for word in "Mock streaming response".split():
                        yield word + " "
            return AsyncGen()


# Import the CSV-based agent
from src.humansa.v2.agents.product_agent_csv import ProductAgentCSV, Product


class MockLLM:
    """Mock LLM for testing"""
    async def acomplete(self, prompt):
        # Simple mock responses based on prompt content
        if "需求分析" in prompt:
            return type('obj', (), {
                'text': json.dumps({
                    "demands": [
                        {"category": "核心目标", "details": "改善睡眠质量"}
                    ]
                })
            })()
        elif "营养科学" in prompt:
            return type('obj', (), {
                'text': json.dumps({
                    "benefits": [
                        {"nutrient": "褪黑素", "mechanism": "调节生物钟"}
                    ]
                })
            })()
        else:
            return type('obj', (), {'text': 'Mock response'})()


async def test_csv_loading():
    """Test CSV loading functionality"""
    print("\n=== Testing CSV Loading ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=False
    )
    
    stats = agent.get_statistics()
    print(f"✅ Loaded {stats['total_products']} products")
    print(f"✅ Categories: {', '.join(stats['categories'])}")
    print(f"✅ Popular tags: {', '.join(stats['popular_tags'][:5])}")
    
    # Show sample products
    print("\nSample products by category:")
    for category, products in list(agent.categories.items())[:3]:
        print(f"\n{category}:")
        for product in products[:2]:
            print(f"  - {product.name}")
            print(f"    标签: {', '.join(product.tags[:3])}")
    
    return stats['total_products'] > 0


async def test_product_search():
    """Test product search functionality"""
    print("\n=== Testing Product Search ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=False
    )
    
    # Test symptom search
    test_cases = [
        ("失眠", "睡眠相关产品"),
        ("儿童", "儿童营养产品"),
        ("备孕", "备孕相关产品"),
        ("免疫力", "免疫增强产品")
    ]
    
    for symptoms, description in test_cases:
        print(f"\n搜索 '{symptoms}' ({description}):")
        results = await agent._search_products_by_symptoms(symptoms)
        print(f"  找到 {len(results)} 个相关产品")
        
        for product in results[:3]:
            print(f"  - {product['name']} (相关度: {product['relevance_score']})")
            print(f"    标签: {', '.join(product['tags'][:3])}")
    
    return True


async def test_tag_search():
    """Test tag-based search"""
    print("\n=== Testing Tag Search ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=False
    )
    
    # Test tag search
    tag_searches = ["长高", "DHA", "维生素", "备孕"]
    
    for tag in tag_searches:
        print(f"\n搜索标签 '{tag}':")
        results = await agent._search_products_by_tags(tag)
        print(f"  找到 {len(results)} 个产品")
        
        for product in results[:2]:
            print(f"  - {product['name']}")
            print(f"    匹配标签: {', '.join(product['matching_tags'])}")


async def test_product_recommendations():
    """Test product combination recommendations"""
    print("\n=== Testing Product Recommendations ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=False
    )
    
    # Test recommendations
    needs = ["儿童生长", "免疫提升", "睡眠改善"]
    
    for need in needs:
        print(f"\n针对 '{need}' 的推荐:")
        recommendations = await agent._recommend_product_combinations(need)
        
        print(f"主要产品 ({len(recommendations['primary'])}):")
        for product in recommendations['primary'][:2]:
            print(f"  - {product['name']}")
        
        print(f"辅助产品 ({len(recommendations['complementary'])}):")
        for product in recommendations['complementary'][:2]:
            print(f"  - {product['name']}")
        
        print(f"推荐理由: {recommendations['reason']}")


async def test_streaming_response():
    """Test streaming query processing"""
    print("\n=== Testing Streaming Response ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=False
    )
    
    # Mock the ReActAgent for testing
    agent.agent = ReActAgent()
    
    query = "我家孩子最近睡眠不好，有什么产品推荐吗？"
    print(f"查询: {query}")
    print("响应: ", end='')
    
    response_text = ""
    async for chunk in agent.process_query(query, {}, stream=True):
        if chunk['type'] == 'content':
            print(chunk['chunk'], end='', flush=True)
            response_text += chunk['chunk']
        elif chunk['type'] == 'error':
            print(f"\n❌ Error: {chunk['chunk']}")
    
    print("\n")
    return len(response_text) > 0


async def test_multi_expert_mode():
    """Test multi-expert consultation mode"""
    print("\n=== Testing Multi-Expert Mode ===")
    
    agent = ProductAgentCSV(
        llm=MockLLM(),
        csv_path='data/noah_supplements.csv',
        use_multi_expert=True  # Enable multi-expert
    )
    
    query = "3岁儿童挑食，需要补充什么营养？"
    
    # Test multi-expert consultation
    expert_insights = await agent._multi_expert_consultation(query)
    
    if expert_insights:
        print("✅ Multi-expert consultation completed")
        print(f"  - Demand analysis: {len(expert_insights.get('demand_analysis', ''))} chars")
        print(f"  - Nutrition science: {len(expert_insights.get('nutrition_science', ''))} chars")
        print(f"  - Risk assessment: {len(expert_insights.get('risk_assessment', ''))} chars")
    else:
        print("❌ Multi-expert consultation failed")
    
    return expert_insights is not None


async def main():
    """Main test function"""
    print("=" * 60)
    print("CSV-based Product Agent Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if CSV exists
    csv_path = 'data/noah_supplements.csv'
    if not os.path.exists(csv_path):
        print(f"\n❌ CSV file not found: {csv_path}")
        print("Please ensure the CSV file is in the correct location.")
        return
    
    # Run tests
    tests = [
        ("CSV Loading", test_csv_loading),
        ("Product Search", test_product_search),
        ("Tag Search", test_tag_search),
        ("Product Recommendations", test_product_recommendations),
        ("Streaming Response", test_streaming_response),
        ("Multi-Expert Mode", test_multi_expert_mode)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            result = await test_func()
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