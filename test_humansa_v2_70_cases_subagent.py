#!/usr/bin/env python3
"""
Test HUMANSA V2 with Sub-Agent Architecture
Runs 70 comprehensive test cases to validate the new architecture
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:6001"
API_ENDPOINT = f"{BASE_URL}/v2/humansa/chat"
USE_SUBAGENT_ARCH = True  # Flag to indicate we're testing sub-agent architecture

# Test categories with cases
TEST_CATEGORIES = {
    "产品推荐": [
        ("我想买一些维生素C，有什么推荐吗？", ["维生素C", "推荐", "价格"]),
        ("有什么提高免疫力的保健品？", ["免疫力", "保健品", "推荐"]),
        ("血压计哪个牌子好？", ["血压计", "品牌", "推荐"]),
        ("老年人适合吃什么营养品？", ["老年人", "营养品", "适合"]),
        ("孕妇可以吃什么保健品？", ["孕妇", "保健品", "安全"]),
        ("儿童补钙产品推荐", ["儿童", "补钙", "产品"]),
        ("失眠吃什么保健品好？", ["失眠", "保健品", "改善"]),
        ("护肤品有什么推荐？", ["护肤", "推荐", "产品"]),
        ("减肥产品哪个效果好？", ["减肥", "产品", "效果"]),
        ("眼睛疲劳吃什么好？", ["眼睛", "疲劳", "保健"])
    ],
    
    "预约挂号": [
        ("我想预约心内科医生", ["预约", "心内科", "医生"]),
        ("帮我查一下明天有哪些医生可以预约", ["查询", "明天", "预约"]),
        ("取消我的预约", ["取消", "预约"]),
        ("改期我的预约到下周", ["改期", "预约", "下周"]),
        ("儿科最早什么时候可以预约？", ["儿科", "最早", "预约"]),
        ("王医生明天有号吗？", ["王医生", "明天", "号"]),
        ("我想做体检，怎么预约？", ["体检", "预约", "流程"]),
        ("皮肤科专家门诊怎么挂？", ["皮肤科", "专家", "挂号"]),
        ("产检需要提前多久预约？", ["产检", "提前", "预约"]),
        ("可以帮我预约中医科吗？", ["预约", "中医科"])
    ],
    
    "症状分析": [
        ("我头痛发烧，是感冒了吗？", ["头痛", "发烧", "感冒"]),
        ("胸口疼痛，呼吸困难", ["胸口", "疼痛", "呼吸困难", "120"]),
        ("最近总是失眠，怎么办？", ["失眠", "建议", "改善"]),
        ("孩子发烧39度，需要去医院吗？", ["孩子", "发烧", "39度", "医院"]),
        ("腹痛拉肚子，可能是什么原因？", ["腹痛", "拉肚子", "原因"]),
        ("咳嗽有痰，吃什么药？", ["咳嗽", "有痰", "用药"]),
        ("皮肤过敏很痒怎么办？", ["皮肤", "过敏", "痒"]),
        ("眼睛红肿疼痛", ["眼睛", "红肿", "疼痛"]),
        ("关节疼痛是关节炎吗？", ["关节", "疼痛", "关节炎"]),
        ("头晕恶心想吐", ["头晕", "恶心", "呕吐"])
    ],
    
    "紧急情况": [
        ("突然晕倒了怎么办", ["晕倒", "急救", "120"]),
        ("心脏病发作的症状", ["心脏病", "症状", "急救"]),
        ("中风的早期症状有哪些", ["中风", "症状", "识别"]),
        ("烫伤了怎么处理", ["烫伤", "处理", "急救"]),
        ("食物中毒怎么办", ["食物中毒", "处理", "急救"]),
        ("突发哮喘如何急救", ["哮喘", "急救", "处理"]),
        ("癫痫发作时该怎么做", ["癫痫", "发作", "急救"]),
        ("严重过敏反应怎么办", ["过敏", "严重", "急救"]),
        ("溺水急救步骤", ["溺水", "急救", "步骤"]),
        ("骨折了怎么处理", ["骨折", "处理", "急救"])
    ],
    
    "用药指导": [
        ("阿司匹林有什么副作用？", ["阿司匹林", "副作用", "注意"]),
        ("感冒药可以和退烧药一起吃吗？", ["感冒药", "退烧药", "同服"]),
        ("高血压药什么时候吃最好？", ["高血压药", "服用时间", "最佳"]),
        ("抗生素要吃够疗程吗？", ["抗生素", "疗程", "坚持"]),
        ("糖尿病药物有哪些？", ["糖尿病", "药物", "种类"]),
        ("止痛药会上瘾吗？", ["止痛药", "上瘾", "安全"]),
        ("中药和西药可以一起吃吗？", ["中药", "西药", "同服"]),
        ("过期药物还能吃吗？", ["过期", "药物", "安全"]),
        ("儿童用药注意事项", ["儿童", "用药", "注意"]),
        ("孕妇禁用哪些药物？", ["孕妇", "禁用", "药物"])
    ],
    
    "健康咨询": [
        ("如何预防高血压？", ["预防", "高血压", "方法"]),
        ("糖尿病饮食注意什么？", ["糖尿病", "饮食", "注意"]),
        ("怎样提高睡眠质量？", ["提高", "睡眠", "质量"]),
        ("减肥的正确方法", ["减肥", "正确", "方法"]),
        ("如何增强免疫力？", ["增强", "免疫力", "方法"]),
        ("办公室如何护眼？", ["办公室", "护眼", "方法"]),
        ("老年人如何补钙？", ["老年人", "补钙", "方法"]),
        ("备孕需要注意什么？", ["备孕", "注意", "准备"]),
        ("产后恢复建议", ["产后", "恢复", "建议"]),
        ("儿童营养搭配", ["儿童", "营养", "搭配"])
    ],
    
    "保险政策": [
        ("医保可以报销哪些项目？", ["医保", "报销", "项目"]),
        ("商业保险和医保的区别", ["商业保险", "医保", "区别"]),
        ("门诊可以用医保吗？", ["门诊", "医保", "使用"]),
        ("异地就医怎么报销？", ["异地", "就医", "报销"]),
        ("慢性病医保政策", ["慢性病", "医保", "政策"]),
        ("大病医保怎么申请？", ["大病", "医保", "申请"]),
        ("医保卡丢了怎么办？", ["医保卡", "丢失", "补办"]),
        ("住院报销比例是多少？", ["住院", "报销", "比例"]),
        ("体检能用医保吗？", ["体检", "医保", "使用"]),
        ("医保定点医院有哪些？", ["医保", "定点", "医院"])
    ]
}


async def send_chat_request(session: aiohttp.ClientSession, query: str, user_id: str = "test_user") -> Tuple[str, float, Dict]:
    """Send a chat request and return response, time taken, and full response data"""
    
    payload = {
        "messages": [
            {"role": "user", "content": query}
        ],
        "user_id": user_id,
        "stream": False,
        "debug": True  # Enable debug for sub-agent visibility
    }
    
    start_time = time.time()
    
    try:
        async with session.post(API_ENDPOINT, json=payload) as response:
            response_time = time.time() - start_time
            
            if response.status == 200:
                data = await response.json()
                
                # Extract response text
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    # Handle case where content is a dict with metadata
                    if isinstance(content, dict):
                        # Extract actual content from response agent output
                        if "output" in content and len(content["output"]) > 0:
                            actual_content = content["output"][0].get("content", "")
                        else:
                            actual_content = str(content)
                    else:
                        actual_content = content
                    return actual_content, response_time, data
                else:
                    return f"Error: Invalid response format", response_time, data
            else:
                error_text = await response.text()
                return f"Error {response.status}: {error_text}", response_time, {}
                
    except Exception as e:
        response_time = time.time() - start_time
        return f"Exception: {str(e)}", response_time, {}


def evaluate_response(response: str, expected_keywords: List[str], query: str) -> Dict[str, Any]:
    """Evaluate response quality based on expected keywords and criteria"""
    
    evaluation = {
        "keywords_found": [],
        "keywords_missing": [],
        "has_identity": False,
        "is_relevant": False,
        "has_emergency_120": False,
        "response_quality": "unknown",
        "agent_used": "unknown"
    }
    
    # Check keywords
    response_lower = response.lower()
    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            evaluation["keywords_found"].append(keyword)
        else:
            evaluation["keywords_missing"].append(keyword)
    
    # Check identity
    identity_markers = ["小诺", "诺亚新舟", "健康医疗助理"]
    evaluation["has_identity"] = any(marker in response for marker in identity_markers)
    
    # Check relevance
    evaluation["is_relevant"] = len(evaluation["keywords_found"]) >= len(expected_keywords) * 0.5
    
    # Check emergency response
    if any(emergency in query for emergency in ["胸口疼痛", "呼吸困难", "晕倒", "中风"]):
        evaluation["has_emergency_120"] = "120" in response or "急救" in response
    
    # Determine which agent was likely used based on response patterns
    if any(keyword in response_lower for keyword in ["产品", "保健品", "推荐", "价格", "商城"]):
        evaluation["agent_used"] = "product"
    elif any(keyword in response_lower for keyword in ["预约", "挂号", "排班", "号源"]):
        evaluation["agent_used"] = "appointment"
    elif any(keyword in response_lower for keyword in ["症状", "诊断", "疾病", "120"]):
        evaluation["agent_used"] = "clinical"
    elif any(keyword in response_lower for keyword in ["药物", "用药", "副作用", "药品"]):
        evaluation["agent_used"] = "medication"
    else:
        evaluation["agent_used"] = "general"
    
    # Overall quality score
    quality_score = 0
    if evaluation["is_relevant"]:
        quality_score += 40
    if evaluation["has_identity"]:
        quality_score += 20
    if evaluation["keywords_found"]:
        quality_score += 20 * (len(evaluation["keywords_found"]) / len(expected_keywords))
    if evaluation["has_emergency_120"] or not any(emergency in query for emergency in ["胸口疼痛", "呼吸困难"]):
        quality_score += 20
    
    if quality_score >= 80:
        evaluation["response_quality"] = "excellent"
    elif quality_score >= 60:
        evaluation["response_quality"] = "good"
    elif quality_score >= 40:
        evaluation["response_quality"] = "fair"
    else:
        evaluation["response_quality"] = "poor"
    
    return evaluation


async def run_test_suite():
    """Run the complete test suite"""
    
    print(f"\n{'='*80}")
    print(f"HUMANSA V2 Sub-Agent Architecture Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing {sum(len(cases) for cases in TEST_CATEGORIES.values())} cases across {len(TEST_CATEGORIES)} categories")
    print(f"{'='*80}\n")
    
    # Check if server is running
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
                if response.status != 200:
                    print("❌ Server is not running! Please start the server first.")
                    return
        except:
            print("❌ Cannot connect to server at", BASE_URL)
            print("Please run: ./run_humansa_test_subagent.sh")
            return
    
    # Run tests
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "by_agent": {
            "product": 0,
            "appointment": 0,
            "clinical": 0,
            "medication": 0,
            "general": 0,
            "unknown": 0
        },
        "response_times": [],
        "errors": []
    }
    
    async with aiohttp.ClientSession() as session:
        for category, test_cases in TEST_CATEGORIES.items():
            print(f"\n📁 Testing Category: {category}")
            print("-" * 60)
            
            category_results = {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
            
            for i, (query, keywords) in enumerate(test_cases, 1):
                results["total"] += 1
                category_results["total"] += 1
                
                print(f"\n[{i}/{len(test_cases)}] Query: {query}")
                
                # Send request
                response, response_time, full_data = await send_chat_request(session, query)
                results["response_times"].append(response_time)
                
                # Evaluate response
                evaluation = evaluate_response(response, keywords, query)
                results["by_agent"][evaluation["agent_used"]] += 1
                
                # Print results
                print(f"⏱️  Response Time: {response_time:.2f}s")
                print(f"🤖 Agent Used: {evaluation['agent_used']}")
                print(f"📝 Response Quality: {evaluation['response_quality']}")
                print(f"✓ Keywords Found: {evaluation['keywords_found']}")
                print(f"✗ Keywords Missing: {evaluation['keywords_missing']}")
                print(f"🆔 Has Identity: {'✓' if evaluation['has_identity'] else '✗'}")
                
                # Determine pass/fail
                if evaluation["response_quality"] in ["excellent", "good"] and evaluation["is_relevant"]:
                    results["passed"] += 1
                    category_results["passed"] += 1
                    print(f"✅ PASSED")
                else:
                    results["failed"] += 1
                    category_results["failed"] += 1
                    print(f"❌ FAILED")
                    results["errors"].append({
                        "category": category,
                        "query": query,
                        "evaluation": evaluation
                    })
                
                # Show part of response
                print(f"Response Preview: {response[:200]}...")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            results["by_category"][category] = category_results
            
            # Category summary
            print(f"\n📊 {category} Summary: {category_results['passed']}/{category_results['total']} passed")
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"FINAL TEST SUMMARY - Sub-Agent Architecture")
    print(f"{'='*80}")
    
    print(f"\n📈 Overall Results:")
    print(f"   Total Tests: {results['total']}")
    print(f"   Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"   Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    
    print(f"\n📁 Results by Category:")
    for category, cat_results in results["by_category"].items():
        print(f"   {category}: {cat_results['passed']}/{cat_results['total']} passed")
    
    print(f"\n🤖 Agent Usage Distribution:")
    for agent, count in results["by_agent"].items():
        percentage = (count / results['total'] * 100) if results['total'] > 0 else 0
        print(f"   {agent}: {count} ({percentage:.1f}%)")
    
    if results["response_times"]:
        avg_time = sum(results["response_times"]) / len(results["response_times"])
        print(f"\n⏱️  Performance:")
        print(f"   Average Response Time: {avg_time:.2f}s")
        print(f"   Min Response Time: {min(results['response_times']):.2f}s")
        print(f"   Max Response Time: {max(results['response_times']):.2f}s")
    
    if results["errors"]:
        print(f"\n❌ Failed Tests Summary:")
        for error in results["errors"][:10]:  # Show first 10 errors
            print(f"   - [{error['category']}] {error['query']}")
            print(f"     Quality: {error['evaluation']['response_quality']}, Agent: {error['evaluation']['agent_used']}")
    
    # Success criteria
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"\n{'🎉 TEST SUITE PASSED!' if success_rate >= 80 else '⚠️ TEST SUITE NEEDS IMPROVEMENT'}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Save detailed results
    with open('test_results_subagent.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Detailed results saved to test_results_subagent.json")


def main():
    """Main entry point"""
    print("🚀 Starting HUMANSA V2 Sub-Agent Architecture Test Suite")
    print("⚠️  Make sure the server is running with sub-agent architecture enabled!")
    print("   Run: ./run_humansa_test_subagent.sh")
    
    asyncio.run(run_test_suite())


if __name__ == "__main__":
    main()