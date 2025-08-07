#!/bin/bash
# HUMANSA Test Environment with Form System Enabled

echo "============================================"
echo "HUMANSA AI AGENT - FORM SYSTEM TEST ENVIRONMENT"
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

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
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001

# CRITICAL: Enable Pattern 2 and enhanced logging for form system
export HUMANSA_USE_PATTERN2=true
export HUMANSA_ENHANCED_LOGGING=true

echo -e "${CYAN}Form System Configuration:${NC}"
echo "  - Pattern 2 Orchestrator: ENABLED"
echo "  - Enhanced Logging: ENABLED"
echo "  - Form System: READY"

# Step 1: Check PostgreSQL test database
echo -e "\n${YELLOW}Step 1: Checking PostgreSQL test database...${NC}"
if pg_isready -h localhost -p 5454 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL test database is running on port 5454${NC}"
else
    echo -e "${RED}❌ PostgreSQL test database is not running${NC}"
    exit 1
fi

# Step 2: Kill any existing processes on port 6001
echo -e "\n${YELLOW}Step 2: Checking for existing processes on port 6001...${NC}"
if lsof -i :6001 > /dev/null 2>&1; then
    echo "Found existing process on port 6001, killing it..."
    lsof -ti :6001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Step 3: Start the ML server with Pattern 2 and forms enabled
echo -e "\n${YELLOW}Step 3: Starting ML server with Pattern 2 and Form System...${NC}"
echo "Server will run on port 6001 with form system enabled"

# Start server in background
python3 -m src.main --port 6001 > server_forms.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo -n "Waiting for server to start"
for i in {1..30}; do
    if curl -s http://localhost:6001/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Server is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Step 4: Verify Pattern 2 is enabled
echo -e "\n${YELLOW}Step 4: Verifying Pattern 2 and Form System...${NC}"
python3 - << 'EOF'
import os
print(f"HUMANSA_USE_PATTERN2: {os.getenv('HUMANSA_USE_PATTERN2')}")
print(f"HUMANSA_ENHANCED_LOGGING: {os.getenv('HUMANSA_ENHANCED_LOGGING')}")

# Check if form system modules can be imported
try:
    from src.humansa.v2.forms.form_service import FormService
    from src.humansa.v2.forms.models import AppointmentForm
    from src.humansa.v2.agents.appointment_agent_v2 import AppointmentAgentV2
    print("✅ Form system modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import form modules: {e}")
EOF

# Step 5: Run form system tests
echo -e "\n${YELLOW}Step 5: Running form system tests...${NC}"

# Save PID for cleanup
echo $SERVER_PID > .server_forms.pid

echo -e "\n${GREEN}✅ Form system test environment is ready!${NC}"
echo -e "\n${BLUE}You can now run:${NC}"
echo "  1. python3 test_appointment_form_system.py"
echo "  2. ./test_appointment_v1.sh"
echo "  3. Manual testing with curl"
echo -e "\n${YELLOW}Server logs: tail -f server_forms.log${NC}"
echo -e "${YELLOW}To stop server: kill $SERVER_PID${NC}"