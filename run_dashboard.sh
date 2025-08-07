#!/bin/bash

# Simple Test Dashboard Runner
# One Python script serves both frontend (3020) and backend (6002)

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Test Management Dashboard ===${NC}"
echo ""

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 1

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

# Install dependencies if needed
echo -e "${GREEN}Checking dependencies...${NC}"
python3 -c "import fastapi" 2>/dev/null || {
    echo -e "${YELLOW}Installing FastAPI...${NC}"
    pip3 install fastapi uvicorn[standard]
}

# Run the dashboard
echo -e "${GREEN}Starting dashboard...${NC}"
echo ""
echo -e "${BLUE}Frontend:${NC} http://localhost:3020"
echo -e "${BLUE}Backend API:${NC} http://localhost:6002"
echo -e "${BLUE}API Docs:${NC} http://localhost:6002/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the all-in-one dashboard
python3 simple_dashboard.py