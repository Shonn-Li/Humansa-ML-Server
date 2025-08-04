#!/bin/bash
set -e

echo "Dashboard Verification Script"
echo "============================"

# Change to script directory
cd "$(dirname "$0")"

# Kill any existing processes
echo "Cleaning up existing processes..."
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend
echo "Starting backend..."
cd backend
source venv/bin/activate
python main.py > backend_test.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend
echo "Waiting for backend to start..."
for i in {1..10}; do
    if curl -s http://localhost:6002/health > /dev/null; then
        echo "✓ Backend is running"
        break
    fi
    sleep 1
done

# Check backend health
HEALTH=$(curl -s http://localhost:6002/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$HEALTH" = "healthy" ]; then
    echo "✓ Backend health check passed"
else
    echo "✗ Backend health check failed"
    cat backend/backend_test.log
    exit 1
fi

# Check API endpoints
echo "Testing API endpoints..."
TESTS=$(curl -s http://localhost:6002/api/tests)
if echo "$TESTS" | grep -q "HUV_011"; then
    echo "✓ Tests API working ($(echo "$TESTS" | grep -o '"id"' | wc -l) tests found)"
else
    echo "✗ Tests API failed"
    echo "$TESTS" | head -100
    exit 1
fi

# Start frontend
echo "Starting frontend..."
cd frontend
NODE_OPTIONS=--openssl-legacy-provider PORT=3020 SKIP_PREFLIGHT_CHECK=true npm start > frontend_test.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to compile
echo "Waiting for frontend to compile (this may take a minute)..."
sleep 20

# Check if frontend is responding
for i in {1..10}; do
    if curl -s http://localhost:3020 | grep -q "Test Dashboard"; then
        echo "✓ Frontend is running and serving content"
        break
    fi
    sleep 2
done

# Check for compilation errors
if grep -q "Failed to compile" frontend/frontend_test.log; then
    echo "✗ Frontend compilation failed:"
    grep -A 10 "Failed to compile" frontend/frontend_test.log
    exit 1
fi

# Final verification
echo ""
echo "Dashboard Status:"
echo "================"
echo "✓ Backend API: http://localhost:6002"
echo "✓ Frontend UI: http://localhost:3020"
echo "✓ API Docs: http://localhost:6002/docs"
echo ""
echo "Both services are running successfully!"
echo ""
echo "Check logs if needed:"
echo "  Backend: test_dashboard/backend/backend_test.log"
echo "  Frontend: test_dashboard/frontend/frontend_test.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep running
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT
wait