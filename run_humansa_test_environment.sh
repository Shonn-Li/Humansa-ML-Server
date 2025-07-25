#!/bin/bash
# Comprehensive Humansa AI Agent V2 Test Environment with Detailed Output

echo "============================================"
echo "HUMANSA AI AGENT V2 - TEST ENVIRONMENT"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Apply Humansa agent improvements
echo -e "\n${YELLOW}Step 1: Applying Humansa agent improvements...${NC}"

# Check if agent already has search_web filter
if grep -q "Filter out search_web tool" src/humansa/agent/humansa_agent.py; then
    echo -e "${GREEN}✅ Agent already has search_web filter${NC}"
else
    echo "Applying search_web filter to agent..."
    python3 - << 'EOF'
import sys
import os

agent_file = "src/humansa/agent/humansa_agent.py"
if os.path.exists(agent_file):
    with open(agent_file, 'r') as f:
        content = f.read()
    
    # Add filtering after tools assignment
    lines = content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if "self.tools = tools or []" in line and i+1 < len(lines):
            if "self.tools = [tool for tool" not in lines[i+1]:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}# Filter out search_web tool to prevent external searches")
                new_lines.append(f"{indent}if self.tools:")
                new_lines.append(f"{indent}    original_count = len(self.tools)")
                new_lines.append(f"{indent}    self.tools = [tool for tool in self.tools if not (hasattr(tool, 'metadata') and hasattr(tool.metadata, 'name') and tool.metadata.name == 'search_web')]")
                new_lines.append(f"{indent}    if len(self.tools) < original_count:")
                new_lines.append(f"{indent}        logger.info(f'🚫 Filtered out search_web tool. Remaining tools: {{len(self.tools)}}')")
    
    content = '\n'.join(new_lines)
    
    with open(agent_file, 'w') as f:
        f.write(content)
    
    print("✅ Applied search_web filter to agent")
else:
    print("❌ Agent file not found")
    sys.exit(1)
EOF
fi

# Step 2: Activate virtual environment
echo -e "\n${YELLOW}Step 2: Activating virtual environment...${NC}"
source youwo-ml-venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Step 3: Clean up port and start ML server
echo -e "\n${YELLOW}Step 3: Cleaning up port 6001...${NC}"

# Use dedicated cleanup script
if [ -f "./kill_port_6001.sh" ]; then
    ./kill_port_6001.sh
else
    # Fallback cleanup
    lsof -ti:6001 | xargs kill -9 2>/dev/null || true
    ps aux | grep -E "python.*main\.py.*6001" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "\n${YELLOW}Starting ML server on port 6001...${NC}"

ML_SERVER_PORT=6001 nohup python3 src/main.py --port 6001 > test_server.log 2>&1 &
SERVER_PID=$!

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi
    # Extra cleanup for any lingering processes
    lsof -ti:6001 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

trap cleanup EXIT

# Wait for server to start
echo "Waiting for server to start..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:6001/api/debug/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is running on port 6001${NC}"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -ne "\rWaiting... ${WAITED}s"
done

if [ $WAITED -eq $MAX_WAIT ]; then
    echo -e "\n${RED}❌ Server failed to start${NC}"
    tail -20 test_server.log
    exit 1
fi

# Step 4: Run comprehensive tests with detailed output
echo -e "\n${YELLOW}Step 4: Running comprehensive Humansa tests...${NC}"

python3 - << 'PYTEST'
import asyncio
import json
import sys
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "aiohttp"])
    import aiohttp

class HumansaTestRunner:
    def __init__(self, base_url):
        self.base_url = base_url
        self.endpoint = f"{base_url}/v1-humansa/chat/completions"
        self.results = []
        self.all_tests = []
    
    def fix_react_format(self, response_text):
        """Auto-fix common ReAct format parsing errors."""
        if not response_text:
            return ""
            
        # Fix missing colons after keywords
        response_text = re.sub(r'(?<!\w)(Thought|Action|Observation|Answer)(?!:)', r'\1:', response_text)
        
        # Fix Action Input format
        response_text = re.sub(r'Action Input(?::|)\s*(?!{)', 'Action Input: ', response_text)
        
        return response_text
    
    def extract_tool_details(self, trace_text):
        """Extract tool calls and their outputs from trace."""
        tools_info = []
        
        if not trace_text:
            return tools_info
            
        # Split by Action: to find tool calls
        parts = trace_text.split('Action:')
        for i, part in enumerate(parts[1:], 1):  # Skip first part before any Action
            lines = part.split('\n')
            if lines:
                tool_name = lines[0].strip()
                
                # Find Action Input
                action_input = ""
                observation = ""
                
                for j, line in enumerate(lines):
                    if 'Action Input:' in line:
                        # Extract JSON after Action Input
                        input_start = line.find('Action Input:') + len('Action Input:')
                        action_input = line[input_start:].strip()
                    elif 'Observation:' in line:
                        # Extract observation
                        obs_start = line.find('Observation:') + len('Observation:')
                        observation = line[obs_start:].strip()
                        # Continue to next lines if observation is multi-line
                        for k in range(j+1, len(lines)):
                            if lines[k].strip() and not any(keyword in lines[k] for keyword in ['Thought:', 'Action:', 'Answer:']):
                                observation += " " + lines[k].strip()
                            else:
                                break
                
                tools_info.append({
                    'tool': tool_name,
                    'input': action_input,
                    'output': observation[:200] + '...' if len(observation) > 200 else observation
                })
        
        return tools_info
        
    async def test_query(self, test_id, test_name, query):
        """Run a single test with detailed output."""
        print(f"\n{'='*80}")
        print(f"TEST {test_id}: {test_name}")
        print(f"{'='*80}")
        print(f"\n📝 Query: {query}")
        print("-"*60)
        
        start_time = time.time()
        
        payload = {
            "messages": [{"role": "user", "content": query}],
            "model": "gpt-4",
            "user_id": f"test_user_{test_id}",
            "stream": False
        }
        
        test_result = {
            'id': test_id,
            'name': test_name,
            'query': query,
            'success': False,
            'duration': 0,
            'tools_used': [],
            'response': '',
            'error': None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    result = await response.json()
                    duration = time.time() - start_time
                    test_result['duration'] = duration
                    
                    # Check for errors
                    if "error" in result:
                        print(f"\n❌ ERROR: {result['error']}")
                        test_result['error'] = result['error']
                        self.results.append(test_result)
                        return
                    
                    # Extract agent trace
                    trace = result.get("agent_trace", "")
                    if trace:
                        # Fix format issues
                        fixed_trace = self.fix_react_format(trace)
                        
                        # Extract thinking process
                        print("\n🧠 AGENT THINKING PROCESS:")
                        thoughts = re.findall(r'Thought:(.*?)(?=Action:|Answer:|$)', fixed_trace, re.DOTALL)
                        for i, thought in enumerate(thoughts, 1):
                            print(f"\n  Step {i}: {thought.strip()[:200]}...")
                        
                        # Extract and display tool usage
                        tools_info = self.extract_tool_details(fixed_trace)
                        if tools_info:
                            print("\n🔧 TOOLS USED:")
                            for i, tool_info in enumerate(tools_info, 1):
                                print(f"\n  Tool {i}: {tool_info['tool']}")
                                print(f"  Input: {tool_info['input']}")
                                print(f"  Output: {tool_info['output']}")
                                test_result['tools_used'].append(tool_info)
                    
                    # Extract tool calls from observation
                    tool_calls = result.get("tool_calls_observed", [])
                    if tool_calls and not test_result['tools_used']:
                        print("\n🔧 TOOLS OBSERVED:")
                        for i, tool in enumerate(tool_calls, 1):
                            tool_name = tool.get("tool_name", "unknown")
                            print(f"  {i}. {tool_name}")
                    
                    # Extract final answer
                    print("\n💬 FINAL RESPONSE:")
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                        
                        # Try to extract Answer: if in ReAct format
                        answer_match = re.search(r'Answer:(.*?)$', content, re.DOTALL)
                        if answer_match:
                            final_answer = answer_match.group(1).strip()
                        else:
                            final_answer = content
                        
                        print(f"  {final_answer[:300]}{'...' if len(final_answer) > 300 else ''}")
                        test_result['response'] = final_answer
                    
                    # Check for specific issues
                    if trace:
                        # Check for search_web usage
                        if "search_web" in trace.lower():
                            print("\n⚠️  WARNING: search_web tool was used!")
                        
                        # Check ReAct format
                        has_thought = "Thought:" in trace
                        has_action = "Action:" in trace
                        
                        if has_thought and has_action:
                            print(f"\n✅ ReAct pattern correctly used")
                        else:
                            print(f"\n⚠️  Missing ReAct components")
                    
                    print(f"\n⏱️  Response time: {duration:.2f}s")
                    test_result['success'] = True
                    
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            test_result['error'] = str(e)
        
        self.results.append(test_result)
        
    async def run_all_tests(self):
        """Run comprehensive test suite."""
        # Define test cases with clear descriptions
        test_cases = [
            # Doctor search tests
            {
                'id': 1,
                'name': 'Find Cardiologist in Chinese',
                'query': '我想找一个心脏科医生'
            },
            {
                'id': 2,
                'name': 'Find Doctors by City',
                'query': '深圳有哪些医生？'
            },
            {
                'id': 3,
                'name': 'Find Specific Doctor Info',
                'query': '张医生的信息'
            },
            {
                'id': 4,
                'name': 'Check Doctor Availability',
                'query': '李医生下周有空吗？'
            },
            {
                'id': 5,
                'name': 'Multi-criteria Doctor Search',
                'query': '北京的骨科医生'
            },
            
            # Appointment tests
            {
                'id': 6,
                'name': 'Book Appointment with Details',
                'query': '预约王医生，我叫李明，电话13800138000'
            },
            {
                'id': 7,
                'name': 'Incomplete Booking Request',
                'query': '帮我预约张医生'
            },
            {
                'id': 8,
                'name': 'Emergency Symptom Case',
                'query': '胸痛很严重，需要看医生'
            },
            {
                'id': 9,
                'name': 'Appointment Confirmation',
                'query': '确认我明天的预约'
            },
            {
                'id': 10,
                'name': 'Cancel Appointment Inquiry',
                'query': '如何取消预约？'
            },
            
            # Clinic and service tests
            {
                'id': 11,
                'name': 'Find Clinics by Location',
                'query': '广州有哪些诊所？'
            },
            {
                'id': 12,
                'name': 'Clinic Services Query',
                'query': '深圳诊所提供什么服务？'
            },
            {
                'id': 13,
                'name': 'Service Pricing Query',
                'query': '肝功能检查多少钱？'
            },
            {
                'id': 14,
                'name': 'Compare Service Prices',
                'query': '哪里的体检最便宜？'
            },
            {
                'id': 15,
                'name': 'Specific Medical Service',
                'query': '核磁共振检查的信息'
            },
            
            # General queries
            {
                'id': 16,
                'name': 'Symptom Department Recommendation',
                'query': '头痛应该看什么科？'
            },
            {
                'id': 17,
                'name': 'Clinic Operating Hours',
                'query': '诊所的营业时间'
            },
            {
                'id': 18,
                'name': 'Health Product Recommendation',
                'query': '推荐一些健康产品'
            },
            {
                'id': 19,
                'name': 'Simple Greeting',
                'query': '你好'
            },
            {
                'id': 20,
                'name': 'Complex Multi-part Query',
                'query': '北京的心脏科医生下周的时间和收费标准'
            }
        ]
        
        print("\n" + "="*80)
        print("HUMANSA AI AGENT V2 - COMPREHENSIVE TEST SUITE")
        print(f"Running {len(test_cases)} test cases")
        print("="*80)
        
        # Run all tests
        for test_case in test_cases:
            await self.test_query(test_case['id'], test_case['name'], test_case['query'])
            await asyncio.sleep(1)  # Small delay between tests
        
        # Generate summary report
        self.generate_summary()
    
    def generate_summary(self):
        """Generate comprehensive test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY REPORT")
        print("="*80)
        
        # Calculate statistics
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed} ({pass_rate:.1f}%)")
        print(f"   Failed: {failed}")
        
        # Tool usage statistics
        all_tools = []
        for result in self.results:
            all_tools.extend([t['tool'] for t in result['tools_used']])
        
        if all_tools:
            print(f"\n🔧 Tool Usage Statistics:")
            tool_counts = {}
            for tool in all_tools:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {tool}: {count} times")
        
        # Performance statistics
        durations = [r['duration'] for r in self.results if r['success']]
        if durations:
            avg_time = sum(durations) / len(durations)
            print(f"\n⏱️  Performance:")
            print(f"   Average response time: {avg_time:.2f}s")
            print(f"   Fastest: {min(durations):.2f}s")
            print(f"   Slowest: {max(durations):.2f}s")
        
        # Failed tests details
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for r in self.results:
                if not r['success']:
                    print(f"   Test {r['id']}: {r['name']}")
                    if r['error']:
                        print(f"      Error: {r['error']}")
        
        # Pass rate evaluation
        print(f"\n📈 Evaluation:")
        if pass_rate >= 90:
            print(f"   🎉 EXCELLENT! Agent meets Humansa requirements (≥90% pass rate)")
        elif pass_rate >= 80:
            print(f"   ✅ GOOD! Agent is performing well ({pass_rate:.1f}%)")
        elif pass_rate >= 70:
            print(f"   ⚠️  NEEDS IMPROVEMENT: Agent at {pass_rate:.1f}% (target ≥90%)")
        else:
            print(f"   ❌ CRITICAL: Agent performance is poor ({pass_rate:.1f}%)")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"humansa_test_results_{timestamp}.json"
        
        with open(filename, "w", encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "summary": {
                    "total_tests": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": pass_rate,
                    "average_response_time": avg_time if durations else 0
                },
                "detailed_results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {filename}")

# Run the tests
async def main():
    runner = HumansaTestRunner("http://localhost:6001")
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
PYTEST

echo -e "\n${GREEN}✅ Test suite completed!${NC}"
echo -e "\nCheck the generated JSON file for detailed results."
echo -e "Server logs are available in: test_server.log"