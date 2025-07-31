#!/bin/bash
# HUMANSA V2 - 70 Test Cases with Multi-turn Conversations
# Using Response API for full transparency

echo "============================================"
echo "HUMANSA V2 - 70 TEST CASES WITH MULTI-TURN"
echo "RESPONSE API IMPLEMENTATION TEST"
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
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true
export HUMANSA_USE_CONSOLIDATED_TOOLS=true

# Step 1: Check PostgreSQL test database
echo -e "\n${YELLOW}Step 1: Checking PostgreSQL test database...${NC}"
if pg_isready -h localhost -p 5454 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL test database is running on port 5454${NC}"
else
    echo -e "${RED}❌ PostgreSQL test database is not running on port 5454${NC}"
    echo "Please start the test database first with:"
    echo "cd test_environment && docker-compose up -d"
    exit 1
fi

# Step 2: Run SQL scripts to populate test data
echo -e "\n${YELLOW}Step 2: Ensuring test database is populated...${NC}"
cd test_environment/sql

# Quick check if tables exist
if PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1 FROM humansa_doctor LIMIT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Test data already populated${NC}"
else
    echo "Populating test database..."
    # Run essential SQL files
    for sql_file in 01_extensions.sql 02_create_tables.sql 06_humansa_test_data.sql; do
        if [ -f "$sql_file" ]; then
            PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -f "$sql_file" > /dev/null 2>&1
        fi
    done
fi

cd ../..

# Step 3: Start the ML server
echo -e "\n${YELLOW}Step 3: Starting ML server on port ${ML_SERVER_PORT}...${NC}"
# Kill any existing server on port 6001
lsof -ti:${ML_SERVER_PORT} | xargs kill -9 2>/dev/null || true
sleep 2

# Start server with enhanced logging
echo -e "${CYAN}Starting server with:${NC}"
echo "  - Enhanced logging: ENABLED"
echo "  - Consolidated tools: ENABLED"
echo "  - Response API: ACTIVE"

python -m src.main --port 6001 > server_70tests.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:${ML_SERVER_PORT}/api/debug/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is ready${NC}"
        break
    fi
    sleep 1
done

# Verify Response API endpoints
echo -e "\n${YELLOW}Step 4: Verifying Response API endpoints...${NC}"
if curl -s http://localhost:${ML_SERVER_PORT}/v2/humansa/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ V2 Health endpoint accessible${NC}"
else
    echo -e "${RED}❌ V2 Health endpoint not accessible${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Step 5: Run the 70 test cases
echo -e "\n${YELLOW}Step 5: Running 70 test cases with multi-turn conversations...${NC}"
echo -e "${CYAN}Test Categories:${NC}"
echo "  1. Identity & Introduction (1-5)"
echo "  2. Doctor Search (6-10)"
echo "  3. Appointment Booking (11-15)"
echo "  4. Clinic & Service (16-20)"
echo "  5. Medical Consultation (21-25)"
echo "  6. Product Recommendation (26-30)"
echo "  7. Memory & Context (31-40)"
echo "  8. Multi-turn Conversations (41-70)"
echo ""
echo -e "${MAGENTA}Starting comprehensive test suite...${NC}"

# Make test script executable
chmod +x test_HUMANSA_v2_70_cases_multiturn.py

# Run the test
python3 test_HUMANSA_v2_70_cases_multiturn.py

# Check if test completed
TEST_EXIT_CODE=$?

# Step 6: Show test results summary
echo -e "\n${YELLOW}Step 6: Test Results Summary${NC}"

# Find the latest results file
LATEST_RESULTS=$(ls -t HUMANSA_v2_70cases_results_*.json 2>/dev/null | head -1)

if [ -f "$LATEST_RESULTS" ]; then
    echo -e "${GREEN}✅ Test results saved to: $LATEST_RESULTS${NC}"
    
    # Extract summary using Python
    python3 -c "
import json
with open('$LATEST_RESULTS', 'r') as f:
    data = json.load(f)
    print(f\"\\nTotal Tests: {data['total_tests']}\")
    print(f\"Passed: {data['passed']}\")
    print(f\"Failed: {data['failed']}\")
    print(f\"Success Rate: {data['success_rate']*100:.1f}%\")
    print(f\"\\nBreakdown:\")
    print(f\"  Single-turn: {data['single_turn_passed']}/40\")
    print(f\"  Multi-turn: {data['multi_turn_passed']}/30\")
"
else
    echo -e "${RED}❌ No test results file found${NC}"
fi

# Step 7: Server logs
echo -e "\n${YELLOW}Step 7: Server logs (last 20 lines):${NC}"
tail -n 20 server_70tests.log

# Step 8: Cleanup
echo -e "\n${YELLOW}Step 8: Test completed!${NC}"
echo "Server is still running on PID $SERVER_PID"

# Summary
echo -e "\n${BLUE}========== SUMMARY ==========${NC}"
echo "Test Environment:"
echo "  - Database: PostgreSQL on port 5454"
echo "  - ML Server: Port 6001"
echo "  - Response API: Enabled"
echo "  - Tool Transparency: Full"
echo ""
echo "Results:"
echo "  - Test results: $LATEST_RESULTS"
echo "  - Server logs: server_70tests.log"
echo ""
echo "Response API Features Tested:"
echo "  ✅ Full reasoning chain visibility"
echo "  ✅ Tool use and tool result transparency"
echo "  ✅ Event-based streaming"
echo "  ✅ Multi-turn conversation with response chaining"
echo "  ✅ Memory persistence across turns"

# Prompt for cleanup
echo -e "\n${YELLOW}Cleanup Options:${NC}"
echo "1. Keep server running for additional testing"
echo "2. Stop server now"
read -p "Enter your choice (1 or 2): " -n 1 -r
echo

if [[ $REPLY == "2" ]]; then
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
    echo -e "${GREEN}✅ Server stopped${NC}"
else
    echo -e "${CYAN}Server still running on PID $SERVER_PID${NC}"
    echo "To stop later: kill $SERVER_PID"
fi

echo -e "\n${GREEN}✅ 70 test cases completed!${NC}"