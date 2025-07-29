#!/bin/bash
#
# One-command test script for YouWoAI ML Server
# Usage: ./test.sh [quick|full|direct]
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test mode
TEST_MODE=${1:-quick}

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}YouWoAI ML Server Test Runner${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Test mode: ${YELLOW}$TEST_MODE${NC}"
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Virtual environment not activated. Activating...${NC}"
    source youwo-ml-venv/bin/activate || {
        echo -e "${RED}Failed to activate virtual environment!${NC}"
        echo "Please ensure you have created the virtual environment:"
        echo "  python -m venv youwo-ml-venv"
        echo "  source youwo-ml-venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    }
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    
    # Kill test server if running
    if [[ -n "$TEST_SERVER_PID" ]]; then
        echo "Stopping test server (PID: $TEST_SERVER_PID)..."
        kill $TEST_SERVER_PID 2>/dev/null || true
        wait $TEST_SERVER_PID 2>/dev/null || true
    fi
    
    # Kill any orphaned test servers on port 5002
    lsof -ti:5002 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Function to wait for server
wait_for_server() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}Waiting for server on port $port...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$port/health > /dev/null; then
            echo -e "${GREEN}✓ Server ready on port $port${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $((attempt % 5)) -eq 0 ]; then
            echo "  Still waiting... ($attempt/$max_attempts)"
        fi
        sleep 1
    done
    
    echo -e "${RED}✗ Server failed to start on port $port${NC}"
    return 1
}

# Handle different test modes
case $TEST_MODE in
    direct)
        echo -e "${BLUE}Running direct endpoint tests (no server needed)...${NC}"
        echo ""
        python test/core/validate.py
        ;;
        
    quick)
        echo -e "${BLUE}Running quick validation tests (no server needed)...${NC}"
        echo ""
        python test/core/validate.py
        echo ""
        echo -e "${GREEN}Quick tests completed!${NC}"
        ;;
        
    full)
        echo -e "${BLUE}Running comprehensive test suite (20 tests)...${NC}"
        echo -e "${YELLOW}This will take approximately 5-10 minutes${NC}"
        echo ""
        
        # Run the comprehensive tests (direct endpoint version)
        python test/core/test_comprehensive_detailed.py
        
        echo ""
        echo -e "${GREEN}Comprehensive tests completed!${NC}"
        ;;
        
    *)
        echo -e "${RED}Invalid test mode: $TEST_MODE${NC}"
        echo ""
        echo "Usage: ./test.sh [mode]"
        echo ""
        echo "Available modes:"
        echo "  direct  - Direct endpoint tests (no server needed, fastest)"
        echo "  quick   - Quick validation tests (5 tests, ~2-3 minutes) [default]"
        echo "  full    - Comprehensive test suite (30+ tests, ~10-15 minutes)"
        echo ""
        echo "Examples:"
        echo "  ./test.sh           # Run quick tests (default)"
        echo "  ./test.sh direct    # Run direct tests (fastest)"
        echo "  ./test.sh full      # Run all tests"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}Test run completed successfully!${NC}"
echo -e "${BLUE}============================================${NC}"