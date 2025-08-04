#!/bin/bash
set -e

# Test Dashboard Launch Script
# ===========================
# This script launches both the backend and frontend for the test dashboard
# Backend: http://localhost:6002
# Frontend: http://localhost:3020

echo "Test Dashboard Launch Script"
echo "============================"

# Navigate to the script directory
cd "$(dirname "$0")"

# Kill any existing processes on the ports
echo "Stopping any existing dashboard processes..."
lsof -ti:6002 | xargs -r kill -9 2>/dev/null || true
lsof -ti:3020 | xargs -r kill -9 2>/dev/null || true

# Function to cleanup on exit
cleanup() {
    echo "Stopping dashboard processes..."
    lsof -ti:6002 | xargs -r kill -9 2>/dev/null || true
    lsof -ti:3020 | xargs -r kill -9 2>/dev/null || true
}
trap cleanup EXIT

# Start Backend
echo "Starting backend server on port 6002..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r ../requirements.txt > /dev/null 2>&1

# Set database environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USER="postgres"
export DB_PASSWORD="12931"
export DB_NAME="test1"
export ML_DIGIT="1"

# Start backend in background
echo "Backend starting..."
python main.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if curl -s http://localhost:6002/health > /dev/null; then
    echo "✓ Backend is running on http://localhost:6002"
else
    echo "✗ Backend failed to start"
    cat backend.log
    exit 1
fi

# Start Frontend
echo "Starting frontend server on port 3020..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install --legacy-peer-deps > /dev/null 2>&1
fi

# Start frontend in background
echo "Frontend starting..."
NODE_OPTIONS=--openssl-legacy-provider PORT=3020 SKIP_PREFLIGHT_CHECK=true npm start > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to compile..."
sleep 10

# Check if frontend is running
if curl -s http://localhost:3020 > /dev/null; then
    echo "✓ Frontend is running on http://localhost:3020"
else
    echo "✗ Frontend may still be starting (check http://localhost:3020 in browser)"
fi

echo ""
echo "🚀 Test Dashboard is now running!"
echo "================================="
echo "Backend API:  http://localhost:6002"
echo "Frontend UI:  http://localhost:3020"
echo "API Docs:     http://localhost:6002/docs"
echo ""
echo "Both processes are running in the background."
echo "Press Ctrl+C to stop all services."
echo "Logs:"
echo "  Backend:  test_dashboard/backend/backend.log"
echo "  Frontend: test_dashboard/frontend/frontend.log"

# Wait a moment before checking status
sleep 3

# Quick status check
if curl -s http://localhost:6002/health > /dev/null && curl -s http://localhost:3020 > /dev/null; then
    echo "✓ Both services appear to be starting successfully"
else
    echo "⚠️ Services may still be starting, check the URLs above"
fi

# Keep script running
wait