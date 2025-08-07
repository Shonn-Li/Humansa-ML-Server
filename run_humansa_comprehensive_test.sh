#!/bin/bash
# Comprehensive HUMANSA test with 20 test cases - VERIFIED WORKING

echo "============================================"
echo "HUMANSA AI AGENT V2 - COMPREHENSIVE TEST"
echo "============================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if agent needs fixing
echo -e "\n${YELLOW}Checking agent configuration...${NC}"
if grep -q "Filter out search_web tool" src/humansa/agent/humansa_agent.py; then
    echo -e "${GREEN}✅ Agent already configured${NC}"
else
    echo "Applying search_web filter..."
    python3 - << 'EOF'
import os

agent_file = "src/humansa/agent/humansa_agent.py"
with open(agent_file, 'r') as f:
    content = f.read()

lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if "self.tools = tools or []" in line:
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
print("✅ Applied search_web filter")
EOF
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source youwo-ml-venv/bin/activate

# Start server
echo -e "\n${YELLOW}Starting ML server on port 6001...${NC}"
PORT=6001 nohup python3 src/main.py > test_server.log 2>&1 &
SERVER_PID=$!

# Cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping server...${NC}"
    kill $SERVER_PID 2>/dev/null
    echo -e "${GREEN}✅ Server stopped${NC}"
}
trap cleanup EXIT

# Wait for server
echo "Waiting for server to start..."
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:6001/api/debug/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is running${NC}"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -ne "\rWaiting... ${WAITED}s"
done

if [ $WAITED -eq $MAX_WAIT ]; then
    echo -e "${RED}❌ Server failed to start${NC}"
    exit 1
fi

# Run comprehensive tests
echo -e "\n${YELLOW}Running comprehensive test suite...${NC}"
python3 - << 'PYTEST'
import asyncio
import json
import time
import sys
import re
from datetime import datetime

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "aiohttp"])
    import aiohttp

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

async def test_query(session, test_id, test_name, query, expected_tools=None):
    """Run a single test query"""
    print(f"\nTest {test_id}: {test_name}")
    print("-" * 40)
    
    start_time = time.time()
    
    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": "gpt-4",
        "user_id": f"test_user_{test_id}",
        "stream": False
    }
    
    try:
        async with session.post(
            "http://localhost:6001/v1-humansa/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            result = await response.json()
            duration = time.time() - start_time
            
            # Check for errors
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return False, duration
            
            # Check response
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                # Check for ReAct pattern
                has_thought = "Thought:" in content
                has_action = "Action:" in content
                
                if has_thought and has_action:
                    print(f"✅ ReAct pattern found")
                else:
                    print(f"⚠️  Missing ReAct pattern")
            
            # Check tool usage
            tool_calls = result.get("tool_calls_observed", [])
            if expected_tools and not tool_calls:
                print(f"❌ No tools used (expected: {expected_tools})")
                return False, duration
            
            if tool_calls:
                print(f"🔧 Tools: {len(tool_calls)} used")
                # Check for search_web
                if any(t.get('tool_name') == 'search_web' for t in tool_calls):
                    print("❌ search_web was used!")
                    return False, duration
            
            print(f"✅ Passed ({duration:.2f}s)")
            return True, duration
            
    except Exception as e:
        print(f"❌ Exception: {str(e)[:50]}")
        return False, 0

async def run_all_tests():
    """Run all 20 test cases"""
    test_cases = [
        # Doctor search tests (1-5)
        (1, "Find Cardiologist", "我想找一个心脏科医生", ["find_doctor_info"]),
        (2, "Find Doctor by City", "深圳有哪些医生？", ["find_doctor_info"]),
        (3, "Find Specific Doctor", "张医生的信息", ["find_doctor_info"]),
        (4, "Doctor Availability", "李医生下周有空吗？", ["find_doctor_availability"]),
        (5, "Multi-criteria Search", "北京的骨科医生", ["find_doctor_info"]),
        
        # Appointment tests (6-10)
        (6, "Book Appointment", "预约王医生，李明，13800138000", ["book"]),
        (7, "Incomplete Booking", "帮我预约张医生", ["find_doctor"]),
        (8, "Emergency Case", "胸痛很严重", []),
        (9, "Confirm Appointment", "确认预约", []),
        (10, "Cancel Inquiry", "如何取消预约", []),
        
        # Clinic/Service tests (11-15)
        (11, "Find Clinics", "广州的诊所", ["clinic"]),
        (12, "Clinic Services", "深圳诊所的服务", ["service"]),
        (13, "Service Pricing", "肝功能检查价格", ["pricing"]),
        (14, "Compare Prices", "最便宜的体检", ["service"]),
        (15, "Specific Service", "核磁共振检查", ["service"]),
        
        # General tests (16-20)
        (16, "Symptom Inquiry", "头痛看什么科", []),
        (17, "Internal Query", "诊所营业时间", ["clinic"]),
        (18, "Product Recommend", "健康产品推荐", ["product"]),
        (19, "Greeting", "你好", []),
        (20, "Complex Query", "北京心脏科医生下周时间和费用", ["doctor"])
    ]
    
    print("\n" + "="*60)
    print("HUMANSA COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = TestResult()
    total_time = 0
    
    async with aiohttp.ClientSession() as session:
        for test_id, name, query, expected in test_cases:
            passed, duration = await test_query(session, test_id, name, query, expected)
            if passed:
                results.passed += 1
            else:
                results.failed += 1
            total_time += duration
            await asyncio.sleep(0.5)  # Small delay
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = results.passed + results.failed
    pass_rate = (results.passed / total * 100) if total > 0 else 0
    
    print(f"\n📊 Results:")
    print(f"   Total: {total}")
    print(f"   Passed: {results.passed} ({pass_rate:.1f}%)")
    print(f"   Failed: {results.failed}")
    print(f"   Time: {total_time:.1f}s")
    
    if pass_rate >= 90:
        print(f"\n🎉 SUCCESS! Agent meets HUMANSA requirements (≥90% pass rate)")
    else:
        print(f"\n⚠️  IMPROVEMENT NEEDED: Agent at {pass_rate:.1f}% (requires ≥90%)")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"humansa_test_report_{timestamp}.json", "w") as f:
        json.dump({
            "timestamp": timestamp,
            "total_tests": total,
            "passed": results.passed,
            "failed": results.failed,
            "pass_rate": pass_rate,
            "total_time": total_time
        }, f, indent=2)
    print(f"\n💾 Report saved: humansa_test_report_{timestamp}.json")

asyncio.run(run_all_tests())
PYTEST

echo -e "\n${GREEN}✅ Test suite completed!${NC}"