#!/bin/bash

# Test Dashboard - Verified Working Script
# This script uses the existing backend venv and creates a simple frontend

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Test Management Dashboard ===${NC}"
echo ""

# Kill existing processes
echo -e "${YELLOW}Cleaning up...${NC}"
lsof -ti:6002 | xargs kill -9 2>/dev/null || true
lsof -ti:3020 | xargs kill -9 2>/dev/null || true
sleep 1

# Navigate to correct directory
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1

# Start Backend using existing venv
echo -e "${GREEN}Starting Backend API on port 6002...${NC}"
cd test_dashboard/backend
source venv/bin/activate
BACKEND_PORT=6002 python3 simple_main.py &
BACKEND_PID=$!
cd ../..

# Wait for backend
sleep 2

# Test backend
if curl -s http://localhost:6002/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
fi

# Create simple HTML frontend
echo -e "${GREEN}Creating simple frontend...${NC}"
cat > test_dashboard_ui.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Test Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-8">
    <div class="max-w-6xl mx-auto">
        <h1 class="text-3xl font-bold mb-8">Test Management Dashboard</h1>
        
        <div class="grid grid-cols-3 gap-4 mb-8">
            <div class="bg-white p-4 rounded shadow">
                <h3 class="font-semibold">Total Tests</h3>
                <p class="text-2xl" id="total">Loading...</p>
            </div>
            <div class="bg-white p-4 rounded shadow">
                <h3 class="font-semibold">Categories</h3>
                <p class="text-2xl" id="categories">Loading...</p>
            </div>
            <div class="bg-white p-4 rounded shadow">
                <h3 class="font-semibold">API Status</h3>
                <p class="text-2xl" id="status">Loading...</p>
            </div>
        </div>
        
        <div class="bg-white p-4 rounded shadow">
            <h3 class="font-semibold mb-4">Test Categories</h3>
            <div id="categoryList" class="grid grid-cols-4 gap-2"></div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                // Check health
                const healthRes = await fetch('http://localhost:6002/api/health');
                const health = await healthRes.json();
                document.getElementById('status').innerHTML = '<span class="text-green-600">Connected</span>';
                
                // Load tests
                const testsRes = await fetch('http://localhost:6002/api/tests');
                const tests = await testsRes.json();
                
                document.getElementById('total').textContent = tests.total;
                document.getElementById('categories').textContent = Object.keys(tests.categories).length;
                
                // Show categories
                const catHtml = Object.entries(tests.categories).map(([cat, count]) => 
                    '<div class="bg-gray-100 p-2 rounded">' + cat + ': ' + count + '</div>'
                ).join('');
                document.getElementById('categoryList').innerHTML = catHtml;
                
            } catch (error) {
                document.getElementById('status').innerHTML = '<span class="text-red-600">Error</span>';
            }
        }
        
        loadData();
        setInterval(loadData, 5000);
    </script>
</body>
</html>
EOF

# Start simple Python HTTP server for frontend
echo -e "${GREEN}Starting Frontend on port 3020...${NC}"
python3 -m http.server 3020 --bind localhost > /dev/null 2>&1 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}=== Dashboard Running ===${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:3020/test_dashboard_ui.html"
echo -e "${BLUE}Backend API:${NC} http://localhost:6002"
echo -e "${BLUE}API Docs:${NC} http://localhost:6002/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Stopping...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    lsof -ti:6002 | xargs kill -9 2>/dev/null || true
    lsof -ti:3020 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}Stopped${NC}"
    exit 0
}

trap cleanup INT TERM

# Keep running
wait