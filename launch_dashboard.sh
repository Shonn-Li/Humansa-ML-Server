#!/bin/bash

# Test Management Dashboard Launcher with ML Instance Management
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Test Management Dashboard Launcher ===${NC}"
echo

# Check Python 3
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

# Kill backend and frontend
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true

# Kill ML server instances
for port in 6011 6012 6013 6014; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Kill any Python processes running main.py or src.main
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*src.main" 2>/dev/null || true

sleep 2

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Navigate to ML server root for instances
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "youwo-ml-venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at $SCRIPT_DIR/youwo-ml-venv${NC}"
    echo "Please create it first with: python3 -m venv youwo-ml-venv"
    exit 1
fi

# Start ML Server Instances (6011-6014)
echo -e "${GREEN}Starting ML Server Instances...${NC}"
source youwo-ml-venv/bin/activate

for digit in 1 2 3 4; do
    port=$((6010 + digit))
    db_port=$((5060 + digit))
    
    echo -e "${BLUE}Starting ML instance $digit on port $port (DB port $db_port)...${NC}"
    
    DIGIT=$digit \
    ML_SERVER_PORT=$port \
    DB_PORT=$db_port \
    DB_NAME="youwoai" \
    DB_USER=youwo \
    DB_PASSWORD=youwo123 \
    DB_HOST=localhost \
    INSTANCE_ID=$digit \
    HUMANSA_ENHANCED_LOGGING=true \
    DB_ACTIVE_DATABASE="youwoai" \
    python -m src.main --port $port > /tmp/ml_server_$port.log 2>&1 &
    
    echo "  ML Server $digit started with PID $!"
    sleep 2
done

# Wait for ML servers to be ready
echo -e "${YELLOW}Waiting for ML servers to be ready...${NC}"
for i in {1..10}; do
    all_ready=true
    for port in 6011 6012 6013 6014; do
        if ! curl -s http://localhost:$port/health > /dev/null 2>&1; then
            all_ready=false
            break
        fi
    done
    
    if [ "$all_ready" = true ]; then
        echo -e "${GREEN}✓ All ML servers are ready${NC}"
        break
    fi
    
    echo -n "."
    sleep 2
done
echo

# Navigate to test_dashboard
cd "$SCRIPT_DIR/test_dashboard"

# Start Backend
echo -e "${GREEN}Starting Backend API on port 6002...${NC}"
cd backend

# Check if we need to install dependencies
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${BLUE}Installing backend dependencies...${NC}"
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start the backend with ML instances already running
BACKEND_PORT=6002 ML_DIGIT=5 python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Give backend time to start
echo -e "${YELLOW}Waiting for backend to start...${NC}"
for i in {1..20}; do
    if curl -s http://localhost:6002/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running on http://localhost:6002${NC}"
        echo -e "  API Docs: http://localhost:6002/docs"
        break
    fi
    echo -n "."
    sleep 1
done
echo

# Sync instances with backend
echo -e "${BLUE}Syncing ML instances with backend...${NC}"
curl -X POST http://localhost:6002/api/instances/sync > /dev/null 2>&1 || true
sleep 2

# Check instance status
echo -e "${GREEN}Instance Status:${NC}"
curl -s http://localhost:6002/api/instances/status | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'  Total: {d[\"total_instances\"]}')
    print(f'  Available: {d[\"available\"]}')
    print(f'  Busy: {d[\"busy\"]}')
    print(f'  Error: {d[\"error\"]}')
except:
    print('  Unable to get status')
"

# Start Frontend
echo -e "${GREEN}Starting Frontend on port 3020...${NC}"
cd frontend

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
fi

# Start the frontend
PORT=3020 npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo
echo -e "${BLUE}=== Dashboard Starting ===${NC}"
echo
echo -e "${GREEN}🌐 Frontend URL: http://localhost:3020${NC}"
echo -e "${GREEN}🔧 Backend API: http://localhost:6002${NC}"
echo -e "${GREEN}📚 API Docs: http://localhost:6002/docs${NC}"
echo
echo -e "${YELLOW}⏳ Frontend may take 30-60 seconds to fully load...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo

# Function to cleanup on exit
cleanup() {
    echo
    echo -e "${YELLOW}Stopping all services...${NC}"
    
    # Kill frontend
    kill $FRONTEND_PID 2>/dev/null || true
    
    # Kill backend
    kill $BACKEND_PID 2>/dev/null || true
    
    # Kill ML servers
    for port in 6011 6012 6013 6014; do
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    done
    
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Show backend logs
echo -e "${BLUE}=== Backend Logs ===${NC}"
tail -f backend/backend.log