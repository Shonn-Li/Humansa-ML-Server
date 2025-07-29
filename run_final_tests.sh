#!/bin/bash
# Final test runner with proper environment loading

echo "============================================"
echo "FINAL TEST RUNNER - Memory & Doctor Tests"
echo "With proper .env loading and Azure OpenAI"
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

# Step 1: Load environment variables from .env
echo -e "\n${YELLOW}Step 1: Loading environment variables...${NC}"
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✅ Loaded .env file${NC}"
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Override with test-specific settings
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true

# Map Azure credentials
export AZURE_OPENAI_API_KEY="${AZURE_INFERENCE_CREDENTIAL}"
# Use the correct Azure OpenAI endpoint format
export AZURE_OPENAI_ENDPOINT="https://youwoai-dev-resource.openai.azure.com/"

echo -e "${BLUE}Environment Configuration:${NC}"
echo "  DB: ${DB_NAME} on port ${DB_PORT}"
echo "  ML Server: Port ${ML_SERVER_PORT}"
echo "  Azure API Key: $([ -n "$AZURE_OPENAI_API_KEY" ] && echo 'Set' || echo 'Not set')"
echo "  OpenAI API Key: $([ -n "$OPENAI_API_KEY" ] && echo 'Set' || echo 'Not set')"

# Step 2: Verify test database
echo -e "\n${YELLOW}Step 2: Checking test database...${NC}"
if PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Test database is running${NC}"
else
    echo -e "${RED}❌ Test database not found on port 5454${NC}"
    echo "Start it with: ./run_humansa_test_environment_v2_enhanced.sh"
    exit 1
fi

# Step 3: Kill existing server
echo -e "\n${YELLOW}Step 3: Checking for existing ML server...${NC}"
if lsof -i :6001 > /dev/null 2>&1; then
    echo "Killing existing server on port 6001..."
    lsof -ti :6001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Step 4: Activate virtual environment
echo -e "\n${YELLOW}Step 4: Activating virtual environment...${NC}"
if [ -f "youwo-ml-venv/bin/activate" ]; then
    source youwo-ml-venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    exit 1
fi

# Step 5: Start ML server
echo -e "\n${YELLOW}Step 5: Starting ML server...${NC}"
python3 -m src.main --port 6001 > final_test_server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server
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
    echo -e "\n${RED}❌ Server failed to start${NC}"
    tail -n 50 final_test_server.log
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Step 6: Check Mem0 status
echo -e "\n${YELLOW}Step 6: Checking Mem0 status...${NC}"
MEM0_STATUS=$(curl -s http://localhost:6001/v2/humansa/memory/status)
echo "$MEM0_STATUS" | python3 -m json.tool || echo "Status: $MEM0_STATUS"

# Check if Mem0 is using Azure
if echo "$MEM0_STATUS" | grep -q "mem0"; then
    echo -e "${GREEN}✅ Mem0 is initialized${NC}"
    
    # Check Azure configuration in logs
    echo -e "\n${YELLOW}Checking Mem0 configuration in logs...${NC}"
    grep -i "configuring mem0" final_test_server.log | tail -5
else
    echo -e "${YELLOW}⚠️ Mem0 may not be fully initialized${NC}"
fi

# Step 7: Run memory tests
echo -e "\n${YELLOW}Step 7: Running memory integration tests...${NC}"
python3 test_mem0_v2_integration_fixed.py

MEM0_TEST_RESULT=$?
if [ $MEM0_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Memory tests passed${NC}"
else
    echo -e "${RED}❌ Memory tests failed${NC}"
    echo "Checking for Mem0 errors in server log..."
    grep -i "mem0.*error\|failed to initialize mem0" final_test_server.log | tail -10
fi

# Step 8: Run doctor tests
echo -e "\n${YELLOW}Step 8: Running doctor tools tests...${NC}"
python3 test_doctor_tools_fixed.py

DOCTOR_TEST_RESULT=$?
if [ $DOCTOR_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Doctor tests passed${NC}"
else
    echo -e "${RED}❌ Doctor tests failed${NC}"
fi

# Step 9: Summary
echo -e "\n${BLUE}============================================${NC}"
echo -e "${BLUE}FINAL TEST SUMMARY${NC}"
echo -e "${BLUE}============================================${NC}"

# Overall status
if [ $MEM0_TEST_RESULT -eq 0 ] && [ $DOCTOR_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
fi

echo ""
echo "Server: Running on port 6001 (PID: $SERVER_PID)"
echo "Database: test4 on port 5454"
echo "Logs: final_test_server.log"
echo "Memory test output: See console above"
echo "Doctor test results: doctor_tools_test_results_*.json"

# Check if memories are persisting
echo -e "\n${YELLOW}Final Memory Check:${NC}"
curl -s -X GET "http://localhost:6001/v2/humansa/memory/context/test_user_10001" | python3 -m json.tool | grep -E "memory_count|recent_memories" || echo "Could not retrieve memory context"

echo -e "\n${YELLOW}Stop the server with: kill $SERVER_PID${NC}"

# Optional cleanup
echo -e "\n${YELLOW}Stop the server now? (y/n)${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill $SERVER_PID 2>/dev/null || true
    echo "Server stopped."
fi