#!/bin/bash

# Quick Test Dashboard Launcher - Assumes dependencies are installed

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
FRONTEND_PORT=3020
BACKEND_PORT=6002
ML_DIGIT=${ML_DIGIT:-5}

echo -e "${BLUE}=== Quick Test Dashboard Launcher ===${NC}"
echo -e "${BLUE}Frontend Port: ${FRONTEND_PORT}${NC}"
echo -e "${BLUE}Backend Port: ${BACKEND_PORT}${NC}"

# Kill existing processes
lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
sleep 1

# Navigate to directory
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_dashboard

# Start backend
echo -e "${GREEN}Starting backend API...${NC}"
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 main.py &
    BACKEND_PID=$!
else
    echo -e "${YELLOW}No venv found, using system Python...${NC}"
    BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 main.py &
    BACKEND_PID=$!
fi
cd ..

# Wait for backend
echo -e "${BLUE}Waiting for backend...${NC}"
sleep 3

# Check if backend is running
if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running!${NC}"
else
    echo -e "${YELLOW}Backend health check failed, but continuing...${NC}"
fi

# Start frontend (assuming dependencies are installed)
echo -e "${GREEN}Starting frontend...${NC}"
cd frontend
if [ -d "node_modules" ]; then
    PORT=$FRONTEND_PORT npm start &
    FRONTEND_PID=$!
else
    echo -e "${YELLOW}Warning: node_modules not found. Run 'npm install --legacy-peer-deps' first${NC}"
    exit 1
fi
cd ..

echo ""
echo -e "${GREEN}=== Dashboard Starting ===${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:${FRONTEND_PORT} (may take 30s to fully load)"
echo -e "${BLUE}Backend API:${NC} http://localhost:${BACKEND_PORT}"
echo -e "${BLUE}API Docs:${NC} http://localhost:${BACKEND_PORT}/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}

trap cleanup INT TERM

# Keep running
wait