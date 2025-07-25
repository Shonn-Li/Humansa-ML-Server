#!/usr/bin/env python3
"""
Comprehensive Test Suite for Humansa AI Agent B2
Tests 20 different scenarios with detailed logging of tool calls, thinking process, and responses
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import aiohttp
from tabulate import tabulate
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class HumansaAgentTestSuite:
    """Comprehensive test suite for Humansa AI Agent B2"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/v1-humansa/chat/completions"
        self.test_results = []
        self.test_user_id = f"test_user_{int(time.time())}"
        
    async def call_agent(self, message: str, user_id: str = None) -> Dict[str, Any]:
        """Make an async call to the Humansa agent endpoint"""
        if user_id is None:
            user_id = self.test_user_id
            
        payload = {
            "messages": [{"role": "user", "content": message}],
            "model": "gpt-4",
            "user_id": user_id,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.endpoint, json=payload) as response:
                    return await response.json()
            except Exception as e:
                return {"error": str(e)}
    
    def parse_agent_trace(self, trace: str) -> Dict[str, List[str]]:
        """Parse the agent trace to extract thoughts, actions, and observations"""
        result = {
            "thoughts": [],
            "actions": [],
            "observations": [],
            "answers": []
        }
        
        if not trace:
            return result
            
        lines = trace.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                result["thoughts"].append(line[8:].strip())
            elif line.startswith("Action:"):
                result["actions"].append(line[7:].strip())
            elif line.startswith("Observation:"):
                result["observations"].append(line[12:].strip())
            elif line.startswith("Answer:"):
                result["answers"].append(line[7:].strip())
                
        return result
    
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from the response"""
        tool_calls = response.get("tool_calls_observed", [])
        parsed_trace = self.parse_agent_trace(response.get("agent_trace", ""))
        
        # Combine information
        enhanced_tool_calls = []
        for i, action in enumerate(parsed_trace["actions"]):
            tool_call = {
                "action": action,
                "tool_name": tool_calls[i]["tool_name"] if i < len(tool_calls) else "unknown",
                "result": tool_calls[i]["result"] if i < len(tool_calls) else "N/A",
                "thought": parsed_trace["thoughts"][i] if i < len(parsed_trace["thoughts"]) else "N/A"
            }
            enhanced_tool_calls.append(tool_call)
            
        return enhanced_tool_calls
    
    async def run_test_case(self, test_name: str, test_message: str, expected_tools: List[str] = None):
        """Run a single test case and record results"""
        print(f"\n{'='*80}")
        print(f"Running Test: {test_name}")
        print(f"{'='*80}")
        print(f"User Message: {test_message}")
        print("-" * 40)
        
        start_time = time.time()
        response = await self.call_agent(test_message)
        duration = time.time() - start_time
        
        # Check for errors
        if "error" in response and response.get("status") == "error":
            print(f"❌ ERROR: {response['error']}")
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": response['error'],
                "duration": duration
            })
            return
        
        # Parse the response
        agent_trace = response.get("agent_trace", "")
        parsed_trace = self.parse_agent_trace(agent_trace)
        tool_calls = self.extract_tool_calls(response)
        
        # Get the final response
        final_response = ""
        if "choices" in response and len(response["choices"]) > 0:
            final_response = response["choices"][0]["message"]["content"]
        
        # Print detailed results
        print("\n🧠 AGENT THINKING PROCESS:")
        for i, thought in enumerate(parsed_trace["thoughts"], 1):
            print(f"  Thought {i}: {thought}")
        
        print("\n🔧 TOOL CALLS:")
        if tool_calls:
            for i, tool_call in enumerate(tool_calls, 1):
                print(f"  Tool {i}: {tool_call['action']}")
                print(f"    - Tool Name: {tool_call['tool_name']}")
                if tool_call['result'] and len(str(tool_call['result'])) < 200:
                    print(f"    - Result: {tool_call['result']}")
                else:
                    print(f"    - Result: [Large result truncated - {len(str(tool_call['result']))} chars]")
        else:
            print("  No tool calls made")
        
        print("\n💬 FINAL RESPONSE:")
        print(f"  {final_response[:500]}{'...' if len(final_response) > 500 else ''}")
        
        # Check if expected tools were used
        tools_used = [tc['tool_name'] for tc in tool_calls]
        test_passed = True
        if expected_tools:
            missing_tools = set(expected_tools) - set(tools_used)
            if missing_tools:
                print(f"\n⚠️  Expected tools not used: {missing_tools}")
                test_passed = False
        
        # Record result
        self.test_results.append({
            "test_name": test_name,
            "status": "PASSED" if test_passed else "FAILED",
            "duration": duration,
            "tools_used": tools_used,
            "thoughts_count": len(parsed_trace["thoughts"]),
            "final_response_length": len(final_response)
        })
        
        print(f"\n✅ Test Status: {'PASSED' if test_passed else 'FAILED'}")
        print(f"⏱️  Duration: {duration:.2f}s")
    
    async def run_all_tests(self):
        """Run all 20 test cases"""
        test_cases = [
            # Doctor search tests (1-5)
            {
                "name": "1. Find doctor by specialty",
                "message": "我想找一个心脏科医生",
                "expected_tools": ["find_doctor_info"]
            },
            {
                "name": "2. Find doctor by city",
                "message": "深圳有哪些医生？",
                "expected_tools": ["find_doctor_info"]
            },
            {
                "name": "3. Find specific doctor",
                "message": "张医生的信息",
                "expected_tools": ["find_doctor_info"]
            },
            {
                "name": "4. Doctor availability check",
                "message": "李医生下周有空吗？",
                "expected_tools": ["find_doctor_availability"]
            },
            {
                "name": "5. Multiple doctor search",
                "message": "北京的骨科医生有哪些？他们的挂号费是多少？",
                "expected_tools": ["find_doctor_info"]
            },
            
            # Appointment booking tests (6-10)
            {
                "name": "6. Book appointment request",
                "message": "我想预约王医生，我叫李明，电话13800138000",
                "expected_tools": ["find_doctor_info", "prepare_booking_confirmation"]
            },
            {
                "name": "7. Appointment with missing info",
                "message": "帮我预约张医生",
                "expected_tools": ["find_doctor_info"]
            },
            {
                "name": "8. Emergency appointment",
                "message": "我胸痛很严重，需要马上看医生",
                "expected_tools": []  # Should refuse and suggest 120
            },
            {
                "name": "9. Appointment confirmation",
                "message": "确认预约",
                "expected_tools": []  # Context dependent
            },
            {
                "name": "10. Cancel appointment inquiry",
                "message": "如何取消预约？",
                "expected_tools": []
            },
            
            # Clinic and service tests (11-15)
            {
                "name": "11. Find clinic by location",
                "message": "广州有哪些诺亚新舟诊所？",
                "expected_tools": ["search_clinics"]
            },
            {
                "name": "12. Clinic services inquiry",
                "message": "深圳诊所提供哪些检查服务？",
                "expected_tools": ["search_services"]
            },
            {
                "name": "13. Service pricing",
                "message": "肝功能检查多少钱？",
                "expected_tools": ["get_pricing"]
            },
            {
                "name": "14. Compare clinic prices",
                "message": "哪个诊所的体检最便宜？",
                "expected_tools": ["search_services", "get_pricing"]
            },
            {
                "name": "15. Specific service search",
                "message": "哪里可以做核磁共振？",
                "expected_tools": ["search_services"]
            },
            
            # General health and information tests (16-20)
            {
                "name": "16. Health symptom inquiry",
                "message": "我头痛应该看什么科？",
                "expected_tools": []
            },
            {
                "name": "17. Web search health info",
                "message": "最新的新冠疫情信息",
                "expected_tools": ["search_web"]
            },
            {
                "name": "18. Product recommendation",
                "message": "有什么健康产品推荐吗？",
                "expected_tools": ["recommend_product"]
            },
            {
                "name": "19. General greeting",
                "message": "你好，诺亚新舟是什么？",
                "expected_tools": []
            },
            {
                "name": "20. Complex multi-step query",
                "message": "我想找北京的心脏科医生，看看他们下周的时间，并了解挂号费用",
                "expected_tools": ["find_doctor_info", "find_doctor_availability"]
            }
        ]
        
        print("\n" + "="*80)
        print("HUMANSA AI AGENT B2 - COMPREHENSIVE TEST SUITE")
        print(f"Testing {len(test_cases)} scenarios")
        print(f"Endpoint: {self.endpoint}")
        print(f"Test User ID: {self.test_user_id}")
        print("="*80)
        
        # Check if server is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status != 200:
                        print("❌ ML Server is not running!")
                        return
        except:
            print("❌ Cannot connect to ML Server at", self.base_url)
            return
        
        # Run all tests
        for test_case in test_cases:
            await self.run_test_case(
                test_case["name"],
                test_case["message"],
                test_case.get("expected_tools", [])
            )
            await asyncio.sleep(1)  # Small delay between tests
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a summary report of all test results"""
        print("\n" + "="*80)
        print("TEST SUMMARY REPORT")
        print("="*80)
        
        # Overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed_tests = total_tests - passed_tests
        avg_duration = sum(r["duration"] for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"  Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"  Average Duration: {avg_duration:.2f}s")
        
        # Tool usage statistics
        all_tools = []
        for result in self.test_results:
            all_tools.extend(result.get("tools_used", []))
        
        tool_counts = {}
        for tool in all_tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        print(f"\n🔧 TOOL USAGE:")
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count} times")
        
        # Detailed results table
        print(f"\n📋 DETAILED RESULTS:")
        table_data = []
        for i, result in enumerate(self.test_results, 1):
            table_data.append([
                i,
                result["test_name"][:40] + "..." if len(result["test_name"]) > 40 else result["test_name"],
                result["status"],
                f"{result['duration']:.2f}s",
                len(result.get("tools_used", [])),
                result.get("thoughts_count", 0)
            ])
        
        print(tabulate(
            table_data,
            headers=["#", "Test Name", "Status", "Duration", "Tools", "Thoughts"],
            tablefmt="grid"
        ))
        
        # Failed tests details
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS DETAILS:")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    print(f"\n  Test: {result['test_name']}")
                    if "error" in result:
                        print(f"  Error: {result['error']}")
        
        # Save report to file
        report_filename = f"humansa_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "test_date": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "average_duration": avg_duration
                },
                "tool_usage": tool_counts,
                "detailed_results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {report_filename}")

async def main():
    """Main entry point"""
    test_suite = HumansaAgentTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    # Check if tabulate is installed
    try:
        import tabulate
    except ImportError:
        print("Installing tabulate for better output formatting...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
        import tabulate
    
    # Run the test suite
    asyncio.run(main())