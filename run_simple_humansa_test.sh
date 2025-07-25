#!/bin/bash
# Simple Humansa AI Agent V2 Test - 3 Essential Tests

echo "============================================"
echo "HUMANSA AI AGENT V2 - SIMPLE TEST (3 CASES)"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Check if virtual environment exists
echo -e "\n${YELLOW}Step 1: Checking virtual environment...${NC}"
if [ ! -d "youwo-ml-venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run: python3 -m venv youwo-ml-venv && source youwo-ml-venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Step 2: Activate virtual environment
echo -e "\n${YELLOW}Step 2: Activating virtual environment...${NC}"
source youwo-ml-venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Step 3: Start ML server
echo -e "\n${YELLOW}Step 3: Starting ML server on port 6001...${NC}"

# Kill any existing process on port 6001
lsof -ti:6001 | xargs kill -9 2>/dev/null || true
sleep 2

ML_SERVER_PORT=6001 nohup python3 src/main.py > simple_test_server.log 2>&1 &
SERVER_PID=$!

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi
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
    tail -20 simple_test_server.log
    exit 1
fi

# Step 4: Run 3 simple tests
echo -e "\n${YELLOW}Step 4: Running 3 simple tests...${NC}"

python3 - << 'PYTEST'
import asyncio
import json
import aiohttp
import time
import sys

class SimpleHumansaTest:
    def __init__(self):
        self.base_url = "http://localhost:6001"
        self.endpoint = f"{self.base_url}/v1-humansa/chat/completions"
    
    async def test_query(self, test_name, query):
        """Run a single test query."""
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print("-"*40)
        
        start_time = time.time()
        
        payload = {
            "messages": [{"role": "user", "content": query}],
            "model": "gpt-4",
            "user_id": "test_user",
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    # Check for error
                    if "error" in result:
                        print(f"❌ ERROR: {result['error']}")
                        return False
                    
                    # Check if we got a response
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                        print(f"✅ Response: {content[:200]}{'...' if len(content) > 200 else ''}")
                        
                        # Check for agent trace (shows tool usage)
                        if "agent_trace" in result:
                            trace = result["agent_trace"]
                            if "Action:" in trace:
                                print(f"✅ Agent used tools (ReAct pattern detected)")
                                # Count tool calls
                                tool_count = trace.count("Action:")
                                print(f"   Tools called: {tool_count}")
                            else:
                                print("⚠️  No tool usage detected")
                    else:
                        print("❌ No response content")
                        return False
                    
                    print(f"⏱️  Response time: {duration:.2f}s")
                    
                    # Check for database errors in trace
                    if "agent_trace" in result:
                        trace = result["agent_trace"]
                        if "connection to server at" in trace and "failed" in trace:
                            print("❌ Database connection error detected!")
                            return False
                    
                    return True
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
    
    async def run_tests(self):
        """Run the 3 essential tests."""
        print("\nRunning 3 Essential Humansa Tests...")
        print("="*60)
        
        tests = [
            ("Find Doctor", "我想找一个心脏科医生"),
            ("Book Appointment", "预约王医生，我叫李明，电话13800138000"),
            ("Emergency", "胸痛很严重，需要看医生")
        ]
        
        results = []
        for test_name, query in tests:
            success = await self.test_query(test_name, query)
            results.append((test_name, success))
            await asyncio.sleep(1)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed. Check the database connection and tool configuration.")
        
        return passed == total

# Run the tests
async def main():
    tester = SimpleHumansaTest()
    success = await tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
PYTEST

echo -e "\n${GREEN}✅ Simple test completed!${NC}"
echo -e "\nServer logs are available in: simple_test_server.log"