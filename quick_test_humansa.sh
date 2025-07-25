#!/bin/bash

echo "=================================="
echo "HUMANSA AI AGENT V2 - QUICK TEST"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check which port to use
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    BASE_URL="http://localhost:5001"
    echo -e "${GREEN}✅ Using existing ML server on port 5001${NC}"
elif curl -s http://localhost:6001/health > /dev/null 2>&1; then
    BASE_URL="http://localhost:6001"
    echo -e "${GREEN}✅ Using test server on port 6001${NC}"
else
    echo -e "${YELLOW}Starting temporary ML server...${NC}"
    
    # Quick start ML server
    source youwo-ml-venv/bin/activate 2>/dev/null || {
        echo -e "${RED}❌ Virtual environment not found${NC}"
        exit 1
    }
    
    # Start server in background
    nohup python3 src/main.py > quick_test_server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server
    echo "Waiting for server to start..."
    for i in {1..20}; do
        if curl -s http://localhost:5001/health > /dev/null 2>&1; then
            BASE_URL="http://localhost:5001"
            echo -e "${GREEN}✅ ML server started on port 5001${NC}"
            break
        fi
        sleep 1
    done
    
    if [ -z "$BASE_URL" ]; then
        echo -e "${RED}❌ Failed to start ML server${NC}"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
fi

ENDPOINT="${BASE_URL}/v1-humansa/chat/completions"

# Function to run a single test
run_test() {
    local test_name="$1"
    local query="$2"
    
    echo -e "\n${BLUE}TEST: ${test_name}${NC}"
    echo "Query: ${query}"
    echo "----------------------------------------"
    
    # Make API call
    response=$(curl -s -X POST "${ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"messages\": [{\"role\": \"user\", \"content\": \"${query}\"}],
            \"model\": \"gpt-4\",
            \"user_id\": \"quick_test_user\",
            \"stream\": false
        }" 2>/dev/null)
    
    # Check for error
    if echo "$response" | grep -q '"error"'; then
        echo -e "${RED}❌ Error:${NC}"
        echo "$response" | python3 -m json.tool | grep -A2 '"error"'
        return
    fi
    
    # Extract and display key information
    echo -e "\n${GREEN}Agent Trace:${NC}"
    echo "$response" | python3 -c '
import sys, json
data = json.load(sys.stdin)
trace = data.get("agent_trace", "No trace")
if trace and trace != "No trace":
    lines = trace.split("\\n")
    for line in lines[:10]:  # First 10 lines
        if line.strip():
            print(f"  {line.strip()}")
    if len(lines) > 10:
        print("  ...")
'
    
    echo -e "\n${GREEN}Tools Used:${NC}"
    echo "$response" | python3 -c '
import sys, json
data = json.load(sys.stdin)
tools = data.get("tool_calls_observed", [])
if tools:
    for tool in tools:
        print(f"  - {tool.get('tool_name', 'unknown')}")
else:
    print("  No tools called")
'
    
    echo -e "\n${GREEN}Final Answer:${NC}"
    echo "$response" | python3 -c '
import sys, json
data = json.load(sys.stdin)
if "choices" in data and data["choices"]:
    content = data["choices"][0]["message"]["content"]
    if "Answer:" in content:
        answer = content.split("Answer:")[-1].strip()
    else:
        answer = content
    print(f"  {answer[:200]}..." if len(answer) > 200 else f"  {answer}")
'
    
    echo -e "\n${GREEN}✅ Test completed${NC}"
}

# Run a few quick tests
echo -e "\n${YELLOW}Running 5 quick tests to demonstrate the Humansa AI Agent V2...${NC}"

run_test "1. Find Doctor" "我想找一个心脏科医生"
run_test "2. Check Availability" "张医生下周有空吗？"
run_test "3. Service Pricing" "肝功能检查多少钱？"
run_test "4. Find Clinic" "深圳有哪些诊所？"
run_test "5. Book Appointment" "我想预约李医生，我叫王小明，电话13800138000"

# Cleanup
if [ ! -z "$SERVER_PID" ]; then
    echo -e "\n${YELLOW}Stopping temporary server...${NC}"
    kill $SERVER_PID 2>/dev/null
fi

echo -e "\n${GREEN}✨ Quick test completed!${NC}"
echo ""
echo "Summary:"
echo "- The Humansa AI Agent V2 uses ReAct pattern for reasoning"
echo "- Tools are automatically selected based on user intent"
echo "- Real database queries are executed"
echo "- Responses are contextual and in Chinese"
echo ""
echo "For full 20-test suite, run: ./run_humansa_test_environment.sh"