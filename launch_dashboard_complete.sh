#!/bin/bash

# Test Management Dashboard - Complete Implementation Launch Script
# This script launches the fully restored original implementation

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_PORT=3020
BACKEND_PORT=6002
ML_DIGIT=${ML_DIGIT:-5}

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Test Management Dashboard - Complete Version     ║${NC}"
echo -e "${BLUE}║           Original Implementation Restored           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Backend Port: ${BACKEND_PORT}"
echo -e "  Frontend Port: ${FRONTEND_PORT}"
echo -e "  ML Server Digit: ${ML_DIGIT}"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    if check_port $1; then
        echo -e "${YELLOW}→ Port $1 is in use. Killing existing process...${NC}"
        lsof -ti:$1 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Navigate to project root
cd "$(dirname "$0")"

# Kill existing processes
echo -e "${YELLOW}→ Cleaning up existing processes...${NC}"
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Start Backend with the original main.py (now fixed)
echo -e "${GREEN}→ Starting backend API (original implementation)...${NC}"
cd test_dashboard/backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}  Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv and install dependencies
source venv/bin/activate
echo -e "${YELLOW}  Installing backend dependencies...${NC}"
pip install fastapi uvicorn python-multipart websockets pydantic pydantic-settings 2>/dev/null || true

# Start the original main.py (now with all required modules)
BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
echo -e "${BLUE}→ Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend failed to start${NC}"
        echo -e "${RED}Backend logs:${NC}"
        tail -20 test_dashboard/backend/backend.log
        exit 1
    fi
    printf "."
    sleep 1
done
echo ""

# Test backend endpoints
echo -e "${BLUE}→ Testing backend endpoints...${NC}"
echo -e "  Testing /api/environments... \c"
if curl -s http://localhost:$BACKEND_PORT/api/environments > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -e "  Testing /api/tests... \c"
if curl -s http://localhost:$BACKEND_PORT/api/tests > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -e "  Testing /api/jobs... \c"
if curl -s http://localhost:$BACKEND_PORT/api/jobs > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Start Frontend with fixed dependencies
echo -e "${GREEN}→ Starting React frontend...${NC}"
cd test_dashboard/frontend

# Check Node version
NODE_VERSION=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" != "18" ]; then
    echo -e "${YELLOW}  Warning: Node.js v$NODE_VERSION detected. Node 18 is recommended.${NC}"
    echo -e "${YELLOW}  Run 'nvm use 18' if you have nvm installed.${NC}"
fi

# Check if setup is needed
if [ ! -d "node_modules" ] || [ ! -f "node_modules/webpack/package.json" ]; then
    echo -e "${YELLOW}  Running frontend setup...${NC}"
    if [ -f "setup.sh" ]; then
        ./setup.sh
    else
        echo -e "${YELLOW}  Installing frontend dependencies manually...${NC}"
        rm -rf node_modules package-lock.json
        npm install --legacy-peer-deps
    fi
fi

# Start the React app
echo -e "${GREEN}  Starting React application...${NC}"
PORT=$FRONTEND_PORT npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait for frontend to start
echo -e "${BLUE}→ Waiting for frontend to start...${NC}"
sleep 5  # Give React time to compile

# Check if frontend started
for i in {1..30}; do
    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}✓ Frontend is running!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Frontend failed to start${NC}"
        echo -e "${RED}Frontend logs:${NC}"
        tail -20 test_dashboard/frontend/frontend.log
        echo -e "${YELLOW}Stopping backend...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    printf "."
    sleep 1
done
echo ""

# Success!
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Dashboard Started Successfully! 🎉                 ║${NC}"
echo -e "${GREEN}║   Original Implementation Fully Restored             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "  Frontend Dashboard: ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  Backend API: ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  API Documentation: ${GREEN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo -e "  API ReDoc: ${GREEN}http://localhost:${BACKEND_PORT}/redoc${NC}"
echo ""
echo -e "${BLUE}Available Endpoints:${NC}"
echo -e "  • /api/environments - Environment management"
echo -e "  • /api/tests - Test catalog (847 tests)"
echo -e "  • /api/jobs - Job management"
echo -e "  • /api/runs - Execution monitoring"
echo -e "  • /api/results - Results analysis"
echo -e "  • /api/export - Export functionality"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}→ Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo -e "${GREEN}✓ Services stopped${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Monitor logs
echo -e "${BLUE}═══ Live Logs (Backend | Frontend) ═══${NC}"
echo -e "${YELLOW}Tip: Backend API docs available at http://localhost:${BACKEND_PORT}/docs${NC}"
echo ""

# Tail both logs
tail -f test_dashboard/backend/backend.log test_dashboard/frontend/frontend.log 2>/dev/null