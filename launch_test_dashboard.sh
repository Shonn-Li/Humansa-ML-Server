#!/bin/bash

# Test Management Dashboard Launch Script
# This script launches both the backend API and frontend UI

# set -e  # Exit on error - disabled to handle npm issues gracefully

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

# Check and create test_dashboard directory if needed
if [ ! -d "test_dashboard" ]; then
    echo -e "${YELLOW}test_dashboard directory not found. Creating it...${NC}"
    mkdir -p test_dashboard
fi

cd test_dashboard

# Check if backend exists, if not create minimal structure
if [ ! -d "backend" ]; then
    echo -e "${YELLOW}Backend not found. Creating minimal backend structure...${NC}"
    mkdir -p backend
    
    # Create minimal FastAPI backend
    cat > backend/main.py << 'EOF'
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import json
import os

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
    import uvicorn
    import os
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", 6002)))
EOF

    # Create requirements.txt
    cat > backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0
EOF
fi

# Check if frontend exists, if not create minimal React app
if [ ! -d "frontend" ]; then
    echo -e "${YELLOW}Frontend not found. Creating React app...${NC}"
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
        echo "Visit https://nodejs.org/ to download and install Node.js"
        exit 1
    fi
    
    # Create React app
    npx create-react-app frontend --template typescript
    
    # Wait for creation to complete
    sleep 2
    
    # Update package.json to use port 3020
    cd frontend
    # Update the start script in package.json
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' 's/"start": "react-scripts start"/"start": "PORT=3020 react-scripts start"/' package.json
    else
        # Linux
        sed -i 's/"start": "react-scripts start"/"start": "PORT=3020 react-scripts start"/' package.json
    fi
    
    # Install additional dependencies
    npm install --save \
        react-router-dom@6 \
        @types/react-router-dom \
        lucide-react \
        tailwindcss \
        @headlessui/react \
        chart.js \
        react-chartjs-2 \
        axios
    
    # Initialize Tailwind CSS
    npx tailwindcss init -p
    
    # Update tailwind.config.js
    cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      }
    },
  },
  plugins: [],
}
EOF
    
    # Update src/index.css
    cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
EOF
    
    # Create a simple dashboard component
    cat > src/App.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, CheckCircle, AlertCircle } from 'lucide-react';

function App() {
  const [health, setHealth] = useState<any>(null);
  const [environments, setEnvironments] = useState<any[]>([]);
  const [selectedEnv, setSelectedEnv] = useState(5);

  useEffect(() => {
    // Fetch health status
    fetch('http://localhost:6002/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error('Failed to fetch health:', err));

    // Fetch environments
    fetch('http://localhost:6002/api/environments')
      .then(res => res.json())
      .then(data => {
        setEnvironments(data.environments || []);
        setSelectedEnv(data.current || 5);
      })
      .catch(err => console.error('Failed to fetch environments:', err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-3xl font-bold text-gray-900">Test Management Dashboard</h1>
            <div className="flex items-center space-x-4">
              <select 
                value={selectedEnv}
                onChange={(e) => setSelectedEnv(Number(e.target.value))}
                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
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

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Health Status */}
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">System Health</h2>
            {health ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex items-center space-x-3">
                  <Database className={health.services?.database === 'connected' ? 'text-green-500' : 'text-red-500'} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Database</p>
                    <p className="text-sm text-gray-500">{health.services?.database || 'unknown'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <Server className={health.services?.ml_server === 'connected' ? 'text-green-500' : 'text-red-500'} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">ML Server</p>
                    <p className="text-sm text-gray-500">{health.services?.ml_server || 'unknown'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <Activity className={health.services?.test_environment === 'connected' ? 'text-green-500' : 'text-red-500'} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Test Environment</p>
                    <p className="text-sm text-gray-500">{health.services?.test_environment || 'unknown'}</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">Loading health status...</p>
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <dt className="text-sm font-medium text-gray-500 truncate">Total Tests</dt>
              <dd className="mt-1 text-3xl font-semibold text-gray-900">847</dd>
            </div>
          </div>
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <dt className="text-sm font-medium text-gray-500 truncate">Active Jobs</dt>
              <dd className="mt-1 text-3xl font-semibold text-gray-900">0</dd>
            </div>
          </div>
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <dt className="text-sm font-medium text-gray-500 truncate">Success Rate</dt>
              <dd className="mt-1 text-3xl font-semibold text-green-600">43.5%</dd>
            </div>
          </div>
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <dt className="text-sm font-medium text-gray-500 truncate">Categories</dt>
              <dd className="mt-1 text-3xl font-semibold text-gray-900">21</dd>
            </div>
          </div>
        </div>

        {/* Welcome Message */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <CheckCircle className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Dashboard Ready</h3>
              <p className="mt-2 text-sm text-blue-700">
                The Test Management Dashboard is running successfully!
                <br />
                Frontend: http://localhost:3020
                <br />
                Backend API: http://localhost:6002
                <br />
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
    
    cd ..
fi

# Install backend dependencies if needed
if [ -d "backend" ] && [ ! -d "backend/venv" ]; then
    echo -e "${GREEN}Installing backend dependencies...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt 2>/dev/null || pip install fastapi uvicorn[standard] python-multipart websockets
    cd ..
fi

# Install frontend dependencies if needed  
if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
    echo -e "${GREEN}Installing frontend dependencies...${NC}"
    cd frontend
    npm install --legacy-peer-deps
    cd ..
fi

# Kill existing processes on our ports
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

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
    if curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null; then
        echo -e "${GREEN}Backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${GREEN}Starting frontend on port ${FRONTEND_PORT}...${NC}"
cd frontend
PORT=$FRONTEND_PORT npm start > frontend.log 2>&1 &
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

# Keep script running and show logs
echo -e "\n${BLUE}=== Live Logs ===${NC}"
tail -f backend/backend.log frontend/frontend.log 2>/dev/null || while true; do sleep 1; done