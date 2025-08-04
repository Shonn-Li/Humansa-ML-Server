"""
Test Product Agent with Staged Loading System
Tests the two-stage loading pattern and token optimization
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
API_URL = "http://localhost:6001/v2/humansa/chat"  # Use v2 endpoint
TEST_USER_ID = "test_product_user_001"

# Test cases for product agent
TEST_CASES = [
    {
        "id": "product_search_dha",
        "name": "搜索DHA产品",
        "query": "给孩子补充DHA，有什么推荐的产品？",
        "expected_behavior": [
            "Should search for DHA products",
            "Should load details for top 2-3 products",
            "Should include dosage information"
        ]
    },
    {
        "id": "product_sleep_aid",
        "name": "失眠产品推荐",
        "query": "最近失眠严重，有什么保健品可以帮助改善睡眠？",
        "expected_behavior": [
            "Should search for sleep-related products",
            "Should not recommend unrelated products",
            "Should include usage instructions"
        ]
    },
    {
        "id": "product_immune_boost",
        "name": "提高免疫力产品",
        "query": "想提高免疫力，推荐一些适合成人的保健品",
        "expected_behavior": [
            "Should search for immune system products",
            "Should filter for adult-suitable products",
            "Should provide multiple options"
        ]
    },
    {
        "id": "product_pregnancy",
        "name": "孕期营养补充",
        "query": "我怀孕3个月了，需要补充什么营养品？",
        "expected_behavior": [
            "Should search for pregnancy-safe products",
            "Should check contraindications",
            "Should recommend appropriate supplements"
        ]
    },
    {
        "id": "product_child_growth",
        "name": "儿童生长发育",
        "query": "5岁孩子挑食，身高偏矮，有什么产品推荐？",
        "expected_behavior": [
            "Should search for child growth products",
            "Should address both nutrition and growth",
            "Should be age-appropriate"
        ]
    },
    {
        "id": "product_elderly_health",
        "name": "老年人保健",
        "query": "给70岁的父母买保健品，主要想改善关节和记忆力",
        "expected_behavior": [
            "Should search for elderly-appropriate products",
            "Should address both joint and cognitive health",
            "Should consider safety for elderly"
        ]
    },
    {
        "id": "product_specific_id",
        "name": "特定产品查询",
        "query": "请介绍一下童年故事DHA藻油的具体信息",
        "expected_behavior": [
            "Should find specific product by name",
            "Should load complete details",
            "Should provide comprehensive information"
        ]
    },
    {
        "id": "product_comparison",
        "name": "产品对比",
        "query": "比较一下不同的DHA产品，哪个更适合2岁宝宝？",
        "expected_behavior": [
            "Should search multiple DHA products",
            "Should load details for comparison",
            "Should make age-appropriate recommendation"
        ]
    }
]

async def test_product_agent(session_id: str = None):
    """Test product agent with various queries"""
    
    import aiohttp
    results = []
    
    async with aiohttp.ClientSession() as session:
        for test_case in TEST_CASES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {test_case['name']}")
            logger.info(f"Query: {test_case['query']}")
            logger.info(f"{'='*60}")
            
            start_time = time.time()
            
            # Prepare request for v2 API
            request_data = {
                "user_id": TEST_USER_ID,
                "messages": [
                    {
                        "role": "user",
                        "content": test_case['query']
                    }
                ],
                "stream": True,
                "debug": True
            }
            
            if session_id:
                request_data["session_id"] = session_id
            
            try:
                # Make request
                async with session.post(
                    API_URL,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error {response.status}: {error_text}")
                        results.append({
                            "test": test_case['id'],
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "duration": time.time() - start_time
                        })
                        continue
                    
                    # Collect streaming response
                    full_response = ""
                    product_agent_called = False
                    products_mentioned = []
                    details_loaded = False
                    
                    async for line in response.content.iter_any():
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                
                                # Check for product agent usage
                                if 'tool_calls' in data:
                                    for tool_call in data['tool_calls']:
                                        if 'ProductAgent' in str(tool_call):
                                            product_agent_called = True
                                
                                # Check for content
                                if 'choices' in data:
                                    for choice in data['choices']:
                                        if 'delta' in choice and 'content' in choice['delta']:
                                            content = choice['delta']['content']
                                            full_response += content
                                            
                                            # Check for product mentions
                                            if 'https://shop137071643.m.youzan.com' in content:
                                                details_loaded = True
                                            
                                            # Simple product name detection
                                            product_keywords = ['DHA', '益生菌', '维生素', '钙', '锌']
                                            for keyword in product_keywords:
                                                if keyword in content and keyword not in products_mentioned:
                                                    products_mentioned.append(keyword)
                                
                            except json.JSONDecodeError:
                                continue
                    
                    # Analyze results
                    duration = time.time() - start_time
                    
                    # Check expected behaviors
                    behavior_checks = []
                    for behavior in test_case['expected_behavior']:
                        if 'search' in behavior.lower() and product_agent_called:
                            behavior_checks.append(True)
                        elif 'load details' in behavior.lower() and details_loaded:
                            behavior_checks.append(True)
                        elif 'dosage' in behavior.lower() and ('用法' in full_response or '每日' in full_response):
                            behavior_checks.append(True)
                        elif 'usage' in behavior.lower() and ('用法' in full_response or '服用' in full_response):
                            behavior_checks.append(True)
                        elif 'multiple' in behavior.lower() and len(products_mentioned) > 1:
                            behavior_checks.append(True)
                        else:
                            behavior_checks.append(False)
                    
                    success_rate = sum(behavior_checks) / len(behavior_checks) if behavior_checks else 0
                    
                    # Log results
                    logger.info(f"\nResponse Summary:")
                    logger.info(f"- Product Agent Called: {product_agent_called}")
                    logger.info(f"- Products Mentioned: {products_mentioned}")
                    logger.info(f"- Details Loaded: {details_loaded}")
                    logger.info(f"- Response Length: {len(full_response)} chars")
                    logger.info(f"- Duration: {duration:.2f}s")
                    logger.info(f"- Behavior Success Rate: {success_rate:.1%}")
                    
                    # Sample of response
                    logger.info(f"\nResponse Preview (first 500 chars):")
                    logger.info(full_response[:500] + "..." if len(full_response) > 500 else full_response)
                    
                    # Record result
                    results.append({
                        "test": test_case['id'],
                        "name": test_case['name'],
                        "status": "success" if success_rate > 0.5 else "partial",
                        "product_agent_called": product_agent_called,
                        "products_mentioned": products_mentioned,
                        "details_loaded": details_loaded,
                        "behavior_success_rate": success_rate,
                        "response_length": len(full_response),
                        "duration": duration
                    })
                    
            except Exception as e:
                logger.error(f"Exception during test: {e}")
                results.append({
                    "test": test_case['id'],
                    "status": "error",
                    "error": str(e),
                    "duration": time.time() - start_time
                })
            
            # Brief pause between tests
            await asyncio.sleep(2)
    
    return results

async def test_token_usage():
    """Test token usage optimization"""
    
    logger.info("\n" + "="*60)
    logger.info("Testing Token Usage Optimization")
    logger.info("="*60)
    
    # Import the product agent to check token estimates
    try:
        from src.humansa.v2.agents.product_agent import ProductAgent
        from llama_index.llms.openai import OpenAI
        
        # Create agent instance
        llm = OpenAI(model="gpt-4o")
        agent = ProductAgent(llm=llm)
        
        # Get token statistics
        stats = agent.get_statistics()
        
        logger.info("\nToken Usage Statistics:")
        logger.info(f"- Total Products: {stats['total_products']}")
        logger.info(f"- Categories: {len(stats['categories'])}")
        logger.info(f"- Catalog Tokens: ~{stats['token_usage']['catalog']:,}")
        logger.info(f"- Per Product Detail: ~{stats['token_usage']['per_product_detail']} tokens")
        logger.info(f"- Selected Products: {stats['selected_products']}")
        logger.info(f"- Current Total Usage: ~{stats['token_usage']['current_total']:,} tokens")
        
        # Simulate different scenarios
        scenarios = [
            {"name": "Single Product Query", "products": 1},
            {"name": "Comparison Query", "products": 3},
            {"name": "Category Browse", "products": 5},
            {"name": "Extensive Search", "products": 10}
        ]
        
        logger.info("\nToken Usage Scenarios:")
        for scenario in scenarios:
            total_tokens = stats['token_usage']['catalog'] + (scenario['products'] * stats['token_usage']['per_product_detail'])
            logger.info(f"- {scenario['name']} ({scenario['products']} products): ~{total_tokens:,} tokens")
        
        return {
            "status": "success",
            "statistics": stats,
            "scenarios": scenarios
        }
        
    except Exception as e:
        logger.error(f"Error testing token usage: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def main():
    """Run all product agent tests"""
    
    logger.info("Starting Product Agent Staged Loading Tests")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Test Environment: Port 6001")
    
    # Test token usage first
    token_results = await test_token_usage()
    
    # Run product agent tests
    test_results = await test_product_agent()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r['status'] == 'success')
    partial_tests = sum(1 for r in test_results if r['status'] == 'partial')
    failed_tests = sum(1 for r in test_results if r['status'] == 'error')
    
    logger.info(f"\nTotal Tests: {total_tests}")
    logger.info(f"Successful: {successful_tests} ({successful_tests/total_tests:.1%})")
    logger.info(f"Partial: {partial_tests} ({partial_tests/total_tests:.1%})")
    logger.info(f"Failed: {failed_tests} ({failed_tests/total_tests:.1%})")
    
    # Performance metrics
    durations = [r['duration'] for r in test_results if 'duration' in r]
    if durations:
        logger.info(f"\nPerformance:")
        logger.info(f"- Average Duration: {sum(durations)/len(durations):.2f}s")
        logger.info(f"- Min Duration: {min(durations):.2f}s")
        logger.info(f"- Max Duration: {max(durations):.2f}s")
    
    # Product agent usage
    agent_calls = sum(1 for r in test_results if r.get('product_agent_called', False))
    logger.info(f"\nProduct Agent Usage:")
    logger.info(f"- Agent Called: {agent_calls}/{total_tests} tests")
    logger.info(f"- Details Loaded: {sum(1 for r in test_results if r.get('details_loaded', False))} times")
    
    # Save results
    results_file = f"product_agent_staged_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "token_usage": token_results,
            "test_results": test_results,
            "summary": {
                "total": total_tests,
                "successful": successful_tests,
                "partial": partial_tests,
                "failed": failed_tests,
                "agent_usage_rate": agent_calls / total_tests if total_tests > 0 else 0
            }
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())