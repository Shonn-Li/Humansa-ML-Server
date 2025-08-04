#!/bin/bash

# Test Management Dashboard Launch Script - Fixed Version
# This script launches both the backend API and frontend UI

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
ML_DIGIT=${ML_DIGIT:-5}  # Default to digit 5 if not set

echo -e "${BLUE}=== Test Management Dashboard Launcher (Fixed) ===${NC}"
echo -e "${BLUE}Frontend Port: ${FRONTEND_PORT}${NC}"
echo -e "${BLUE}Backend Port: ${BACKEND_PORT}${NC}"
echo -e "${BLUE}ML Digit: ${ML_DIGIT}${NC}"
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
        echo -e "${YELLOW}Port $1 is in use. Killing existing process...${NC}"
        lsof -ti:$1 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Navigate to test_dashboard directory
cd "$(dirname "$0")/test_dashboard"

# Kill existing processes on our ports
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Start backend using simple_main.py
echo -e "${GREEN}Starting backend API on port ${BACKEND_PORT}...${NC}"
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Use simple_main.py instead of main.py
BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 simple_main.py > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo -e "${BLUE}Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null; then
        echo -e "${GREEN}Backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Check if backend actually started
if ! curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null; then
    echo -e "${RED}Backend failed to start! Check backend.log for errors.${NC}"
    cat backend/backend.log
    exit 1
fi

# Fix frontend dependencies
echo -e "${GREEN}Ensuring frontend dependencies are installed...${NC}"
cd frontend

# Remove node_modules if webpack is missing
if [ -d "node_modules" ] && ! [ -f "node_modules/webpack/package.json" ]; then
    echo -e "${YELLOW}Incomplete node_modules detected. Reinstalling...${NC}"
    rm -rf node_modules package-lock.json
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${GREEN}Installing frontend dependencies...${NC}"
    npm install --legacy-peer-deps
fi

# Start frontend
echo -e "${GREEN}Starting frontend on port ${FRONTEND_PORT}...${NC}"
PORT=$FRONTEND_PORT npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a bit for frontend to start
echo -e "${BLUE}Waiting for frontend to start...${NC}"
sleep 5

# Check if frontend started
if ! check_port $FRONTEND_PORT; then
    echo -e "${RED}Frontend failed to start! Check frontend.log for errors.${NC}"
    echo -e "${RED}Last 20 lines of frontend.log:${NC}"
    tail -20 frontend/frontend.log
    echo -e "${YELLOW}Stopping backend...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}=== Test Management Dashboard Started Successfully! ===${NC}"
echo -e "${BLUE}Frontend URL:${NC} http://localhost:${FRONTEND_PORT}"
echo -e "${BLUE}Backend API:${NC} http://localhost:${BACKEND_PORT}" 
echo -e "${BLUE}API Docs:${NC} http://localhost:${BACKEND_PORT}/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Keep script running and show logs
echo -e "\n${BLUE}=== Live Logs ===${NC}"
tail -f backend/backend.log frontend/frontend.log 2>/dev/null || while true; do sleep 1; done