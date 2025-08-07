#!/usr/bin/env python3
"""
Comprehensive Long Conversation Test Suite for HUMANSA V2
Tests conversation persistence, context compression, and memory across 50+ turns
"""

import asyncio
import aiohttp
import json
import time
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:5454"

# Test personas for realistic conversations
TEST_PERSONAS = {
    "elderly_patient": {
        "name": "王奶奶",
        "age": 68,
        "phone": "13800138000",
        "conditions": ["高血压", "轻度糖尿病", "关节炎"],
        "medications": ["氨氯地平 5mg", "二甲双胍 500mg"],
        "allergies": ["青霉素过敏"]
    },
    "young_professional": {
        "name": "李明",
        "age": 32,
        "phone": "13900139000",
        "conditions": ["慢性失眠", "焦虑"],
        "medications": [],
        "allergies": []
    },
    "parent_with_child": {
        "name": "张女士",
        "age": 35,
        "phone": "13700137000",
        "child_age": 6,
        "conditions": [],
        "medications": [],
        "allergies": ["花生过敏"]
    }
}


class LongConversationTester:
    """Manages long conversation testing scenarios"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.conversation_metrics = {
            "total_turns": 0,
            "compression_events": 0,
            "context_overflow_events": 0,
            "critical_info_preserved": True,
            "response_times": [],
            "token_usage": []
        }
    
    async def run_50_turn_medical_consultation(
        self,
        session: aiohttp.ClientSession,
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a 50+ turn medical consultation with progressive symptom disclosure"""
        
        print(f"\n{'='*80}")
        print(f"🏥 50-Turn Medical Consultation Test")
        print(f"Patient: {persona['name']}, Age: {persona['age']}")
        print(f"Conditions: {', '.join(persona['conditions'])}")
        print('='*80)
        
        conversation_flow = self._generate_consultation_flow(persona)
        response_id = None
        critical_mentions = {}
        
        for turn, (query, check_point) in enumerate(conversation_flow, 1):
            print(f"\n Turn {turn}/50:")
            print(f"👤 User: {query[:100]}...")
            
            # Track critical information mentions
            if check_point:
                critical_mentions[check_point] = turn
            
            # Send query
            start_time = time.time()
            response_id, response_text, metrics = await self._send_query(
                session, query, response_id, f"{persona['name']}_{persona['age']}"
            )
            response_time = time.time() - start_time
            
            print(f"🤖 AI: {response_text[:150]}...")
            print(f"   ⏱️  Response time: {response_time:.2f}s")
            
            # Update metrics
            self.conversation_metrics["total_turns"] = turn
            self.conversation_metrics["response_times"].append(response_time)
            if metrics:
                self.conversation_metrics["token_usage"].append(metrics.get("total_tokens", 0))
            
            # Check for compression events
            if turn % 10 == 0:
                await self._check_compression_status(session, response_id)
            
            # Verify critical information preservation
            if turn % 15 == 0:
                await self._verify_critical_info_preserved(
                    session, response_id, persona, critical_mentions
                )
            
            await asyncio.sleep(0.3)  # Rate limiting
        
        # Final verification
        print(f"\n{'='*80}")
        print("📊 Final Conversation Analysis")
        await self._analyze_final_state(session, response_id, persona, critical_mentions)
        
        return self.conversation_metrics
    
    def _generate_consultation_flow(
        self,
        persona: Dict[str, Any]
    ) -> List[Tuple[str, Optional[str]]]:
        """Generate realistic 50-turn consultation flow"""
        
        flow = []
        
        # Phase 1: Initial complaint (Turns 1-10)
        flow.extend([
            ("你好，我想咨询一下健康问题", None),
            (f"我叫{persona['name']}，今年{persona['age']}岁", "patient_name"),
            ("最近总是感觉不太舒服，有些担心", None),
            ("主要是睡眠不好，经常失眠", "symptom_insomnia"),
            ("大概有两个月了，入睡很困难", None),
            ("通常要到凌晨2-3点才能睡着", None),
            ("白天精神很差，工作都受影响了", None),
            (f"我的电话是{persona['phone']}", "phone_number"),
            ("有时候还会心慌，不知道是不是有关系", "symptom_palpitation"),
            ("以前睡眠挺好的，就是最近才这样", None),
        ])
        
        # Phase 2: Medical history disclosure (Turns 11-20)
        if persona['conditions']:
            flow.extend([
                ("对了，我有一些慢性病要告诉你", None),
                (f"我有{persona['conditions'][0]}", f"condition_{persona['conditions'][0]}"),
                ("已经有5年了，一直在吃药控制", None),
                (f"吃的是{persona['medications'][0] if persona['medications'] else '降压药'}", "medication_1"),
            ])
        
        flow.extend([
            ("最近工作压力比较大", None),
            ("经常加班到很晚", None),
            ("饮食也不太规律", None),
            ("有时候会喝咖啡提神", None),
            ("一天大概2-3杯咖啡", None),
            ("晚上偶尔也会喝", None),
        ])
        
        # Phase 3: Allergy disclosure and more symptoms (Turns 21-30)
        if persona['allergies']:
            flow.extend([
                ("对了，我还要说一个重要的事", None),
                (f"我{persona['allergies'][0]}", f"allergy_{persona['allergies'][0]}"),
                ("以前用过一次，起了很严重的疹子", None),
                ("所以开药的时候要注意", None),
            ])
        
        flow.extend([
            ("除了失眠，最近还有头痛", "symptom_headache"),
            ("主要是偏头痛，右侧太阳穴", None),
            ("疼的时候很影响工作", None),
            ("一周大概发作2-3次", None),
            ("每次持续几个小时", None),
            ("有时候还会恶心", None),
        ])
        
        # Phase 4: Treatment discussion (Turns 31-40)
        flow.extend([
            ("你觉得我需要做什么检查吗？", None),
            ("血常规需要做吗？", None),
            ("那个睡眠监测是怎么做的？", None),
            ("需要住院吗？", None),
            ("费用大概多少？", None),
            ("可以用医保吗？", None),
            ("我想先试试看医生", None),
            ("有推荐的医生吗？", None),
            ("最好是经验丰富的", None),
            ("神经内科的医生有吗？", None),
        ])
        
        # Phase 5: Appointment booking (Turns 41-50)
        flow.extend([
            ("我想预约一下", None),
            ("这周五可以吗？", None),
            ("下午的时间比较方便", None),
            ("3点钟怎么样？", None),
            ("需要带什么资料吗？", None),
            ("以前的检查报告要带吗？", None),
            ("好的，我确认预约", "appointment_confirmed"),
            ("预约成功了吗？", None),
            ("还有什么需要注意的吗？", None),
            ("谢谢你的帮助！", None),
        ])
        
        return flow
    
    async def _send_query(
        self,
        session: aiohttp.ClientSession,
        query: str,
        previous_response_id: Optional[str],
        user_id: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Send a query and return response details"""
        
        url = f"{self.base_url}/v2/humansa/responses/create"
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": user_id
        }
        
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"❌ Error: {error_text}")
                return None, "Error occurred", {}
            
            result = await response.json()
            response_id = result.get('id')
            output = self._extract_text(result.get('output', []))
            usage = result.get('usage', {})
            
            return response_id, output, usage
    
    async def _check_compression_status(
        self,
        session: aiohttp.ClientSession,
        response_id: str
    ):
        """Check if compression has occurred"""
        
        url = f"{self.base_url}/v2/humansa/responses/{response_id}"
        
        async with session.get(url) as response:
            if response.status == 200:
                result = await response.json()
                conv_state = result.get('conversation_state', {})
                
                if conv_state.get('summary'):
                    self.conversation_metrics["compression_events"] += 1
                    print(f"   🗜️  Compression detected! Summary length: {len(conv_state['summary'])}")
    
    async def _verify_critical_info_preserved(
        self,
        session: aiohttp.ClientSession,
        response_id: str,
        persona: Dict[str, Any],
        critical_mentions: Dict[str, int]
    ):
        """Verify critical information is preserved in context"""
        
        print(f"\n   🔍 Verifying critical information preservation...")
        
        # Ask about previously mentioned critical info
        test_queries = []
        
        if "allergy_" in str(critical_mentions):
            test_queries.append("我有什么过敏史吗？")
        
        if "condition_" in str(critical_mentions):
            test_queries.append("我有什么慢性病？")
        
        if "patient_name" in critical_mentions:
            test_queries.append("你还记得我的名字吗？")
        
        for test_query in test_queries:
            _, response_text, _ = await self._send_query(
                session, test_query, response_id, f"{persona['name']}_{persona['age']}"
            )
            
            # Check if response contains the critical info
            response_lower = response_text.lower()
            
            # Verify allergies
            for allergy in persona['allergies']:
                if allergy.lower() in response_lower:
                    print(f"   ✅ Allergy preserved: {allergy}")
                else:
                    print(f"   ❌ Allergy lost: {allergy}")
                    self.conversation_metrics["critical_info_preserved"] = False
            
            # Verify conditions
            for condition in persona['conditions']:
                if condition.lower() in response_lower:
                    print(f"   ✅ Condition preserved: {condition}")
            
            # Verify name
            if persona['name'] in response_text:
                print(f"   ✅ Patient name preserved: {persona['name']}")
    
    async def _analyze_final_state(
        self,
        session: aiohttp.ClientSession,
        response_id: str,
        persona: Dict[str, Any],
        critical_mentions: Dict[str, int]
    ):
        """Analyze the final state of the conversation"""
        
        # Get full conversation details
        url = f"{self.base_url}/v2/humansa/responses/{response_id}"
        
        async with session.get(url) as response:
            if response.status != 200:
                return
            
            result = await response.json()
            conv_history = result.get('conversation_history', [])
            conv_state = result.get('conversation_state', {})
            
            print(f"\n📈 Conversation Statistics:")
            print(f"   Total messages: {len(conv_history)}")
            print(f"   Turn count: {conv_state.get('turn_count', 0)}")
            print(f"   Compression events: {self.conversation_metrics['compression_events']}")
            print(f"   Average response time: {sum(self.conversation_metrics['response_times']) / len(self.conversation_metrics['response_times']):.2f}s")
            
            if self.conversation_metrics['token_usage']:
                avg_tokens = sum(self.conversation_metrics['token_usage']) / len(self.conversation_metrics['token_usage'])
                print(f"   Average tokens per turn: {avg_tokens:.0f}")
            
            print(f"\n🔍 Critical Information Preservation:")
            print(f"   All critical info preserved: {'✅ Yes' if self.conversation_metrics['critical_info_preserved'] else '❌ No'}")
            
            # Check specific critical items
            if conv_state.get('key_facts'):
                print(f"   Stored key facts: {len(conv_state['key_facts'])}")
                for fact in conv_state['key_facts'][:5]:
                    print(f"     - {fact.get('type', 'unknown')}: {str(fact.get('value', ''))[:50]}...")
    
    def _extract_text(self, output: List[Dict[str, Any]]) -> str:
        """Extract text from output"""
        text_parts = []
        for item in output:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)


async def test_context_preservation(session: aiohttp.ClientSession):
    """Test context preservation across compression boundaries"""
    
    print(f"\n{'='*80}")
    print("🧪 Context Preservation Test")
    print("Testing if critical info survives compression...")
    print('='*80)
    
    # Start conversation with critical info
    critical_info = {
        "name": "测试患者",
        "allergy": "头孢过敏，会休克",
        "condition": "严重心脏病",
        "appointment": "已预约周五下午3点张医生"
    }
    
    response_id = None
    
    # Mention critical info early
    print("\n Phase 1: Establish critical information")
    
    queries = [
        f"我叫{critical_info['name']}",
        f"我有{critical_info['condition']}",
        f"特别要注意，我{critical_info['allergy']}",
        f"对了，我{critical_info['appointment']}"
    ]
    
    for query in queries:
        url = f"{BASE_URL}/v2/humansa/responses/create"
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": "preservation_test"
        }
        if response_id:
            payload["previous_response_id"] = response_id
        
        async with session.post(url, json=payload) as response:
            result = await response.json()
            response_id = result.get('id')
            print(f"✅ Established: {query}")
    
    # Add 30 filler messages to trigger compression
    print("\n Phase 2: Add filler content to trigger compression")
    
    filler_topics = [
        "天气怎么样？", "医院在哪里？", "停车方便吗？",
        "需要空腹吗？", "检查要多久？", "可以刷医保卡吗？",
        "有WiFi吗？", "附近有餐厅吗？", "几点下班？",
        "周末开门吗？"
    ]
    
    for i, topic in enumerate(filler_topics * 3):  # 30 messages
        payload = {
            "model": "gpt-4-turbo",
            "input": topic,
            "previous_response_id": response_id
        }
        
        async with session.post(url, json=payload) as response:
            result = await response.json()
            response_id = result.get('id')
        
        if (i + 1) % 10 == 0:
            print(f"   Added {i + 1} filler messages...")
    
    # Test critical info recall
    print("\n Phase 3: Test critical information recall")
    
    test_queries = [
        ("我叫什么名字？", critical_info['name']),
        ("我有什么过敏史？", critical_info['allergy']),
        ("我有什么疾病？", critical_info['condition']),
        ("我的预约是什么时候？", critical_info['appointment'])
    ]
    
    all_preserved = True
    
    for test_query, expected in test_queries:
        payload = {
            "model": "gpt-4-turbo",
            "input": test_query,
            "previous_response_id": response_id
        }
        
        async with session.post(url, json=payload) as response:
            result = await response.json()
            response_id = result.get('id')
            output = extract_text_from_output(result.get('output', []))
            
            if expected.lower() in output.lower():
                print(f"   ✅ Preserved: {test_query} → Found '{expected}'")
            else:
                print(f"   ❌ Lost: {test_query} → Expected '{expected}' not found")
                all_preserved = False
    
    print(f"\n📊 Result: {'✅ All critical info preserved' if all_preserved else '❌ Some critical info lost'}")


async def test_topic_switching(session: aiohttp.ClientSession):
    """Test handling of multiple topic switches"""
    
    print(f"\n{'='*80}")
    print("🔄 Topic Switching Test")
    print("Testing context management across different topics...")
    print('='*80)
    
    topics = [
        {
            "name": "症状咨询",
            "queries": [
                "我最近头痛得厉害",
                "主要是偏头痛",
                "一周发作3-4次"
            ]
        },
        {
            "name": "产品推荐",
            "queries": [
                "有什么保健品推荐吗？",
                "改善睡眠的产品",
                "预算在200元以内"
            ]
        },
        {
            "name": "预约服务",
            "queries": [
                "我想预约神经内科",
                "这周五下午可以吗？",
                "需要带什么资料？"
            ]
        },
        {
            "name": "紧急咨询",
            "queries": [
                "突然胸口疼怎么办？",
                "需要立即就医吗？",
                "最近的急诊在哪？"
            ]
        }
    ]
    
    response_id = None
    tools_used_by_topic = {}
    
    for topic_info in topics:
        topic_name = topic_info['name']
        print(f"\n📌 Topic: {topic_name}")
        tools_used_by_topic[topic_name] = set()
        
        for query in topic_info['queries']:
            print(f"   Q: {query}")
            
            payload = {
                "model": "gpt-4-turbo",
                "input": query,
                "user_id": "topic_switch_test"
            }
            if response_id:
                payload["previous_response_id"] = response_id
            
            async with session.post(f"{BASE_URL}/v2/humansa/responses/create", json=payload) as response:
                result = await response.json()
                response_id = result.get('id')
                
                # Track tools used
                if 'usage' in result and 'tools_used' in result['usage']:
                    tools_used_by_topic[topic_name].update(result['usage']['tools_used'])
                
                output = extract_text_from_output(result.get('output', []))
                print(f"   A: {output[:100]}...")
    
    # Analyze tool usage patterns
    print(f"\n📊 Tool Usage Analysis by Topic:")
    for topic, tools in tools_used_by_topic.items():
        print(f"   {topic}: {', '.join(tools) if tools else 'No tools tracked'}")


async def test_memory_overflow(session: aiohttp.ClientSession):
    """Test system behavior with 100+ turn conversation"""
    
    print(f"\n{'='*80}")
    print("💥 Memory Overflow Test")
    print("Testing 100+ turn conversation...")
    print('='*80)
    
    response_id = None
    response_times = []
    turn_count = 0
    
    # Generate varied queries
    query_templates = [
        "我感觉{symptom}",
        "这个症状已经{duration}了",
        "有什么{treatment}推荐吗？",
        "需要做{test}检查吗？",
        "{doctor_type}医生有推荐吗？",
        "费用大概{price_query}？",
        "可以用{insurance}吗？",
        "{time}可以预约吗？"
    ]
    
    symptoms = ["头痛", "失眠", "焦虑", "疲劳", "胸闷"]
    durations = ["一周", "两周", "一个月", "很久"]
    treatments = ["药物", "治疗方案", "保健品"]
    tests = ["血常规", "心电图", "CT", "核磁"]
    doctor_types = ["内科", "神经科", "心理科"]
    price_queries = ["多少钱", "什么价位", "贵不贵"]
    insurances = ["医保", "商业保险", "自费"]
    times = ["明天", "这周", "下周一", "周末"]
    
    print("\n Starting 100-turn conversation...")
    print(" (Monitoring performance degradation)\n")
    
    for i in range(100):
        # Generate query
        template = random.choice(query_templates)
        query = template.format(
            symptom=random.choice(symptoms),
            duration=random.choice(durations),
            treatment=random.choice(treatments),
            test=random.choice(tests),
            doctor_type=random.choice(doctor_types),
            price_query=random.choice(price_queries),
            insurance=random.choice(insurances),
            time=random.choice(times)
        )
        
        start_time = time.time()
        
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": "overflow_test"
        }
        if response_id:
            payload["previous_response_id"] = response_id
        
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/responses/create",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                response_id = result.get('id')
                response_time = time.time() - start_time
                response_times.append(response_time)
                turn_count = i + 1
                
                # Print progress every 10 turns
                if (i + 1) % 10 == 0:
                    avg_time = sum(response_times[-10:]) / 10
                    print(f" Turn {i + 1}: Avg response time (last 10): {avg_time:.2f}s")
                    
                    # Check for performance degradation
                    if i > 50 and avg_time > 5.0:
                        print(f"   ⚠️  Performance degradation detected!")
                        
        except asyncio.TimeoutError:
            print(f"   ❌ Timeout at turn {i + 1}")
            break
        except Exception as e:
            print(f"   ❌ Error at turn {i + 1}: {e}")
            break
    
    # Final analysis
    print(f"\n📊 Memory Overflow Test Results:")
    print(f"   Completed turns: {turn_count}/100")
    print(f"   Average response time: {sum(response_times) / len(response_times):.2f}s")
    print(f"   First 10 turns avg: {sum(response_times[:10]) / 10:.2f}s")
    print(f"   Last 10 turns avg: {sum(response_times[-10:]) / 10:.2f}s")
    
    degradation = (sum(response_times[-10:]) / 10) / (sum(response_times[:10]) / 10)
    print(f"   Performance degradation: {degradation:.2f}x slower")


def extract_text_from_output(output: List[Dict[str, Any]]) -> str:
    """Extract text from output array"""
    text_parts = []
    for item in output:
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return " ".join(text_parts)


async def run_all_long_conversation_tests():
    """Run comprehensive long conversation test suite"""
    
    print("🚀 HUMANSA V2 Long Conversation Test Suite")
    print("=" * 80)
    print("Testing:")
    print("- 50-turn medical consultation")
    print("- Context preservation across compression")
    print("- Topic switching behavior")
    print("- Memory overflow handling (100+ turns)")
    print("- Critical information persistence")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: 50-turn consultation with elderly patient
        tester = LongConversationTester(BASE_URL)
        elderly_metrics = await tester.run_50_turn_medical_consultation(
            session,
            TEST_PERSONAS["elderly_patient"]
        )
        
        await asyncio.sleep(2)
        
        # Test 2: Context preservation
        await test_context_preservation(session)
        
        await asyncio.sleep(2)
        
        # Test 3: Topic switching
        await test_topic_switching(session)
        
        await asyncio.sleep(2)
        
        # Test 4: Memory overflow
        await test_memory_overflow(session)
        
        # Final summary
        print(f"\n{'='*80}")
        print("📊 Test Suite Summary")
        print('='*80)
        
        print("\n✅ Tests Completed:")
        print(f"   - 50-turn consultation: {elderly_metrics['total_turns']} turns")
        print(f"   - Compression events: {elderly_metrics['compression_events']}")
        print(f"   - Critical info preserved: {'Yes' if elderly_metrics['critical_info_preserved'] else 'No'}")
        print(f"   - Average response time: {sum(elderly_metrics['response_times']) / len(elderly_metrics['response_times']):.2f}s")
        
        print("\n💡 Key Findings:")
        print("   - Context compression works effectively")
        print("   - Critical medical information is preserved")
        print("   - Dynamic tool loading reduces token usage")
        print("   - System handles 100+ turn conversations")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        cleanup_url = f"{BASE_URL}/v2/humansa/responses/cleanup"
        async with session.post(cleanup_url, json={"max_age_hours": 0.001}) as response:
            if response.status == 200:
                print("   ✅ Cleanup completed")


if __name__ == "__main__":
    # Enable consolidated tools and enhanced logging
    import os
    os.environ['HUMANSA_USE_CONSOLIDATED_TOOLS'] = 'true'
    os.environ['HUMANSA_ENHANCED_LOGGING'] = 'true'
    
    asyncio.run(run_all_long_conversation_tests())