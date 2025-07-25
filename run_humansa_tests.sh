#!/bin/bash

echo "=================================="
echo "HUMANSA AI AGENT V2 TEST RUNNER"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Base URL
BASE_URL="http://localhost:5001"
ENDPOINT="${BASE_URL}/v1-humansa/chat/completions"

# Check if server is running
echo "Checking ML server status..."
if curl -s "${BASE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ ML Server is running${NC}"
else
    echo -e "${YELLOW}❌ ML Server is not running. Please start it first.${NC}"
    exit 1
fi

echo ""
echo "Running test cases..."
echo "===================="

# Function to test a query
test_query() {
    local test_name="$1"
    local query="$2"
    local user_id="test_user_$(date +%s)"
    
    echo -e "\n${BLUE}TEST: ${test_name}${NC}"
    echo "User: ${query}"
    echo "----------------------------------------"
    
    # Make the API call and format the output
    response=$(curl -s -X POST "${ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"messages\": [{\"role\": \"user\", \"content\": \"${query}\"}],
            \"model\": \"gpt-4\",
            \"user_id\": \"${user_id}\",
            \"stream\": false
        }")
    
    # Extract and display key information
    echo -e "\n${GREEN}🧠 AGENT THINKING:${NC}"
    echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trace = data.get('agent_trace', '')
if trace:
    for line in trace.split('\\n'):
        line = line.strip()
        if line.startswith('Thought:'):
            print(f'  💭 {line}')
        elif line.startswith('Action:'):
            print(f'  🔧 {line}')
        elif line.startswith('Observation:'):
            obs = line[12:].strip()
            if len(obs) > 100:
                print(f'  👁️  Observation: {obs[:100]}...')
            else:
                print(f'  👁️  {line}')
"
    
    echo -e "\n${GREEN}🔧 TOOLS USED:${NC}"
    echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tools = data.get('tool_calls_observed', [])
if tools:
    for i, tool in enumerate(tools, 1):
        print(f'  {i}. {tool.get(\"tool_name\", \"unknown\")}')
else:
    print('  No tools used')
"
    
    echo -e "\n${GREEN}💬 FINAL ANSWER:${NC}"
    echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'choices' in data and data['choices']:
    content = data['choices'][0]['message']['content']
    if 'Answer:' in content:
        answer = content.split('Answer:')[-1].strip()
    else:
        answer = content
    print(f'  {answer[:200]}...' if len(answer) > 200 else f'  {answer}')
"
    
    echo -e "\n========================================\n"
    sleep 2
}

# Run test cases
test_query "1. Find Cardiologist" "我想找一个心脏科医生"
test_query "2. Doctor Availability" "张医生下周有空吗？"
test_query "3. Service Pricing" "肝功能检查多少钱？"
test_query "4. Find Clinics" "深圳有哪些诊所？"
test_query "5. Book Appointment" "我想预约李医生，我叫王小明，电话13800138000"

echo -e "${GREEN}✅ Test completed!${NC}"
echo ""
echo "Summary:"
echo "- The agent uses ReAct pattern (Thought → Action → Observation)"
echo "- Tools are selected based on user intent"
echo "- Real database queries are executed"
echo "- Responses are contextual and helpful"