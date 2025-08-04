#!/bin/bash

# Test Management Dashboard - Simple Launch Script
# Frontend: Port 3020
# Backend: Port 6002

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Test Management Dashboard Launcher ===${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is required but not installed${NC}"
    echo "Please install from: https://nodejs.org/"
    exit 1
fi

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 1

# Navigate to test_dashboard
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_dashboard

# Start Backend
echo -e "${GREEN}Starting Backend API on port 6002...${NC}"
cd backend

# Check if we need to install dependencies
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${BLUE}Installing backend dependencies...${NC}"
    pip install fastapi uvicorn[standard] python-multipart websockets
else
    source venv/bin/activate
fi

# Start the simple backend
BACKEND_PORT=6002 ML_DIGIT=5 python3 simple_main.py > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Give backend time to start
sleep 2

# Check if backend started
if curl -s http://localhost:6002/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running on http://localhost:6002${NC}"
    echo -e "${BLUE}  API Docs: http://localhost:6002/docs${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed, but it may still be starting...${NC}"
fi

# Start Frontend
echo -e "${GREEN}Starting Frontend on port 3020...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found!${NC}"
    echo -e "${BLUE}Installing frontend dependencies (this will take a few minutes)...${NC}"
    npm install --legacy-peer-deps
fi

# Start frontend
PORT=3020 npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Display success message
echo ""
echo -e "${GREEN}=== Dashboard Starting ===${NC}"
echo ""
echo -e "${BLUE}🌐 Frontend URL:${NC} http://localhost:3020"
echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:6002"
echo -e "${BLUE}📚 API Docs:${NC} http://localhost:6002/docs"
echo ""
echo -e "${YELLOW}⏳ Frontend may take 30-60 seconds to fully load...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    lsof -ti:6002 | xargs kill -9 2>/dev/null || true
    lsof -ti:3020 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

# Set trap
trap cleanup INT TERM

# Show logs
echo -e "${BLUE}=== Backend Logs ===${NC}"
tail -f backend/backend.log &
TAIL_PID=$!

# Wait
wait $BACKEND_PID $FRONTEND_PID