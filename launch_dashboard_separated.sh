#!/bin/bash

# Launch Test Dashboard with Separated Frontend
# Backend API: Port 6002
# Frontend: Port 3020

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ML_DIGIT=${ML_DIGIT:-5}

echo -e "${BLUE}=== Test Management Dashboard ===${NC}"
echo -e "${BLUE}Configuration:${NC}"
echo -e "  ML Digit: ${ML_DIGIT}"
echo -e "  Database: test${ML_DIGIT}"
echo -e "  ML Server: Port $((5000 + ML_DIGIT))"
echo -e "  Backend API: Port 6002"
echo -e "  Frontend: Port 3020"
echo ""

# Kill existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 1

# Start Backend API
echo -e "${GREEN}Starting Backend API on port 6002...${NC}"
ML_DIGIT=$ML_DIGIT python3 test_dashboard_final.py > dashboard_backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Test backend
if curl -s http://localhost:6002/api/environment > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API is running${NC}"
    
    # Show database info
    echo -e "${BLUE}Database Connection:${NC}"
    curl -s http://localhost:6002/api/environment | python3 -c "
import sys, json
data = json.load(sys.stdin)
db = data['database']
print(f'  Database: {db[\"name\"]}')
print(f'  Host: {db[\"host\"]}:{db[\"port\"]}')
print(f'  Status: Connected' if db['connected'] else 'Status: Disconnected')
"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo "Check dashboard_backend.log for errors"
    exit 1
fi

# Extract HTML from the dashboard and serve it separately
echo -e "${GREEN}Extracting frontend HTML...${NC}"
curl -s http://localhost:6002/ > test_dashboard.html

# Start frontend server on port 3020
echo -e "${GREEN}Starting Frontend on port 3020...${NC}"
python3 -m http.server 3020 --bind localhost > dashboard_frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 1

echo ""
echo -e "${GREEN}=== Dashboard Running ===${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:3020/test_dashboard.html"
echo -e "${BLUE}Backend API:${NC} http://localhost:6002"
echo -e "${BLUE}API Endpoints:${NC}"
echo "  • GET  /api/environment - Environment info"
echo "  • GET  /api/tests/all - All tests"
echo "  • GET  /api/tests/category/{name} - Tests by category"
echo "  • POST /api/tests/run - Run tests"
echo "  • POST /api/jobs/create - Create batch job"
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