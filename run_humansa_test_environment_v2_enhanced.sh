#!/bin/bash
# Enhanced Humansa AI Agent V2 Test Environment with Detailed Logging

echo "============================================"
echo "HUMANSA AI AGENT V2 - ENHANCED TEST ENVIRONMENT"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "youwo-ml-venv/bin/activate" ]; then
    source youwo-ml-venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found. Please create it first.${NC}"
    exit 1
fi

# Environment variables for test
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5456
export DB_USER=postgres
export DB_PASSWORD=youwo123
export DB_NAME=youwoai
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true  # Enable enhanced logging

# Step 1: Check PostgreSQL test database
echo -e "\n${YELLOW}Step 1: Checking PostgreSQL test database...${NC}"
if pg_isready -h localhost -p 5456 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL test database is running on port 5456${NC}"
else
    echo -e "${RED}❌ PostgreSQL test database is not running on port 5456${NC}"
    echo "Please start the test database first with:"
    echo "cd test_environment && docker-compose up -d"
    exit 1
fi

# Step 2: Check Mem0 initialization
echo -e "\n${YELLOW}Step 2: Checking Mem0 configuration...${NC}"
python3 - << 'EOF'
import os
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
print(f"ML_SERVER_PORT: {os.getenv('ML_SERVER_PORT')}")
print(f"HUMANSA_ENHANCED_LOGGING: {os.getenv('HUMANSA_ENHANCED_LOGGING')}")

# Check if Mem0 can be imported
try:
    from mem0 import Memory
    print("✅ Mem0 package is installed")
except ImportError:
    print("❌ Mem0 package not found. Install with: pip install mem0ai")
EOF

# Step 3: Kill any existing processes on port 6001
echo -e "\n${YELLOW}Step 3: Checking for existing processes on port 6001...${NC}"
if lsof -i :6001 > /dev/null 2>&1; then
    echo "Found existing process on port 6001, killing it..."
    lsof -ti :6001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Step 4: Start the ML server with V2 enabled
echo -e "\n${YELLOW}Step 4: Starting ML server with Enhanced Humansa V2...${NC}"
echo "Server will run on port 6001 (test environment)"
echo -e "${CYAN}Enhanced logging is ENABLED${NC}"

# Start server in background with port argument
python3 -m src.main --port 6001 > server_v2_enhanced.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo -n "Waiting for server to start"
for i in {1..30}; do
    if curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Server is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
    echo -e "\n${RED}❌ Server failed to start. Check server_v2_enhanced.log for errors${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Step 5: Check V2 health and memory status
echo -e "\n${YELLOW}Step 5: Checking V2 health and memory status...${NC}"
echo -e "${BLUE}V2 Health Check:${NC}"
curl -s http://localhost:6001/v2/humansa/health | python3 -m json.tool

echo -e "\n${BLUE}Memory Status:${NC}"
curl -s http://localhost:6001/v2/humansa/memory/status | python3 -m json.tool

# Step 6: Run comprehensive V2 tests with enhanced logging
echo -e "\n${YELLOW}Step 6: Running comprehensive V2 tests with enhanced logging (30 test cases)...${NC}"

# Create enhanced V2 test script
cat > test_humansa_v2_comprehensive_enhanced.py << 'TESTSCRIPT'
#!/usr/bin/env python3
"""Enhanced Humansa V2 Test Suite with Detailed Logging - 30 Test Cases"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
import sys

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text, color=Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

# Original 20 identity test cases
IDENTITY_TEST_CASES = [
    {
        "id": 1,
        "name": "Basic Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"],
        "description": "Agent should identify itself as 诺亚新舟健康医疗助理/小诺"
    },
    {
        "id": 2,
        "name": "Company Background",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "三甲主任级", "名医专家", "30+家", "高端综合名医诊所"],
        "description": "Agent should provide accurate company background"
    },
    {
        "id": 3,
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航", "体检报告"],
        "description": "Agent should list its service capabilities"
    },
    {
        "id": 4,
        "name": "Brand Slogan",
        "query": "诺亚新舟的口号是什么？",
        "expected_keywords": ["以爱行舟", "亲近相守"],
        "description": "Agent should know the company slogan"
    },
    {
        "id": 5,
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["Humansa", "health", "assistant", "medical"],
        "description": "Agent should respond in English when asked in English"
    },
    {
        "id": 6,
        "name": "Service Scope",
        "query": "你们有多少医生？多少诊所？",
        "expected_keywords": ["500", "三甲", "30+", "诊所"],
        "description": "Agent should know the scale of services"
    },
    {
        "id": 7,
        "name": "Health Mall Reference",
        "query": "我想买保健品",
        "expected_keywords": ["健康商城", "诺亚新舟医疗", "小程序"],
        "description": "Agent should recommend the health mall for products"
    },
    {
        "id": 8,
        "name": "Article Reference",
        "query": "有什么最新的健康文章推荐吗？",
        "expected_keywords": ["mp.weixin.qq.com", "最新文章"],
        "description": "Agent should provide the latest article link"
    },
    {
        "id": 9,
        "name": "Emergency Response",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "立即", "急救"],
        "description": "Agent should recommend calling 120 for emergencies"
    },
    {
        "id": 10,
        "name": "Self-Owned Clinics Only",
        "query": "推荐一个最好的医院给我",
        "expected_keywords": ["诊所", "诺亚新舟", "预约"],
        "not_expected": ["其他医院", "公立医院", "三甲医院"],
        "description": "Agent should only recommend self-owned clinics"
    },
    {
        "id": 11,
        "name": "Greeting - Hello",
        "query": "你好",
        "expected_keywords": ["你好", "诺亚新舟", "小诺", "健康"],
        "description": "Should respond with friendly greeting and identity"
    },
    {
        "id": 12,
        "name": "Greeting - Hi",
        "query": "Hi",
        "expected_keywords": ["你好", "诺亚新舟", "小诺", "健康"],
        "description": "Should respond with friendly greeting and identity"
    },
    {
        "id": 13,
        "name": "Booking Request",
        "query": "我想预约看医生",
        "expected_keywords": ["预约", "诊所", "时间", "医生"],
        "description": "Should guide user through booking process"
    },
    {
        "id": 14,
        "name": "Health Consultation",
        "query": "最近总是失眠怎么办？",
        "expected_keywords": ["睡眠", "建议", "医生", "诊所"],
        "description": "Should provide health advice and suggest consultation"
    },
    {
        "id": 15,
        "name": "Check-up Query",
        "query": "你们提供体检服务吗？",
        "expected_keywords": ["体检", "检查", "套餐", "预约"],
        "description": "Should explain check-up services"
    },
    {
        "id": 16,
        "name": "Doctor Specialties",
        "query": "你们有哪些科室的医生？",
        "expected_keywords": ["内科", "外科", "儿科", "专科"],
        "description": "Should list available specialties"
    },
    {
        "id": 17,
        "name": "Location Query",
        "query": "最近的诊所在哪里？",
        "expected_keywords": ["诊所", "地址", "导航", "位置"],
        "description": "Should help with clinic locations"
    },
    {
        "id": 18,
        "name": "Insurance Query",
        "query": "你们接受医保吗？",
        "expected_keywords": ["医保", "保险", "支付", "费用"],
        "description": "Should explain payment options"
    },
    {
        "id": 19,
        "name": "Report Interpretation",
        "query": "能帮我看看这个检查报告吗？",
        "expected_keywords": ["报告", "解读", "医生", "咨询"],
        "description": "Should offer report interpretation service"
    },
    {
        "id": 20,
        "name": "Follow-up Care",
        "query": "手术后需要注意什么？",
        "expected_keywords": ["术后", "恢复", "注意事项", "复查"],
        "description": "Should provide post-operative care advice"
    }
]

# Additional 10 Mem0-specific test cases
MEM0_TEST_CASES = [
    {
        "id": 21,
        "name": "Memory Persistence - Allergy",
        "setup": {
            "user_id": 10001,
            "messages": [
                {"role": "user", "content": "我对花生过敏"},
                {"role": "assistant", "content": "我已记录您对花生过敏的信息。"}
            ]
        },
        "query": "我有什么过敏史吗？",
        "expected_keywords": ["花生", "过敏"],
        "description": "Should recall allergy information from memory"
    },
    {
        "id": 22,
        "name": "Memory Persistence - Medical History",
        "setup": {
            "user_id": 10002,
            "messages": [
                {"role": "user", "content": "我有高血压，每天吃降压药"},
                {"role": "assistant", "content": "了解，您有高血压病史，正在服用降压药。"}
            ]
        },
        "query": "我需要注意什么健康问题？",
        "expected_keywords": ["高血压", "降压药"],
        "description": "Should recall medical history from memory"
    },
    {
        "id": 23,
        "name": "Preference Learning - Appointment",
        "setup": {
            "user_id": 10003,
            "messages": [
                {"role": "user", "content": "我喜欢周末上午来看病"},
                {"role": "assistant", "content": "好的，我记住了您偏好周末上午的预约时间。"}
            ]
        },
        "query": "帮我预约一个合适的时间",
        "expected_keywords": ["周末", "上午"],
        "description": "Should suggest appointment based on preference"
    },
    {
        "id": 24,
        "name": "Cross-Session Continuity",
        "setup": {
            "user_id": 10004,
            "messages": [
                {"role": "user", "content": "我上次说的膝盖疼痛问题"},
                {"role": "assistant", "content": "您之前提到的膝盖疼痛问题，建议..."}
            ]
        },
        "query": "我的膝盖还是有问题",
        "expected_keywords": ["膝盖", "疼痛", "之前", "上次"],
        "description": "Should reference previous conversations"
    },
    {
        "id": 25,
        "name": "Family Member Tracking",
        "setup": {
            "user_id": 10005,
            "messages": [
                {"role": "user", "content": "我女儿5岁，经常感冒"},
                {"role": "assistant", "content": "了解，您5岁的女儿经常感冒。"}
            ]
        },
        "query": "适合小孩的感冒药有哪些？",
        "expected_keywords": ["女儿", "5岁", "儿童"],
        "description": "Should remember family member information"
    },
    {
        "id": 26,
        "name": "Medication Tracking",
        "setup": {
            "user_id": 10006,
            "messages": [
                {"role": "user", "content": "我在吃阿司匹林和二甲双胍"},
                {"role": "assistant", "content": "记录了您正在服用阿司匹林和二甲双胍。"}
            ]
        },
        "query": "我现在吃的药会不会有冲突？",
        "expected_keywords": ["阿司匹林", "二甲双胍", "药物"],
        "description": "Should track current medications"
    },
    {
        "id": 27,
        "name": "Doctor Preference",
        "setup": {
            "user_id": 10007,
            "messages": [
                {"role": "user", "content": "我喜欢找李医生看病"},
                {"role": "assistant", "content": "好的，您偏好李医生。"}
            ]
        },
        "query": "帮我预约个医生",
        "expected_keywords": ["李医生", "偏好"],
        "description": "Should remember doctor preferences"
    },
    {
        "id": 28,
        "name": "Health Goal Tracking",
        "setup": {
            "user_id": 10008,
            "messages": [
                {"role": "user", "content": "我想减重10公斤"},
                {"role": "assistant", "content": "记录了您的减重目标：10公斤。"}
            ]
        },
        "query": "我的健康目标进展如何？",
        "expected_keywords": ["减重", "10公斤", "目标"],
        "description": "Should track health goals"
    },
    {
        "id": 29,
        "name": "Insurance Information",
        "setup": {
            "user_id": 10009,
            "messages": [
                {"role": "user", "content": "我有平安保险的高端医疗险"},
                {"role": "assistant", "content": "了解，您有平安保险的高端医疗险。"}
            ]
        },
        "query": "我的保险能覆盖这个检查吗？",
        "expected_keywords": ["平安", "高端医疗险", "保险"],
        "description": "Should remember insurance details"
    },
    {
        "id": 30,
        "name": "Complex Context Recall",
        "setup": {
            "user_id": 10010,
            "messages": [
                {"role": "user", "content": "我妈妈有糖尿病，爸爸有心脏病"},
                {"role": "assistant", "content": "记录了您的家族病史：母亲糖尿病，父亲心脏病。"}
            ]
        },
        "query": "我需要做哪些预防性检查？",
        "expected_keywords": ["糖尿病", "心脏", "家族", "预防"],
        "description": "Should use family history for recommendations"
    }
]

# Combined test cases
ALL_TEST_CASES = IDENTITY_TEST_CASES + MEM0_TEST_CASES

# Global tracking for debug information
debug_events = []
agent_calls = []
tool_calls = []
thinking_steps = []
mem0_events = []

async def test_v2_endpoint_enhanced(session, test_case):
    """Test V2 endpoint with enhanced logging and streaming"""
    global debug_events, agent_calls, tool_calls, thinking_steps, mem0_events
    
    # Reset tracking
    debug_events = []
    agent_calls = []
    tool_calls = []
    thinking_steps = []
    mem0_events = []
    
    try:
        # Setup memory if needed
        if "setup" in test_case:
            print_colored(f"  Setting up memory for user {test_case['setup']['user_id']}...", Colors.YELLOW)
            setup_data = {
                "user_id": test_case['setup']['user_id'],
                "messages": test_case['setup']['messages']
            }
            async with session.post(f"{BASE_URL}/v2/humansa/memory/add", json=setup_data) as resp:
                if resp.status != 200:
                    print_colored(f"    ❌ Memory setup failed: {resp.status}", Colors.RED)
                else:
                    print_colored(f"    ✅ Memory setup completed", Colors.GREEN)
            
            # Small delay to ensure memory is persisted
            await asyncio.sleep(0.5)
        
        # Prepare request data with debug flag
        user_id = test_case.get('setup', {}).get('user_id', 123)
        request_data = {
            "user_id": user_id,
            "messages": [{"role": "user", "content": test_case['query']}],
            "stream": True,  # Enable streaming for detailed output
            "debug": True    # Enable debug mode for enhanced logging
        }
        
        # Make request
        start_time = time.time()
        full_response = ""
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status != 200:
                error_text = await response.text()
                elapsed_time = time.time() - start_time
                return {
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "passed": False,
                    "response_time": elapsed_time,
                    "response": None,
                    "error": f"HTTP {response.status}: {error_text}",
                    "debug_info": {}
                }
            
            # Process streaming response
            print_colored("\n  📡 Streaming response:", Colors.CYAN)
            
            async for line in response.content:
                if line:
                    decoded = line.decode('utf-8').strip()
                    
                    # Parse SSE format
                    if decoded.startswith('data: '):
                        data_str = decoded[6:]  # Remove 'data: ' prefix
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            
                            # Handle debug events
                            if data.get('object') == 'debug.event' or data.get('debug'):
                                event = data.get('debug', data.get('event', data))
                                event_type = event.get('type', 'unknown')
                                
                                if event_type == 'thinking_start' or event_type == 'thinking_end':
                                    thought = event.get('thought', event.get('content', ''))
                                    if thought:
                                        print_colored(f"    💭 Thinking: {thought[:100]}...", Colors.CYAN)
                                        thinking_steps.append(thought)
                                
                                elif event_type == 'tool_call_start':
                                    tool = event.get('tool', 'unknown')
                                    input_data = event.get('input', {})
                                    print_colored(f"    🔧 Tool Call: {tool}", Colors.BLUE)
                                    print_colored(f"       Input: {json.dumps(input_data, ensure_ascii=False)[:100]}...", Colors.BLUE)
                                    tool_calls.append({"tool": tool, "input": input_data})
                                
                                elif event_type == 'tool_call_end':
                                    result = event.get('result', '')
                                    if result:
                                        print_colored(f"    📊 Tool Result: {str(result)[:100]}...", Colors.GREEN)
                                
                                elif event_type in ['memory', 'mem0_check', 'memory_context']:
                                    print_colored(f"    🧠 Mem0 Event: {event_type}", Colors.MAGENTA)
                                    mem0_events.append(event)
                                
                                elif 'agent' in str(event).lower():
                                    agent_name = event.get('agent', 'unknown')
                                    print_colored(f"    🤖 Agent: {agent_name}", Colors.YELLOW)
                                    agent_calls.append(agent_name)
                                
                                debug_events.append(event)
                            
                            # Handle regular content
                            elif 'choices' in data:
                                for choice in data.get('choices', []):
                                    delta = choice.get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        full_response += content
                                        # Don't print every character, just collect
                            
                            # Handle summary
                            elif data.get('object') == 'debug.summary':
                                summary = data.get('summary', {})
                                print_colored(f"\n    📊 Process Summary:", Colors.BOLD)
                                print_colored(f"       Total events: {summary.get('total_events', 0)}", Colors.CYAN)
                                print_colored(f"       Agent calls: {summary.get('agent_calls', 0)}", Colors.CYAN)
                                print_colored(f"       Tool calls: {summary.get('tool_calls', 0)}", Colors.CYAN)
                                print_colored(f"       Thinking steps: {summary.get('thinking_steps', 0)}", Colors.CYAN)
                                print_colored(f"       Memory events: {summary.get('memory_events', 0)}", Colors.CYAN)
                                
                        except json.JSONDecodeError:
                            pass  # Ignore non-JSON lines
            
            elapsed_time = time.time() - start_time
            
            # Process full response
            print_colored(f"\n  📝 Full Response:", Colors.GREEN)
            print_colored(f"    {full_response[:300]}{'...' if len(full_response) > 300 else ''}", Colors.GREEN)
            
            # Check for expected keywords
            found_keywords = []
            missing_keywords = []
            
            for keyword in test_case.get('expected_keywords', []):
                if keyword.lower() in full_response.lower():
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            # Check for not expected keywords
            found_not_expected = []
            for keyword in test_case.get('not_expected', []):
                if keyword.lower() in full_response.lower():
                    found_not_expected.append(keyword)
            
            # Determine pass/fail
            passed = len(missing_keywords) == 0 and len(found_not_expected) == 0
            
            # Create debug info summary
            debug_info = {
                "agent_calls": agent_calls,
                "tool_calls": tool_calls,
                "thinking_steps": len(thinking_steps),
                "mem0_events": len(mem0_events),
                "total_debug_events": len(debug_events)
            }
            
            return {
                "test_id": test_case['id'],
                "test_name": test_case['name'],
                "passed": passed,
                "response_time": elapsed_time,
                "response": full_response,  # Full response, not truncated
                "found_keywords": found_keywords,
                "missing_keywords": missing_keywords,
                "found_not_expected": found_not_expected,
                "error": None,
                "debug_info": debug_info
            }
                
    except asyncio.TimeoutError:
        return {
            "test_id": test_case['id'],
            "test_name": test_case['name'],
            "passed": False,
            "response_time": 30.0,
            "response": None,
            "error": "Request timeout (30s)",
            "debug_info": {}
        }
    except Exception as e:
        return {
            "test_id": test_case['id'],
            "test_name": test_case['name'],
            "passed": False,
            "response_time": 0,
            "response": None,
            "error": str(e),
            "debug_info": {}
        }


async def run_all_tests():
    """Run all test cases with enhanced logging"""
    print_section("Running Enhanced Humansa V2 Comprehensive Test Suite")
    print(f"Total test cases: {len(ALL_TEST_CASES)}")
    print(f"- Identity tests: {len(IDENTITY_TEST_CASES)}")
    print(f"- Mem0 tests: {len(MEM0_TEST_CASES)}")
    print_colored("Enhanced logging is ENABLED - showing full process details", Colors.CYAN)
    
    async with aiohttp.ClientSession() as session:
        # Check V2 health first
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print_colored(f"\n✅ V2 Health Check: {health['status']}", Colors.GREEN)
                    print(f"   Components: {health['components']}")
                    if 'mem0' in health['components']:
                        print_colored(f"   🧠 Mem0 Status: {health['components']['mem0']}", Colors.MAGENTA)
                else:
                    print_colored(f"❌ V2 Health Check Failed: {resp.status}", Colors.RED)
                    return
        except Exception as e:
            print_colored(f"❌ Cannot connect to V2 endpoint: {e}", Colors.RED)
            return
        
        # Run all tests
        results = []
        passed_count = 0
        
        for i, test_case in enumerate(ALL_TEST_CASES, 1):
            print_section(f"Test {i}/{len(ALL_TEST_CASES)}: {test_case['name']}")
            print(f"  Query: {test_case.get('query', 'N/A')}")
            print(f"  Description: {test_case['description']}")
            
            result = await test_v2_endpoint_enhanced(session, test_case)
            results.append(result)
            
            # Display result
            if result['passed']:
                passed_count += 1
                print_colored(f"\n  ✅ PASSED (Response time: {result['response_time']:.2f}s)", Colors.GREEN)
                if result['found_keywords']:
                    print_colored(f"  Found keywords: {', '.join(result['found_keywords'])}", Colors.GREEN)
            else:
                print_colored(f"\n  ❌ FAILED", Colors.RED)
                if result['error']:
                    print_colored(f"  Error: {result['error']}", Colors.RED)
                if result.get('missing_keywords'):
                    print_colored(f"  Missing keywords: {', '.join(result['missing_keywords'])}", Colors.YELLOW)
                if result.get('found_not_expected'):
                    print_colored(f"  Found unexpected: {', '.join(result['found_not_expected'])}", Colors.YELLOW)
            
            # Display debug info
            debug_info = result.get('debug_info', {})
            if debug_info:
                print_colored(f"\n  🔍 Debug Info:", Colors.CYAN)
                print(f"     Agents called: {len(debug_info.get('agent_calls', []))}")
                print(f"     Tools called: {len(debug_info.get('tool_calls', []))}")
                print(f"     Thinking steps: {debug_info.get('thinking_steps', 0)}")
                print(f"     Mem0 events: {debug_info.get('mem0_events', 0)}")
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Summary
        print_section("TEST SUMMARY")
        print(f"Total tests: {len(ALL_TEST_CASES)}")
        print_colored(f"Passed: {passed_count}", Colors.GREEN)
        print_colored(f"Failed: {len(ALL_TEST_CASES) - passed_count}", Colors.RED)
        print(f"Success rate: {(passed_count/len(ALL_TEST_CASES)*100):.1f}%")
        
        # Save results with debug info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"humansa_v2_enhanced_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "total_tests": len(ALL_TEST_CASES),
                "passed": passed_count,
                "failed": len(ALL_TEST_CASES) - passed_count,
                "success_rate": passed_count/len(ALL_TEST_CASES),
                "enhanced_logging": True,
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {filename}")
        
        # Failed tests details
        if passed_count < len(ALL_TEST_CASES):
            print_section("FAILED TESTS DETAILS")
            for result in results:
                if not result['passed']:
                    print_colored(f"\nTest {result['test_id']}: {result['test_name']}", Colors.RED)
                    if result.get('missing_keywords'):
                        print(f"  Missing: {', '.join(result['missing_keywords'])}")
                    if result.get('found_not_expected'):
                        print(f"  Unexpected: {', '.join(result['found_not_expected'])}")
                    if result.get('error'):
                        print(f"  Error: {result['error']}")
                    
                    # Show debug info for failed tests
                    debug_info = result.get('debug_info', {})
                    if debug_info and debug_info.get('agent_calls'):
                        print(f"  Agents used: {', '.join(debug_info['agent_calls'])}")
                    if debug_info and debug_info.get('tool_calls'):
                        print(f"  Tools used: {[t['tool'] for t in debug_info['tool_calls']]}")


if __name__ == "__main__":
    # Enable colored output on Windows
    if sys.platform == "win32":
        os.system("color")
    
    asyncio.run(run_all_tests())
TESTSCRIPT

# Make test script executable
chmod +x test_humansa_v2_comprehensive_enhanced.py

# Run the enhanced tests
echo -e "\n${CYAN}Running enhanced tests with full process logging...${NC}"
python3 test_humansa_v2_comprehensive_enhanced.py

# Step 7: Show server logs
echo -e "\n${YELLOW}Step 7: Server logs (last 50 lines):${NC}"
tail -n 50 server_v2_enhanced.log

# Step 8: Cleanup
echo -e "\n${YELLOW}Step 8: Test completed. Cleaning up...${NC}"
echo "Server is still running on PID $SERVER_PID"
echo "To stop the server, run: kill $SERVER_PID"
echo -e "\n${GREEN}✅ Enhanced Humansa V2 test environment completed!${NC}"

# Provide summary
echo -e "\n${BLUE}Summary:${NC}"
echo "- Test database: PostgreSQL on port 5456"
echo "- ML Server: Running on port 6001"
echo "- Endpoint: http://localhost:6001/v2/humansa/chat"
echo "- Memory endpoints: /v2/humansa/memory/status, /add, /search"
echo "- Enhanced logging: ENABLED"
echo "- Server logs: server_v2_enhanced.log"
echo "- Test results: humansa_v2_enhanced_test_results_*.json"
echo -e "\n${YELLOW}Note: Remember to kill the server process when done!${NC}"

# Optional: Auto-cleanup after tests
read -p "Do you want to stop the server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
    echo "Server stopped."
fi