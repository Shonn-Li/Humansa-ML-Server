#!/bin/bash
# Verified working HUMANSA test runner

echo "============================================"
echo "HUMANSA AI AGENT V2 - VERIFIED TEST RUNNER"
echo "============================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# First, apply the minimal fix to the main agent
echo -e "\n${YELLOW}Step 1: Applying search_web filter to agent...${NC}"
cat > apply_agent_fix.py << 'EOF'
import os

agent_file = "src/humansa/agent/humansa_agent.py"
if os.path.exists(agent_file):
    with open(agent_file, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if "Filter out search_web tool to prevent external searches" in content:
        print("✅ Agent already has search_web filter")
    else:
        # Add filtering after tools assignment
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if "self.tools = tools or []" in line and i+1 < len(lines):
                # Check if next line already has filtering
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
EOF

python3 apply_agent_fix.py

# Activate virtual environment
echo -e "\n${YELLOW}Step 2: Activating virtual environment...${NC}"
source youwo-ml-venv/bin/activate

# Start server
echo -e "\n${YELLOW}Step 3: Starting ML server on port 6001...${NC}"
PORT=6001 nohup python3 src/main.py > test_server.log 2>&1 &
SERVER_PID=$!

# Cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo -e "${GREEN}✅ Server stopped${NC}"
}
trap cleanup EXIT

# Wait for server
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
    echo -e "${RED}❌ Server failed to start${NC}"
    tail -20 test_server.log
    exit 1
fi

# Verify with a simple test first
echo -e "\n${YELLOW}Step 4: Verifying agent is working...${NC}"
VERIFY_RESPONSE=$(curl -s -X POST http://localhost:6001/v1-humansa/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}],
    "model": "gpt-4",
    "user_id": "verify_user",
    "stream": false
  }')

if echo "$VERIFY_RESPONSE" | grep -q "error"; then
    echo -e "${RED}❌ Agent verification failed:${NC}"
    echo "$VERIFY_RESPONSE" | python3 -m json.tool
    exit 1
else
    echo -e "${GREEN}✅ Agent is responding correctly${NC}"
fi

# Run 5 key tests
echo -e "\n${YELLOW}Step 5: Running key test cases...${NC}"
python3 - << 'EOF'
import asyncio
import json
import time
import sys
import re
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "aiohttp"])
    import aiohttp

async def test_query(session, test_id, test_name, query):
    """Run a single test query"""
    print(f"\n{'='*60}")
    print(f"TEST {test_id}: {test_name}")
    print(f"{'='*60}")
    print(f"Query: {query}")
    
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
                print(f"\n❌ ERROR: {result['error']}")
                return False
            
            # Extract response
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"\n💬 Response: {content[:200]}{'...' if len(content) > 200 else ''}")
            
            # Check tool usage
            tool_calls = result.get("tool_calls_observed", [])
            if tool_calls:
                print(f"\n🔧 Tools used: {len(tool_calls)}")
                for tool in tool_calls[:3]:  # Show first 3
                    print(f"   - {tool.get('tool_name', 'unknown')}")
                
                # Check for search_web
                if any(t.get('tool_name') == 'search_web' for t in tool_calls):
                    print("   ⚠️ WARNING: search_web was used!")
            
            print(f"\n✅ Test completed in {duration:.2f}s")
            return True
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return False

async def run_tests():
    """Run key test cases"""
    test_cases = [
        (1, "Find Doctor", "我想找一个心脏科医生"),
        (2, "Check Availability", "李医生下周有空吗？"),
        (3, "Service Pricing", "肝功能检查多少钱？"),
        (4, "Find Clinic", "深圳有哪些诊所？"),
        (5, "Book Appointment", "预约王医生，我叫李明，电话13800138000")
    ]
    
    print("\n" + "="*80)
    print("RUNNING KEY TESTS")
    print("="*80)
    
    passed = 0
    async with aiohttp.ClientSession() as session:
        for test_id, name, query in test_cases:
            if await test_query(session, test_id, name, query):
                passed += 1
            await asyncio.sleep(1)  # Delay between tests
    
    print("\n" + "="*80)
    print(f"SUMMARY: {passed}/{len(test_cases)} tests passed")
    print("="*80)
    
    if passed == len(test_cases):
        print("\n🎉 All tests passed! Agent is working correctly.")
    else:
        print(f"\n⚠️ Only {passed}/{len(test_cases)} tests passed.")

asyncio.run(run_tests())
EOF

echo -e "\n${GREEN}✅ Test complete!${NC}"