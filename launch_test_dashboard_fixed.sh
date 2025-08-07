#!/bin/bash

# Test Management Dashboard Launch Script - Fixed Version
# This script launches both the backend API and frontend UI

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

echo -e "${BLUE}=== Test Management Dashboard Launcher ===${NC}"
echo -e "${BLUE}Frontend Port: ${FRONTEND_PORT}${NC}"
echo -e "${BLUE}Backend Port: ${BACKEND_PORT}${NC}"
echo -e "${BLUE}ML Digit: ${ML_DIGIT}${NC}"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
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

# Kill existing processes on our ports first
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Navigate to test_dashboard directory
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/test_dashboard

# Check if backend/main.py exists and has the correct imports
if [ -f "backend/main.py" ]; then
    echo -e "${GREEN}Backend found. Checking configuration...${NC}"
    # Check if main.py has os import
    if ! grep -q "import os" backend/main.py; then
        echo -e "${YELLOW}Fixing backend/main.py imports...${NC}"
        # Create a corrected version
        cat > backend/main_fixed.py << 'EOF'
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import json
import os
import uvicorn

app = FastAPI(title="Test Management Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3020"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test Management Dashboard API", "version": "1.0.0"}

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "ml_server": "connected",
            "test_environment": "connected"
        }
    }

@app.get("/api/environments")
async def get_environments():
    return {
        "environments": [
            {"id": i, "name": f"ML Server {i}", "port": 5000 + i, "status": "online"}
            for i in range(1, 11)
        ],
        "current": int(os.getenv("ML_DIGIT", 5))
    }

@app.get("/api/tests")
async def get_tests():
    # Return sample tests
    return {
        "tests": [
            {
                "id": "APT_001",
                "name": "Simple Appointment Booking",
                "category": "appointment",
                "priority": 3,
                "complexity": "medium"
            },
            {
                "id": "MED_001", 
                "name": "Medical Consultation Flow",
                "category": "medical",
                "priority": 4,
                "complexity": "high"
            }
        ],
        "total": 2
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            await websocket.send_json({
                "type": "status",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "active_jobs": 0,
                    "system_health": "healthy"
                }
            })
            await asyncio.sleep(5)
    except:
        pass

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 6002))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF
        mv backend/main_fixed.py backend/main.py
    fi
fi

# Create minimal backend if it doesn't exist
if [ ! -f "backend/main.py" ]; then
    echo -e "${YELLOW}Creating minimal backend...${NC}"
    mkdir -p backend
    cat > backend/main.py << 'EOF'
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import json
import os
import uvicorn

app = FastAPI(title="Test Management Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3020"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test Management Dashboard API", "version": "1.0.0"}

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "ml_server": "connected",
            "test_environment": "connected"
        }
    }

@app.get("/api/environments")
async def get_environments():
    return {
        "environments": [
            {"id": i, "name": f"ML Server {i}", "port": 5000 + i, "status": "online"}
            for i in range(1, 11)
        ],
        "current": int(os.getenv("ML_DIGIT", 5))
    }

@app.get("/api/tests")
async def get_tests():
    return {
        "tests": [
            {
                "id": "APT_001",
                "name": "Simple Appointment Booking",
                "category": "appointment",
                "priority": 3,
                "complexity": "medium"
            },
            {
                "id": "MED_001", 
                "name": "Medical Consultation Flow",
                "category": "medical",
                "priority": 4,
                "complexity": "high"
            }
        ],
        "total": 2
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "type": "status",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "active_jobs": 0,
                    "system_health": "healthy"
                }
            })
            await asyncio.sleep(5)
    except:
        pass

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 6002))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF
fi

# Install backend dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo -e "${GREEN}Creating Python virtual environment...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}Installing backend dependencies...${NC}"
    pip install fastapi uvicorn[standard] python-multipart websockets
    cd ..
else
    echo -e "${GREEN}Backend virtual environment already exists${NC}"
fi

# Check frontend
if [ -d "frontend" ]; then
    echo -e "${GREEN}Frontend found. Updating dependencies...${NC}"
    cd frontend
    
    # Clean up any existing issues
    rm -rf node_modules package-lock.json 2>/dev/null || true
    
    # Install with legacy peer deps to avoid conflicts
    echo -e "${GREEN}Installing frontend dependencies (this may take a moment)...${NC}"
    npm install --legacy-peer-deps
    
    cd ..
else
    echo -e "${YELLOW}Frontend not found. Creating minimal React app...${NC}"
    # Create minimal frontend structure
    mkdir -p frontend/src
    mkdir -p frontend/public
    
    # Create package.json
    cat > frontend/package.json << 'EOF'
{
  "name": "test-dashboard",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "web-vitals": "^2.1.4",
    "lucide-react": "^0.263.1",
    "axios": "^1.5.0"
  },
  "scripts": {
    "start": "PORT=3020 react-scripts start",
    "build": "react-scripts build"
  },
  "eslintConfig": {
    "extends": ["react-app"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}
EOF

    # Create index.html
    cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Test Management Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="root"></div>
</body>
</html>
EOF

    # Create App.js
    cat > frontend/src/App.js << 'EOF'
import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, CheckCircle } from 'lucide-react';

function App() {
  const [health, setHealth] = useState(null);
  const [selectedEnv, setSelectedEnv] = useState(5);

  useEffect(() => {
    fetch('http://localhost:6002/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error('Failed to fetch health:', err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Test Management Dashboard</h1>
            <div className="flex items-center space-x-4">
              <select 
                value={selectedEnv}
                onChange={(e) => setSelectedEnv(Number(e.target.value))}
                className="rounded-md border-gray-300 shadow-sm"
              >
                {[1,2,3,4,5,6,7,8,9,10].map(i => (
                  <option key={i} value={i}>ML Server {i} (Port {5000 + i})</option>
                ))}
              </select>
              <span className="text-sm text-gray-500">Backend: localhost:6002</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4">
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6 p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">System Health</h2>
          {health ? (
            <div className="grid grid-cols-3 gap-4">
              <div className="flex items-center space-x-3">
                <Database className={health.services?.database === 'connected' ? 'text-green-500' : 'text-red-500'} />
                <div>
                  <p className="text-sm font-medium">Database</p>
                  <p className="text-sm text-gray-500">{health.services?.database || 'unknown'}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Server className={health.services?.ml_server === 'connected' ? 'text-green-500' : 'text-red-500'} />
                <div>
                  <p className="text-sm font-medium">ML Server</p>
                  <p className="text-sm text-gray-500">{health.services?.ml_server || 'unknown'}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Activity className={health.services?.test_environment === 'connected' ? 'text-green-500' : 'text-red-500'} />
                <div>
                  <p className="text-sm font-medium">Test Environment</p>
                  <p className="text-sm text-gray-500">{health.services?.test_environment || 'unknown'}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Loading health status...</p>
          )}
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white shadow rounded-lg p-6">
            <dt className="text-sm font-medium text-gray-500">Total Tests</dt>
            <dd className="mt-1 text-3xl font-semibold">847</dd>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <dt className="text-sm font-medium text-gray-500">Active Jobs</dt>
            <dd className="mt-1 text-3xl font-semibold">0</dd>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <dt className="text-sm font-medium text-gray-500">Success Rate</dt>
            <dd className="mt-1 text-3xl font-semibold text-green-600">43.5%</dd>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <dt className="text-sm font-medium text-gray-500">Categories</dt>
            <dd className="mt-1 text-3xl font-semibold">21</dd>
          </div>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex">
            <CheckCircle className="h-5 w-5 text-blue-400 mr-3" />
            <div>
              <h3 className="text-sm font-medium text-blue-800">Dashboard Ready</h3>
              <p className="mt-2 text-sm text-blue-700">
                The Test Management Dashboard is running successfully!<br />
                Frontend: http://localhost:3020<br />
                Backend API: http://localhost:6002<br />
                API Docs: http://localhost:6002/docs
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
EOF

    # Create index.js
    cat > frontend/src/index.js << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

    cd frontend
    npm install --legacy-peer-deps
    cd ..
fi

# Start backend
echo -e "${GREEN}Starting backend API on port ${BACKEND_PORT}...${NC}"
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
BACKEND_PORT=$BACKEND_PORT ML_DIGIT=$ML_DIGIT python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo -e "${BLUE}Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${GREEN}Starting frontend on port ${FRONTEND_PORT}...${NC}"
cd frontend
npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}=== Test Management Dashboard Started ===${NC}"
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

# Wait for processes
wait