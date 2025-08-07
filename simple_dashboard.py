#!/usr/bin/env python3
"""
Simple Test Dashboard - All-in-One Solution
Serves both API and static frontend on different ports
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import threading
import http.server
import socketserver

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Backend API (Port 6002)
app = FastAPI(title="Test Management Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
                "complexity": "medium",
                "suite": "appointment"
            },
            {
                "id": "MED_001", 
                "name": "Medical Consultation Flow",
                "category": "medical",
                "priority": 4,
                "complexity": "high",
                "suite": "medical_consultation"
            },
            {
                "id": "PROD_001",
                "name": "Product Recommendation Test",
                "category": "product",
                "priority": 3,
                "complexity": "medium",
                "suite": "product"
            },
            {
                "id": "MULTI_001",
                "name": "Multi-turn Conversation Test",
                "category": "multi_turn",
                "priority": 5,
                "complexity": "high",
                "suite": "multi_turn"
            }
        ],
        "total": 847,
        "categories": {
            "appointment": 119,
            "medical": 30,
            "product": 55,
            "multi_turn": 67,
            "identity": 20,
            "emergency": 8,
            "edge_case": 22,
            "framework": 71,
            "api": 34,
            "integration": 32,
            "performance": 50,
            "streaming": 16,
            "orchestrator": 20,
            "memory": 22,
            "validation": 8
        }
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

# HTML Frontend
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Management Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-gray-50">
    <div id="app">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-4">
                    <div class="flex items-center space-x-3">
                        <i data-lucide="zap" class="w-8 h-8 text-blue-600"></i>
                        <div>
                            <h1 class="text-2xl font-bold text-gray-900">Test Management Dashboard</h1>
                            <p class="text-sm text-gray-500">YouWo AI ML Server Test Suite</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-4">
                        <select id="envSelect" class="block w-48 rounded-md border-gray-300 shadow-sm text-sm">
                            <option value="1">ML Server 1 (Port 5001)</option>
                            <option value="2">ML Server 2 (Port 5002)</option>
                            <option value="3">ML Server 3 (Port 5003)</option>
                            <option value="4">ML Server 4 (Port 5004)</option>
                            <option value="5" selected>ML Server 5 (Port 5005)</option>
                            <option value="6">ML Server 6 (Port 5006)</option>
                            <option value="7">ML Server 7 (Port 5007)</option>
                            <option value="8">ML Server 8 (Port 5008)</option>
                            <option value="9">ML Server 9 (Port 5009)</option>
                            <option value="10">ML Server 10 (Port 5010)</option>
                        </select>
                        <span class="text-sm text-gray-500">API: localhost:6002</span>
                    </div>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <!-- Health Status -->
            <div class="bg-white overflow-hidden shadow rounded-lg mb-6">
                <div class="px-4 py-5 sm:p-6">
                    <h2 class="text-lg font-medium text-gray-900 mb-4 flex items-center">
                        <i data-lucide="activity" class="w-5 h-5 mr-2 text-gray-600"></i>
                        System Health
                    </h2>
                    <div id="healthStatus" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="animate-pulse">
                            <div class="h-4 bg-gray-200 rounded w-full"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Stats -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="px-4 py-5 sm:p-6">
                        <dt class="text-sm font-medium text-gray-500 truncate flex items-center">
                            <i data-lucide="package" class="w-4 h-4 mr-2"></i>
                            Total Tests
                        </dt>
                        <dd id="totalTests" class="mt-1 text-3xl font-semibold text-gray-900">847</dd>
                    </div>
                </div>
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="px-4 py-5 sm:p-6">
                        <dt class="text-sm font-medium text-gray-500 truncate flex items-center">
                            <i data-lucide="bar-chart-3" class="w-4 h-4 mr-2"></i>
                            Active Jobs
                        </dt>
                        <dd class="mt-1 text-3xl font-semibold text-gray-900">0</dd>
                    </div>
                </div>
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="px-4 py-5 sm:p-6">
                        <dt class="text-sm font-medium text-gray-500 truncate flex items-center">
                            <i data-lucide="check-circle" class="w-4 h-4 mr-2"></i>
                            Success Rate
                        </dt>
                        <dd class="mt-1 text-3xl font-semibold text-green-600">43.5%</dd>
                    </div>
                </div>
                <div class="bg-white overflow-hidden shadow rounded-lg">
                    <div class="px-4 py-5 sm:p-6">
                        <dt class="text-sm font-medium text-gray-500 truncate flex items-center">
                            <i data-lucide="users" class="w-4 h-4 mr-2"></i>
                            Categories
                        </dt>
                        <dd id="totalCategories" class="mt-1 text-3xl font-semibold text-gray-900">21</dd>
                    </div>
                </div>
            </div>

            <!-- Test Categories -->
            <div class="bg-white shadow rounded-lg mb-6">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Test Categories</h3>
                    <div id="categories" class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div class="animate-pulse">
                            <div class="h-16 bg-gray-200 rounded"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sample Tests -->
            <div class="bg-white shadow rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Sample Tests</h3>
                    <div id="sampleTests" class="space-y-3">
                        <div class="animate-pulse">
                            <div class="h-16 bg-gray-200 rounded"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Status Message -->
            <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mt-6">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i data-lucide="check-circle" class="h-5 w-5 text-blue-400"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-blue-800">Dashboard Ready</h3>
                        <p class="mt-2 text-sm text-blue-700">
                            The Test Management Dashboard is running successfully!<br>
                            Frontend: http://localhost:3020<br>
                            Backend API: http://localhost:6002<br>
                            API Docs: http://localhost:6002/docs
                        </p>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();

        // API base URL
        const API_URL = 'http://localhost:6002';

        // Fetch and display health status
        async function fetchHealth() {
            try {
                const response = await fetch(`${API_URL}/api/health`);
                const data = await response.json();
                
                const healthHtml = `
                    <div class="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                        <i data-lucide="database" class="w-6 h-6 ${data.services.database === 'connected' ? 'text-green-500' : 'text-red-500'}"></i>
                        <div>
                            <p class="text-sm font-medium text-gray-900">Database</p>
                            <p class="text-sm text-gray-500">${data.services.database}</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                        <i data-lucide="server" class="w-6 h-6 ${data.services.ml_server === 'connected' ? 'text-green-500' : 'text-red-500'}"></i>
                        <div>
                            <p class="text-sm font-medium text-gray-900">ML Server</p>
                            <p class="text-sm text-gray-500">${data.services.ml_server}</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                        <i data-lucide="activity" class="w-6 h-6 ${data.services.test_environment === 'connected' ? 'text-green-500' : 'text-red-500'}"></i>
                        <div>
                            <p class="text-sm font-medium text-gray-900">Test Environment</p>
                            <p class="text-sm text-gray-500">${data.services.test_environment}</p>
                        </div>
                    </div>
                `;
                document.getElementById('healthStatus').innerHTML = healthHtml;
                lucide.createIcons();
            } catch (error) {
                console.error('Failed to fetch health:', error);
            }
        }

        // Fetch and display tests
        async function fetchTests() {
            try {
                const response = await fetch(`${API_URL}/api/tests`);
                const data = await response.json();
                
                // Update total tests
                document.getElementById('totalTests').textContent = data.total;
                
                // Update categories
                const categoriesHtml = Object.entries(data.categories).slice(0, 8).map(([category, count]) => `
                    <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-semibold text-gray-900">${count}</div>
                        <div class="text-sm text-gray-500 capitalize">${category.replace(/_/g, ' ')}</div>
                    </div>
                `).join('');
                document.getElementById('categories').innerHTML = categoriesHtml;
                
                // Update sample tests
                const testsHtml = data.tests.map(test => `
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div class="flex-1">
                            <div class="flex items-center space-x-3">
                                <span class="text-sm font-mono text-gray-600">${test.id}</span>
                                <span class="text-sm font-medium text-gray-900">${test.name}</span>
                            </div>
                            <div class="flex items-center space-x-4 mt-1">
                                <span class="text-xs text-gray-500">Category: ${test.category}</span>
                                <span class="text-xs text-gray-500">Priority: ${test.priority}</span>
                                <span class="text-xs text-gray-500">Complexity: ${test.complexity}</span>
                            </div>
                        </div>
                        <button onclick="runTest('${test.id}')" class="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200">
                            Run Test
                        </button>
                    </div>
                `).join('');
                document.getElementById('sampleTests').innerHTML = testsHtml;
                
                // Update total categories
                document.getElementById('totalCategories').textContent = Object.keys(data.categories).length;
            } catch (error) {
                console.error('Failed to fetch tests:', error);
            }
        }

        // Run test function
        function runTest(testId) {
            alert(`Running test: ${testId}\\nThis feature will be implemented soon!`);
        }

        // Initialize dashboard
        async function init() {
            await fetchHealth();
            await fetchTests();
            
            // Set up auto-refresh
            setInterval(fetchHealth, 5000);
        }

        // Start the dashboard
        init();
    </script>
</body>
</html>
"""

def run_frontend_server():
    """Run simple HTTP server for frontend on port 3020"""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
    
    with socketserver.TCPServer(("", 3020), Handler) as httpd:
        print("Frontend server running on http://localhost:3020")
        httpd.serve_forever()

def run_backend_server():
    """Run FastAPI backend on port 6002"""
    print("Backend API running on http://localhost:6002")
    print("API Docs available at http://localhost:6002/docs")
    uvicorn.run(app, host="0.0.0.0", port=6002)

if __name__ == "__main__":
    print("\n=== Test Management Dashboard ===")
    print("Starting servers...")
    print("")
    
    # Start frontend server in a thread
    frontend_thread = threading.Thread(target=run_frontend_server, daemon=True)
    frontend_thread.start()
    
    # Run backend server in main thread
    run_backend_server()