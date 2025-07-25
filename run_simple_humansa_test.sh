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

<<<<<<< HEAD
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

ML_SERVER_PORT=6001 nohup python3 src/main.py --port 6001 > simple_test_server.log 2>&1 &
=======
# Step 3: Start ML server
echo -e "\n${YELLOW}Step 3: Starting ML server on port 6001...${NC}"

# Kill any existing process on port 6001
lsof -ti:6001 | xargs kill -9 2>/dev/null || true
sleep 2

ML_SERVER_PORT=6001 nohup python3 src/main.py > simple_test_server.log 2>&1 &
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
SERVER_PID=$!

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi
<<<<<<< HEAD
    # Extra cleanup for any lingering processes
    lsof -ti:6001 | xargs kill -9 2>/dev/null || true
=======
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
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

<<<<<<< HEAD
# Create output file with timestamp
OUTPUT_FILE="humansa_test_output_$(date +%Y%m%d_%H%M%S).md"
echo "Test output will be saved to: $OUTPUT_FILE"

python3 - "$OUTPUT_FILE" << 'PYTEST'
=======
python3 - << 'PYTEST'
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
import asyncio
import json
import aiohttp
import time
import sys
<<<<<<< HEAD
import os

# Get output file from command line argument
output_file = sys.argv[1] if len(sys.argv) > 1 else "humansa_test_output.md"

class SimpleHumansaTest:
    def __init__(self, output_file):
        self.base_url = "http://localhost:6001"
        self.endpoint = f"{self.base_url}/v1-humansa/chat/completions"
        self.output_file = output_file
        self.output_content = []
    
    def log(self, text):
        """Log to both console and markdown file."""
        print(text)
        self.output_content.append(text)
    
    async def test_query(self, test_name, query):
        """Run a single test query."""
        self.log(f"\n{'='*60}")
        self.log(f"TEST: {test_name}")
        self.log(f"{'='*60}")
        self.log(f"Query: {query}")
        self.log("-"*40)
=======

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
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
        
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
<<<<<<< HEAD
                        self.log(f"❌ ERROR: {result['error']}")
=======
                        print(f"❌ ERROR: {result['error']}")
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
                        return False
                    
                    # Check if we got a response
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
<<<<<<< HEAD
                        self.log(f"✅ Response: {content[:200]}{'...' if len(content) > 200 else ''}")
=======
                        print(f"✅ Response: {content[:200]}{'...' if len(content) > 200 else ''}")
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
                        
                        # Check for agent trace (shows tool usage)
                        if "agent_trace" in result:
                            trace = result["agent_trace"]
<<<<<<< HEAD
                            self.log("\n**Agent Trace:**")
                            self.log("```")
                            self.log(trace[:500] + "..." if len(trace) > 500 else trace)
                            self.log("```")
                            if "Action:" in trace:
                                self.log(f"✅ Agent used tools (ReAct pattern detected)")
                                # Count tool calls
                                tool_count = trace.count("Action:")
                                self.log(f"   Tools called: {tool_count}")
                            else:
                                self.log("⚠️  No tool usage detected")
                    else:
                        self.log("❌ No response content")
                        return False
                    
                    self.log(f"⏱️  Response time: {duration:.2f}s")
=======
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
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
                    
                    # Check for database errors in trace
                    if "agent_trace" in result:
                        trace = result["agent_trace"]
                        if "connection to server at" in trace and "failed" in trace:
<<<<<<< HEAD
                            self.log("❌ Database connection error detected!")
=======
                            print("❌ Database connection error detected!")
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
                            return False
                    
                    return True
                    
        except Exception as e:
<<<<<<< HEAD
            self.log(f"❌ Exception: {e}")
=======
            print(f"❌ Exception: {e}")
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
            return False
    
    async def run_tests(self):
        """Run the 3 essential tests."""
<<<<<<< HEAD
        self.log("# Humansa AI Agent V2 - Test Results\n")
        self.log(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log("## Test Execution\n")
        self.log("Running 3 Essential Humansa Tests...")
        self.log("="*60)
=======
        print("\nRunning 3 Essential Humansa Tests...")
        print("="*60)
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
        
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
<<<<<<< HEAD
        self.log("\n" + "="*60)
        self.log("## TEST SUMMARY")
        self.log("="*60)
=======
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
<<<<<<< HEAD
        self.log("\n| Test Name | Status |")
        self.log("|-----------|--------|")
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"| {test_name} | {status} |")
        
        self.log(f"\n**Total**: {passed}/{total} passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            self.log("\n🎉 **All tests passed!**")
        else:
            self.log("\n❌ **Some tests failed. Check the database connection and tool configuration.**")
        
        # Write to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output_content))
        print(f"\n📄 Full test report saved to: {self.output_file}")
=======
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed. Check the database connection and tool configuration.")
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
        
        return passed == total

# Run the tests
async def main():
<<<<<<< HEAD
    tester = SimpleHumansaTest(output_file)
=======
    tester = SimpleHumansaTest()
>>>>>>> a9c69345cb75216c9f80d28d788de04305a8356f
    success = await tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
PYTEST

echo -e "\n${GREEN}✅ Simple test completed!${NC}"
echo -e "\nServer logs are available in: simple_test_server.log"