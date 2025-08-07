#!/bin/bash

# Enhanced Test Dashboard Launcher
# Features: Database info, clickable categories, test details, run functionality

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get ML digit from environment or use default
ML_DIGIT=${ML_DIGIT:-5}

echo -e "${BLUE}=== Enhanced Test Management Dashboard ===${NC}"
echo -e "${BLUE}ML Digit: ${ML_DIGIT}${NC}"
echo -e "${BLUE}Database: test${ML_DIGIT}${NC}"
echo -e "${BLUE}ML Server Port: $((5000 + ML_DIGIT))${NC}"
echo ""

# Kill existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 1

# Navigate to directory
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1

# Start Enhanced Backend
echo -e "${GREEN}Starting Enhanced Backend API on port 6002...${NC}"
cd test_dashboard/backend
source venv/bin/activate
ML_DIGIT=$ML_DIGIT BACKEND_PORT=6002 python3 enhanced_main.py &
BACKEND_PID=$!
cd ../..

# Wait for backend
sleep 2

# Test backend
if curl -s http://localhost:6002/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
    
    # Show database info
    echo -e "${BLUE}Database Connection Info:${NC}"
    curl -s http://localhost:6002/api/environments | python3 -c "
import sys, json
data = json.load(sys.stdin)
db = data['database_info']
print(f\"  Host: {db['host']}:{db['port']}\")
print(f\"  Database: {db['name']}\")
print(f\"  User: {db['user']}\")
print(f\"  ML Server: localhost:{db['ml_server_port']}\")
print(f\"  Test Environment: localhost:{db['test_environment_port']}\")
"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
fi

# Start simple Python HTTP server for frontend
echo -e "${GREEN}Starting Frontend on port 3020...${NC}"
python3 -m http.server 3020 --bind localhost > /dev/null 2>&1 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}=== Enhanced Dashboard Running ===${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:3020/enhanced_dashboard.html"
echo -e "${BLUE}Backend API:${NC} http://localhost:6002"
echo -e "${BLUE}API Docs:${NC} http://localhost:6002/docs"
echo ""
echo -e "${GREEN}Features:${NC}"
echo "  • Click on any category to see tests"
echo "  • Click on any test to see full details"
echo "  • Run individual tests or entire categories"
echo "  • View environment and database info"
echo "  • Real-time status updates via WebSocket"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    lsof -ti:6002 | xargs kill -9 2>/dev/null || true
    lsof -ti:3020 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}Stopped${NC}"
    exit 0
}

trap cleanup INT TERM

# Keep running
wait