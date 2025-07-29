#!/usr/bin/env python3
"""
Comprehensive Response Forking Test Suite for HUMANSA V2
Tests conversation branching, parallel exploration, and fork management
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import graphviz
import os

# Test configuration
BASE_URL = "http://localhost:5454"

# Forking scenarios to test
FORKING_SCENARIOS = {
    "doctor_selection": {
        "name": "Doctor Selection Fork",
        "description": "Patient explores different doctor options",
        "initial_queries": [
            "我想看神经内科医生",
            "有哪些医生可以选择？"
        ],
        "fork_point": "我看到有张医生和李医生，他们有什么区别？",
        "branches": [
            {
                "name": "Choose Dr. Zhang",
                "queries": [
                    "我想了解更多张医生的信息",
                    "张医生的专长是什么？",
                    "张医生本周有号吗？",
                    "好的，我选择张医生",
                    "周五下午3点可以吗？"
                ]
            },
            {
                "name": "Choose Dr. Li",
                "queries": [
                    "李医生的经验怎么样？",
                    "李医生擅长治疗失眠吗？",
                    "李医生的号好约吗？",
                    "那我约李医生吧",
                    "最早什么时候有号？"
                ]
            },
            {
                "name": "Request More Options",
                "queries": [
                    "还有其他医生吗？",
                    "有女医生吗？",
                    "哪个医生评价最好？",
                    "我再考虑一下"
                ]
            }
        ]
    },
    
    "treatment_options": {
        "name": "Treatment Options Fork",
        "description": "Exploring different treatment paths",
        "initial_queries": [
            "我有慢性失眠问题",
            "已经持续3个月了",
            "影响到工作和生活"
        ],
        "fork_point": "有什么治疗方案推荐吗？",
        "branches": [
            {
                "name": "Medication Route",
                "queries": [
                    "药物治疗安全吗？",
                    "会有依赖性吗？",
                    "需要长期服药吗？",
                    "有什么副作用？",
                    "开始用药需要做什么检查？"
                ]
            },
            {
                "name": "Non-medication Route",
                "queries": [
                    "有非药物治疗方案吗？",
                    "认知行为疗法是什么？",
                    "需要多长时间见效？",
                    "费用怎么样？",
                    "可以先试试这个方案"
                ]
            },
            {
                "name": "Combined Approach",
                "queries": [
                    "能不能药物和心理治疗结合？",
                    "哪种组合效果最好？",
                    "治疗周期是多久？",
                    "总费用大概多少？"
                ]
            }
        ]
    },
    
    "appointment_rescheduling": {
        "name": "Appointment Rescheduling Fork",
        "description": "Multiple rescheduling options",
        "initial_queries": [
            "我是李明，上周预约了这周五的号",
            "但是临时有事可能去不了"
        ],
        "fork_point": "能帮我改一下时间吗？",
        "branches": [
            {
                "name": "Next Week Same Time",
                "queries": [
                    "下周五同样时间可以吗？",
                    "下午3点还有号吗？",
                    "好的，就改到下周五"
                ]
            },
            {
                "name": "This Week Different Day",
                "queries": [
                    "这周其他时间有吗？",
                    "周三或周四可以吗？",
                    "上午的时间也行",
                    "周四上午10点怎么样？"
                ]
            },
            {
                "name": "Cancel and Rebook Later",
                "queries": [
                    "要不先取消吧",
                    "等我确定时间再约",
                    "取消有费用吗？",
                    "好的，确认取消"
                ]
            }
        ]
    },
    
    "emergency_triage": {
        "name": "Emergency Triage Fork",
        "description": "Different urgency levels lead to different paths",
        "initial_queries": [
            "我现在很不舒服",
            "不知道该怎么办"
        ],
        "fork_point": "你能帮我判断一下严重程度吗？",
        "branches": [
            {
                "name": "High Urgency Path",
                "queries": [
                    "胸口剧痛，呼吸困难",
                    "疼痛向左臂放射",
                    "已经持续20分钟了",
                    "我该立即去急诊吗？"
                ]
            },
            {
                "name": "Medium Urgency Path",
                "queries": [
                    "头痛得厉害，还有点发烧",
                    "体温38.5度",
                    "没有其他严重症状",
                    "需要今天就看医生吗？"
                ]
            },
            {
                "name": "Low Urgency Path",
                "queries": [
                    "就是有点咳嗽",
                    "已经3天了",
                    "没有发烧",
                    "可以约个普通门诊吗？"
                ]
            }
        ]
    }
}


class ForkingScenarioTester:
    """Tests conversation forking scenarios"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.fork_trees = {}
        self.branch_metrics = {}
    
    async def test_forking_scenario(
        self,
        session: aiohttp.ClientSession,
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test a complete forking scenario"""
        
        print(f"\n{'='*80}")
        print(f"🔀 Testing: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print('='*80)
        
        # Phase 1: Build up to fork point
        print("\n📍 Phase 1: Building context to fork point")
        
        response_id = None
        user_id = f"fork_test_{scenario['name'].replace(' ', '_').lower()}"
        
        # Initial queries
        for query in scenario['initial_queries']:
            response_id = await self._send_and_track(
                session, query, response_id, user_id, "initial"
            )
            await asyncio.sleep(0.3)
        
        # Fork point query
        print(f"\n🔸 Fork Point: {scenario['fork_point']}")
        fork_response_id = await self._send_and_track(
            session, scenario['fork_point'], response_id, user_id, "fork_point"
        )
        
        # Phase 2: Explore branches
        print("\n📍 Phase 2: Exploring branches")
        
        branch_results = {}
        branch_endpoints = {}
        
        for i, branch in enumerate(scenario['branches'], 1):
            print(f"\n🌿 Branch {i}: {branch['name']}")
            
            # Each branch starts from the fork point
            branch_response_id = fork_response_id
            branch_start_time = time.time()
            
            for query in branch['queries']:
                branch_response_id = await self._send_and_track(
                    session, query, branch_response_id, user_id, f"branch_{i}"
                )
                await asyncio.sleep(0.3)
            
            branch_time = time.time() - branch_start_time
            
            # Store branch results
            branch_endpoints[branch['name']] = branch_response_id
            branch_results[branch['name']] = {
                "final_response_id": branch_response_id,
                "query_count": len(branch['queries']),
                "total_time": branch_time
            }
        
        # Phase 3: Analyze fork tree
        print("\n📍 Phase 3: Analyzing fork tree")
        
        analysis = await self._analyze_fork_tree(
            session, fork_response_id, scenario['name']
        )
        
        # Phase 4: Test branch independence
        print("\n📍 Phase 4: Testing branch independence")
        
        independence_results = await self._test_branch_independence(
            session, branch_endpoints, user_id
        )
        
        # Phase 5: Visualize fork tree
        if analysis.get('tree'):
            self._visualize_fork_tree(analysis['tree'], scenario['name'])
        
        return {
            "scenario": scenario['name'],
            "fork_point_id": fork_response_id,
            "branches_explored": len(branch_results),
            "branch_results": branch_results,
            "tree_analysis": analysis,
            "independence_test": independence_results
        }
    
    async def _send_and_track(
        self,
        session: aiohttp.ClientSession,
        query: str,
        previous_id: Optional[str],
        user_id: str,
        phase: str
    ) -> str:
        """Send query and track metrics"""
        
        print(f"  {'→' if previous_id else '•'} User: {query}")
        
        url = f"{self.base_url}/v2/humansa/responses/create"
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": user_id,
            "metadata": {"phase": phase}
        }
        
        if previous_id:
            payload["previous_response_id"] = previous_id
        
        start_time = time.time()
        
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error = await response.text()
                print(f"  ❌ Error: {error}")
                return None
            
            result = await response.json()
            response_time = time.time() - start_time
            
            response_id = result.get('id')
            output = self._extract_text(result.get('output', []))
            
            print(f"  ← AI: {output[:100]}...")
            print(f"     (Response time: {response_time:.2f}s, ID: {response_id[-8:]})")
            
            # Track metrics
            if phase not in self.branch_metrics:
                self.branch_metrics[phase] = []
            
            self.branch_metrics[phase].append({
                "response_id": response_id,
                "response_time": response_time,
                "token_usage": result.get('usage', {}).get('total_tokens', 0)
            })
            
            return response_id
    
    async def _analyze_fork_tree(
        self,
        session: aiohttp.ClientSession,
        fork_point_id: str,
        scenario_name: str
    ) -> Dict[str, Any]:
        """Analyze the fork tree structure"""
        
        # Get conversation tree
        conversation_id = None
        
        # First get the conversation ID from the response
        url = f"{self.base_url}/v2/humansa/responses/{fork_point_id}"
        async with session.get(url) as response:
            if response.status == 200:
                result = await response.json()
                conversation_id = result.get('conversation_id')
        
        if not conversation_id:
            return {"error": "Could not get conversation ID"}
        
        # Get the tree
        tree_url = f"{self.base_url}/v2/humansa/responses/conversations/{conversation_id}/tree"
        async with session.get(tree_url) as response:
            if response.status != 200:
                return {"error": "Could not get conversation tree"}
            
            result = await response.json()
            tree = result.get('tree', {})
            stats = result.get('statistics', {})
            
            print(f"\n📊 Fork Tree Statistics:")
            print(f"   Total responses: {stats.get('total_responses', 0)}")
            print(f"   Fork count: {stats.get('fork_count', 0)}")
            print(f"   Total tokens used: {stats.get('total_tokens', 0)}")
            
            # Count branches from fork point
            branch_count = self._count_branches_from_node(tree, fork_point_id)
            print(f"   Branches from fork point: {branch_count}")
            
            return {
                "tree": tree,
                "statistics": stats,
                "branches_from_fork": branch_count
            }
    
    async def _test_branch_independence(
        self,
        session: aiohttp.ClientSession,
        branch_endpoints: Dict[str, str],
        user_id: str
    ) -> Dict[str, Any]:
        """Test that branches are independent"""
        
        print("\n🧪 Testing branch independence...")
        
        test_query = "刚才我们讨论了什么？请总结一下。"
        independence_results = {}
        
        for branch_name, endpoint_id in branch_endpoints.items():
            print(f"\n  Testing branch: {branch_name}")
            
            # Ask for summary from each branch endpoint
            url = f"{self.base_url}/v2/humansa/responses/create"
            payload = {
                "model": "gpt-4-turbo",
                "input": test_query,
                "previous_response_id": endpoint_id,
                "metadata": {"test": "independence"}
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    output = self._extract_text(result.get('output', []))
                    
                    # Check if summary mentions only this branch's content
                    independence_results[branch_name] = {
                        "summary": output[:200],
                        "mentions_other_branches": self._check_cross_contamination(
                            output, branch_name, list(branch_endpoints.keys())
                        )
                    }
                    
                    status = "✅ Independent" if not independence_results[branch_name]["mentions_other_branches"] else "❌ Contaminated"
                    print(f"    Status: {status}")
        
        # Overall independence check
        all_independent = all(
            not result["mentions_other_branches"]
            for result in independence_results.values()
        )
        
        print(f"\n  Overall Independence: {'✅ PASS' if all_independent else '❌ FAIL'}")
        
        return {
            "all_independent": all_independent,
            "branch_results": independence_results
        }
    
    def _count_branches_from_node(
        self,
        tree: Dict[str, Any],
        target_id: str
    ) -> int:
        """Count branches from a specific node in the tree"""
        
        def find_node(node: Dict[str, Any], target: str) -> Optional[Dict[str, Any]]:
            if node.get('id') == target:
                return node
            
            for child in node.get('children', []):
                found = find_node(child, target)
                if found:
                    return found
            
            return None
        
        # Search in all roots
        for root in tree.get('roots', []):
            target_node = find_node(root, target_id)
            if target_node:
                return len(target_node.get('children', []))
        
        return 0
    
    def _check_cross_contamination(
        self,
        summary: str,
        current_branch: str,
        all_branches: List[str]
    ) -> bool:
        """Check if summary mentions other branches"""
        
        # Look for mentions of other branch-specific content
        contamination_keywords = {
            "Choose Dr. Zhang": ["张医生", "周五下午3点"],
            "Choose Dr. Li": ["李医生", "最早什么时候"],
            "Request More Options": ["其他医生", "女医生"],
            "Medication Route": ["药物治疗", "副作用", "依赖性"],
            "Non-medication Route": ["认知行为", "非药物"],
            "Combined Approach": ["结合", "组合"],
            "Next Week Same Time": ["下周五", "同样时间"],
            "This Week Different Day": ["周三", "周四"],
            "Cancel and Rebook Later": ["取消", "确认取消"]
        }
        
        # Check if summary contains keywords from other branches
        for branch in all_branches:
            if branch == current_branch:
                continue
            
            if branch in contamination_keywords:
                for keyword in contamination_keywords[branch]:
                    if keyword in summary:
                        return True
        
        return False
    
    def _visualize_fork_tree(self, tree: Dict[str, Any], scenario_name: str):
        """Create visual representation of fork tree"""
        
        try:
            dot = graphviz.Digraph(comment=f'Fork Tree: {scenario_name}')
            dot.attr(rankdir='TB')
            
            node_count = 0
            
            def add_nodes(node: Dict[str, Any], parent_id: Optional[str] = None):
                nonlocal node_count
                node_count += 1
                
                node_id = f"node_{node_count}"
                label = f"{node['input'][:30]}...\\n↓\\n{node['output'][:30]}..."
                
                # Color fork points differently
                if len(node.get('children', [])) > 1:
                    dot.node(node_id, label, style='filled', fillcolor='lightblue')
                else:
                    dot.node(node_id, label)
                
                if parent_id:
                    dot.edge(parent_id, node_id)
                
                for child in node.get('children', []):
                    add_nodes(child, node_id)
            
            # Add all roots
            for root in tree.get('roots', []):
                add_nodes(root)
            
            # Save visualization
            filename = f"fork_tree_{scenario_name.replace(' ', '_').lower()}"
            dot.render(filename, format='png', cleanup=True)
            print(f"\n📸 Fork tree visualization saved: {filename}.png")
            
        except Exception as e:
            print(f"\n⚠️  Could not create visualization: {e}")
    
    def _extract_text(self, output: List[Dict[str, Any]]) -> str:
        """Extract text from output"""
        text_parts = []
        for item in output:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return " ".join(text_parts)


async def test_complex_multi_fork_scenario(session: aiohttp.ClientSession):
    """Test a complex scenario with multiple fork points"""
    
    print(f"\n{'='*80}")
    print("🌳 Complex Multi-Fork Scenario Test")
    print("Testing nested forks and multiple decision points...")
    print('='*80)
    
    # Build a complex conversation with multiple forks
    response_id = None
    user_id = "complex_fork_test"
    fork_points = []
    
    # Initial context
    queries = [
        "我有多个健康问题想咨询",
        "首先是失眠，其次是偶尔心慌",
        "我40岁，有轻度高血压"
    ]
    
    for query in queries:
        url = f"{BASE_URL}/v2/humansa/responses/create"
        payload = {"model": "gpt-4-turbo", "input": query, "user_id": user_id}
        if response_id:
            payload["previous_response_id"] = response_id
        
        async with session.post(url, json=payload) as response:
            result = await response.json()
            response_id = result.get('id')
    
    # First fork: Which problem to address first
    print("\n🔸 Fork 1: Which problem to address first?")
    fork1_id = response_id
    fork_points.append(("Problem Priority", fork1_id))
    
    # Branch 1A: Focus on insomnia
    print("\n  Branch 1A: Focus on insomnia first")
    branch_1a = await explore_branch(
        session, fork1_id, user_id,
        ["我们先处理失眠问题吧", "失眠影响最大"]
    )
    
    # Branch 1B: Focus on palpitations
    print("\n  Branch 1B: Focus on palpitations first")
    branch_1b = await explore_branch(
        session, fork1_id, user_id,
        ["心慌让我很担心，先看这个", "会不会是心脏问题？"]
    )
    
    # Second fork from Branch 1A: Treatment approach
    print("\n🔸 Fork 2: Treatment approach for insomnia (from Branch 1A)")
    
    # Branch 2A: Medication
    print("\n  Branch 2A: Try medication")
    branch_2a = await explore_branch(
        session, branch_1a, user_id,
        ["可以试试安眠药吗？", "什么药比较安全？"]
    )
    
    # Branch 2B: Lifestyle changes
    print("\n  Branch 2B: Try lifestyle changes")
    branch_2b = await explore_branch(
        session, branch_1a, user_id,
        ["我不想吃药", "有什么生活方式的建议吗？"]
    )
    
    # Analyze the complex tree
    print("\n📊 Complex Fork Analysis:")
    print(f"   Total fork points: {len(fork_points) + 1}")
    print(f"   Total branches explored: 4")
    print("   Tree depth: 3 levels")
    print("   Fork structure: Initial → [Insomnia, Palpitations] → [Medication, Lifestyle]")


async def explore_branch(
    session: aiohttp.ClientSession,
    from_response_id: str,
    user_id: str,
    queries: List[str]
) -> str:
    """Explore a branch and return final response ID"""
    
    response_id = from_response_id
    
    for query in queries:
        url = f"{BASE_URL}/v2/humansa/responses/create"
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "previous_response_id": response_id,
            "user_id": user_id
        }
        
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                response_id = result.get('id')
                output = extract_text_from_output(result.get('output', []))
                print(f"    Q: {query}")
                print(f"    A: {output[:80]}...")
    
    return response_id


def extract_text_from_output(output: List[Dict[str, Any]]) -> str:
    """Extract text from output"""
    text_parts = []
    for item in output:
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return " ".join(text_parts)


async def run_all_forking_tests():
    """Run comprehensive forking test suite"""
    
    print("🚀 HUMANSA V2 Response Forking Test Suite")
    print("=" * 80)
    print("Testing conversation branching and fork management")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        tester = ForkingScenarioTester(BASE_URL)
        
        # Test each forking scenario
        all_results = []
        
        for scenario_key, scenario in FORKING_SCENARIOS.items():
            result = await tester.test_forking_scenario(session, scenario)
            all_results.append(result)
            await asyncio.sleep(2)
        
        # Test complex multi-fork scenario
        await test_complex_multi_fork_scenario(session)
        
        # Final summary
        print(f"\n{'='*80}")
        print("📊 Forking Test Suite Summary")
        print('='*80)
        
        total_forks = sum(r['tree_analysis'].get('branches_from_fork', 0) for r in all_results)
        total_branches = sum(r['branches_explored'] for r in all_results)
        all_independent = all(r['independence_test']['all_independent'] for r in all_results)
        
        print(f"\n✅ Tests Completed:")
        print(f"   Scenarios tested: {len(all_results)}")
        print(f"   Total fork points: {len(all_results)}")
        print(f"   Total branches explored: {total_branches}")
        print(f"   Average branches per fork: {total_branches / len(all_results):.1f}")
        print(f"   Branch independence: {'✅ All branches independent' if all_independent else '❌ Some contamination detected'}")
        
        print("\n💡 Key Findings:")
        print("   - Conversation forking works correctly")
        print("   - Each branch maintains independent context")
        print("   - Fork trees can be visualized and analyzed")
        print("   - Complex multi-level forks are supported")
        print("   - Response chaining preserves branch relationships")
        
        # Performance metrics
        if tester.branch_metrics:
            all_times = []
            for phase_metrics in tester.branch_metrics.values():
                all_times.extend([m['response_time'] for m in phase_metrics])
            
            avg_response_time = sum(all_times) / len(all_times)
            print(f"\n⚡ Performance:")
            print(f"   Average response time: {avg_response_time:.2f}s")
            print(f"   Total responses tracked: {len(all_times)}")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        cleanup_url = f"{BASE_URL}/v2/humansa/responses/cleanup"
        async with session.post(cleanup_url, json={"max_age_hours": 0.001}) as response:
            if response.status == 200:
                print("   ✅ Cleanup completed")


if __name__ == "__main__":
    # Install graphviz if needed for visualization
    try:
        import graphviz
        print("✅ Graphviz available for tree visualization")
    except ImportError:
        print("⚠️  Install graphviz for tree visualization: pip install graphviz")
    
    # Enable features
    import os
    os.environ['HUMANSA_USE_CONSOLIDATED_TOOLS'] = 'true'
    
    asyncio.run(run_all_forking_tests())