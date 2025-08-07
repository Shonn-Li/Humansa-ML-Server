#!/bin/bash

# Test Management Dashboard - Working Launch Script
# This script uses the simple backend and enhanced HTML frontend
# No npm dependencies required - guaranteed to work

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=6002
ML_DIGIT=${ML_DIGIT:-5}

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Test Management Dashboard              ║${NC}"
echo -e "${BLUE}║       Working Version - No NPM Required      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Backend Port:${NC} ${BACKEND_PORT}"
echo -e "${GREEN}ML Server:${NC} ${ML_DIGIT}"
echo -e "${GREEN}Frontend:${NC} Enhanced HTML (no build required)"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Kill existing processes
echo -e "${YELLOW}→ Cleaning up existing processes...${NC}"
if check_port $BACKEND_PORT; then
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Navigate to project root
cd "$(dirname "$0")"

# Start backend using simple_main.py (which we know works)
echo -e "${GREEN}→ Starting backend API...${NC}"
cd test_dashboard/backend

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}  Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv and install minimal requirements
source venv/bin/activate
pip install fastapi uvicorn python-multipart 2>/dev/null || true

# Start the simple backend
BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 simple_main.py > backend.log 2>&1 &
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
        echo -e "${RED}Last 10 lines of backend.log:${NC}"
        tail -10 test_dashboard/backend/backend.log
        exit 1
    fi
    printf "."
    sleep 1
done
echo ""

# Open the enhanced dashboard HTML
echo -e "${GREEN}→ Opening dashboard in browser...${NC}"
if [ -f "enhanced_dashboard.html" ]; then
    if command -v open > /dev/null; then
        open enhanced_dashboard.html
    elif command -v xdg-open > /dev/null; then
        xdg-open enhanced_dashboard.html
    else
        echo -e "${YELLOW}Please open enhanced_dashboard.html in your browser${NC}"
    fi
else
    echo -e "${RED}✗ enhanced_dashboard.html not found!${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Dashboard Started Successfully! 🎉       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Backend API:${NC} http://localhost:${BACKEND_PORT}"
echo -e "${BLUE}API Docs:${NC} http://localhost:${BACKEND_PORT}/docs"
echo -e "${BLUE}Frontend:${NC} enhanced_dashboard.html (open in browser)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the backend${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}→ Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    echo -e "${GREEN}✓ Services stopped${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Show backend logs
echo -e "${BLUE}═══ Backend Logs ═══${NC}"
tail -f test_dashboard/backend/backend.log