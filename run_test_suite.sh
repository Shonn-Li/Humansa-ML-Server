#!/bin/bash

echo "=========================================="
echo "HUMANSA AI AGENT V2 - COMPLETE TEST SUITE"
echo "=========================================="
echo ""

# Configuration
TEST_PORT=6001
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "youwo-ml-venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please run: python3 -m venv youwo-ml-venv && source youwo-ml-venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source youwo-ml-venv/bin/activate

# Check if server is already running on any port
if lsof -ti:5001 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ML Server already running on port 5001${NC}"
    echo "Running tests against existing server..."
    python3 test_humansa_fixed.py 5001
elif lsof -ti:$TEST_PORT > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Test server already running on port $TEST_PORT${NC}"
    echo "Running tests against existing test server..."
    python3 test_humansa_fixed.py $TEST_PORT
else
    echo -e "${YELLOW}Starting test ML server on port $TEST_PORT...${NC}"
    
    # Start ML server in background
    PORT=$TEST_PORT nohup python3 src/main.py > test_server_$TEST_PORT.log 2>&1 &
    SERVER_PID=$!
    
    echo "Test server started with PID: $SERVER_PID"
    echo "Waiting for server to be ready..."
    
    # Wait for server to start
    MAX_WAIT=30
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        if curl -s http://localhost:$TEST_PORT/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Test server is ready on port $TEST_PORT${NC}"
            break
        fi
        sleep 1
        WAITED=$((WAITED + 1))
        echo -ne "\rWaiting... ${WAITED}s"
    done
    echo ""
    
    if [ $WAITED -eq $MAX_WAIT ]; then
        echo -e "${RED}❌ Server failed to start${NC}"
        echo "Last 10 lines of server log:"
        tail -10 test_server_$TEST_PORT.log
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    # Run tests
    echo -e "\n${YELLOW}Running Humansa AI Agent V2 tests...${NC}"
    python3 test_humansa_fixed.py $TEST_PORT
    
    # Cleanup
    echo -e "\n${YELLOW}Stopping test server...${NC}"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo -e "${GREEN}✅ Test server stopped${NC}"
fi

echo -e "\n${GREEN}✨ Test suite completed!${NC}"