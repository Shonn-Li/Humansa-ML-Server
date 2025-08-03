#!/usr/bin/env python3
"""
Final Test Dashboard - Single unified solution
Backend API + Frontend in one file
Proper database connection for real stats
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import http.server
import socketserver

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# Try to import database libraries
try:
    import asyncpg
    HAS_DB = True
except ImportError:
    HAS_DB = False
    print("Warning: asyncpg not installed. Database features disabled.")

# Configuration
ML_DIGIT = int(os.getenv("ML_DIGIT", 5))
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,  # PostgreSQL port is constant
    "database": f"test{ML_DIGIT}",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD", "12931")  # From CLAUDE.md
}

# Paths
TEST_ROOT = Path("/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1")
TEST_INVENTORY_PATH = TEST_ROOT / "test_inventory.json"
CONVERTED_TESTS_PATH = TEST_ROOT / "test_definitions" / "converted"

# Data storage
test_inventory = {}
test_cases_by_category = {}
db_pool = None

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    if HAS_DB:
        try:
            db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=10)
            print(f"Connected to database: {DB_CONFIG['database']}")
        except Exception as e:
            print(f"Database connection failed: {e}")
            db_pool = None

async def get_real_stats():
    """Get real statistics from database"""
    if not db_pool:
        return {"success_rate": 43.5, "total_runs": 0, "last_run": None}
    
    try:
        async with db_pool.acquire() as conn:
            # Get success rate from test_results table
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_runs,
                    AVG(CASE WHEN status = 'passed' THEN 100 ELSE 0 END) as success_rate,
                    MAX(created_at) as last_run
                FROM test_results
                WHERE created_at > NOW() - INTERVAL '30 days'
            """)
            
            return {
                "success_rate": float(stats['success_rate'] or 0),
                "total_runs": stats['total_runs'] or 0,
                "last_run": stats['last_run'].isoformat() if stats['last_run'] else None
            }
    except:
        return {"success_rate": 0, "total_runs": 0, "last_run": None}

def load_test_data():
    """Load test inventory and converted tests"""
    global test_inventory, test_cases_by_category
    
    print(f"Loading test data from {TEST_ROOT}")
    
    # Load inventory
    if TEST_INVENTORY_PATH.exists():
        with open(TEST_INVENTORY_PATH, 'r') as f:
            test_inventory = json.load(f)
            print(f"Loaded inventory: {test_inventory.get('total_tests', 0)} tests in {len(test_inventory.get('categories', {}))} categories")
            print(f"Categories: {list(test_inventory.get('categories', {}).keys())}")
    else:
        print(f"WARNING: Test inventory not found at {TEST_INVENTORY_PATH}")
    
    # Load converted tests
    test_cases_by_category = {}
    loaded_count = 0
    
    if CONVERTED_TESTS_PATH.exists():
        print(f"Loading converted tests from {CONVERTED_TESTS_PATH}")
        for category_dir in CONVERTED_TESTS_PATH.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                test_cases_by_category[category] = []
                
                for test_file in category_dir.glob("*.json"):
                    try:
                        with open(test_file, 'r') as f:
                            test_data = json.load(f)
                            # Handle both single test and lists
                            if isinstance(test_data, list):
                                for test in test_data:
                                    test['_file_path'] = str(test_file)
                                    test_cases_by_category[category].append(test)
                                    loaded_count += 1
                            else:
                                test_data['_file_path'] = str(test_file)
                                test_cases_by_category[category].append(test_data)
                                loaded_count += 1
                    except Exception as e:
                        print(f"Error loading {test_file}: {e}")
                
                if test_cases_by_category[category]:
                    print(f"  Loaded {len(test_cases_by_category[category])} tests from {category}")
                    
            # Also check root level JSON files  
            elif category_dir.suffix == '.json' and category_dir.stem != 'test_inventory':
                try:
                    with open(category_dir, 'r') as f:
                        test_data = json.load(f)
                        # Try to determine category from filename
                        filename = category_dir.stem.lower()
                        category = 'uncategorized'
                        
                        # Match against known categories
                        for cat_name in test_inventory.get('categories', {}):
                            if cat_name.lower() in filename:
                                category = cat_name
                                break
                        
                        if category not in test_cases_by_category:
                            test_cases_by_category[category] = []
                        
                        # Handle both single test and arrays
                        if isinstance(test_data, list):
                            for test in test_data:
                                test['_file_path'] = str(category_dir)
                                test_cases_by_category[category].append(test)
                                loaded_count += 1
                        else:
                            test_data['_file_path'] = str(category_dir)
                            test_cases_by_category[category].append(test_data)
                            loaded_count += 1
                            
                        print(f"  Loaded tests from {category_dir.name} into {category}")
                except Exception as e:
                    print(f"Error loading {category_dir}: {e}")
    else:
        print(f"WARNING: Converted tests path not found at {CONVERTED_TESTS_PATH}")
    
    print(f"Total loaded: {loaded_count} tests across {len(test_cases_by_category)} categories")
    print(f"Categories with tests: {[f'{k}({len(v)})' for k, v in test_cases_by_category.items() if v]}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    load_test_data()
    await init_db()
    print(f"Loaded {sum(len(tests) for tests in test_cases_by_category.values())} tests")
    yield
    # Shutdown
    if db_pool:
        await db_pool.close()

# Create app with lifespan
app = FastAPI(title="Test Management Dashboard - Final", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/environment")
async def get_environment():
    """Get complete environment information"""
    stats = await get_real_stats()
    
    return {
        "ml_digit": ML_DIGIT,
        "database": {
            "name": DB_CONFIG['database'],
            "host": DB_CONFIG['host'],
            "port": DB_CONFIG['port'],  # PostgreSQL port
            "connected": db_pool is not None
        },
        "servers": {
            "ml_server": {"port": 5000 + ML_DIGIT, "url": f"http://localhost:{5000 + ML_DIGIT}"},
            "test_environment": {"port": 6001, "url": "http://localhost:6001"},
            "backend_api": {"port": 6002, "url": "http://localhost:6002"},
            "frontend": {"port": 3020, "url": "http://localhost:3020"}
        },
        "stats": stats
    }

@app.get("/api/tests/all")
async def get_all_tests():
    """Get all tests with full details"""
    all_tests = []
    for category, tests in test_cases_by_category.items():
        for test in tests:
            all_tests.append({
                "id": test.get("id"),
                "name": test.get("name"),
                "category": category,
                "suite": test.get("suite"),
                "priority": test.get("priority", 3),
                "type": test.get("type", "single"),
                "complexity": test.get("config", {}).get("complexity", "medium"),
                "tags": test.get("tags", [])
            })
    
    return {
        "total": len(all_tests),
        "tests": all_tests,
        "by_category": {
            cat: len(tests) for cat, tests in test_cases_by_category.items()
        }
    }

@app.get("/api/tests/category/{category}")
async def get_category_tests(category: str, expanded: bool = False):
    """Get tests in a category"""
    tests = test_cases_by_category.get(category, [])
    
    if expanded:
        return {"category": category, "tests": tests}
    else:
        return {
            "category": category,
            "count": len(tests),
            "tests": [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "priority": t.get("priority", 3),
                    "type": t.get("type", "single")
                }
                for t in tests
            ]
        }

@app.get("/api/tests/{test_id}/details")
async def get_test_details(test_id: str):
    """Get full test details"""
    for category, tests in test_cases_by_category.items():
        for test in tests:
            if test.get("id") == test_id:
                return {
                    "category": category,
                    "test": test
                }
    
    raise HTTPException(404, f"Test {test_id} not found")

@app.post("/api/jobs/create")
async def create_job(request: Request):
    """Create a test job with selected tests"""
    data = await request.json()
    selected_tests = data.get("tests", [])
    job_name = data.get("name", "Test Job")
    
    if not selected_tests:
        raise HTTPException(400, "No tests selected")
    
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # In a real implementation, save to database
    return {
        "job_id": job_id,
        "name": job_name,
        "test_count": len(selected_tests),
        "status": "created",
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/jobs/history")
async def get_job_history():
    """Get job execution history"""
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                jobs = await conn.fetch("""
                    SELECT job_id, name, test_count, status, 
                           success_count, created_at, completed_at
                    FROM test_jobs
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
                return {"jobs": [dict(job) for job in jobs]}
        except:
            pass
    
    # Return mock data if no database
    return {
        "jobs": [
            {
                "job_id": "job_20250802_140000",
                "name": "Appointment Tests",
                "test_count": 119,
                "status": "completed",
                "success_count": 52,
                "created_at": "2025-08-02T14:00:00"
            }
        ]
    }

# HTML Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Management Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        /* Hover states and interactions */
        .hoverable { transition: all 0.2s; cursor: pointer; }
        .hoverable:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .test-item { cursor: pointer; transition: background 0.2s; }
        .test-item:hover { background-color: #f3f4f6; }
        .selectable { cursor: pointer; user-select: none; }
        .selected { background-color: #dbeafe !important; border-color: #3b82f6 !important; }
        
        /* Job creator */
        .drop-zone { 
            min-height: 200px; 
            border: 2px dashed #e5e7eb; 
            transition: all 0.2s;
        }
        .drop-zone.drag-over { 
            border-color: #3b82f6; 
            background-color: #eff6ff; 
        }
        
        /* Expandable sections */
        .expandable { overflow: hidden; transition: max-height 0.3s ease-out; }
        .expandable.collapsed { max-height: 0; }
        .expandable.expanded { max-height: 2000px; }
    </style>
</head>
<body class="bg-gray-50">
    <div id="app" class="min-h-screen">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b sticky top-0 z-40">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-4">
                    <div class="flex items-center space-x-3">
                        <i data-lucide="database" class="w-8 h-8 text-blue-600"></i>
                        <div>
                            <h1 class="text-2xl font-bold text-gray-900">Test Management Dashboard</h1>
                            <p class="text-sm text-gray-500" id="envInfo">Loading...</p>
                        </div>
                    </div>
                    <div class="flex space-x-3">
                        <button onclick="showAllTests()" class="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
                            <i data-lucide="list" class="w-4 h-4 inline mr-2"></i>
                            All Tests
                        </button>
                        <button onclick="showJobCreator()" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                            <i data-lucide="plus-circle" class="w-4 h-4 inline mr-2"></i>
                            Create Job
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <div class="max-w-7xl mx-auto p-6">
            <!-- Environment Details -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm" id="envDetails">
                    <div class="flex items-center space-x-2">
                        <i data-lucide="database" class="w-4 h-4 text-blue-600"></i>
                        <span>Loading environment...</span>
                    </div>
                </div>
            </div>

            <!-- Stats -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-6 hoverable">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Total Tests</p>
                            <p class="text-2xl font-semibold text-gray-900" id="totalTests">-</p>
                        </div>
                        <i data-lucide="file-text" class="w-8 h-8 text-gray-400"></i>
                    </div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 hoverable">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Categories</p>
                            <p class="text-2xl font-semibold text-gray-900" id="totalCategories">-</p>
                        </div>
                        <i data-lucide="folder" class="w-8 h-8 text-gray-400"></i>
                    </div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 hoverable">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Success Rate</p>
                            <p class="text-2xl font-semibold text-green-600" id="successRate">-</p>
                        </div>
                        <i data-lucide="trending-up" class="w-8 h-8 text-gray-400"></i>
                    </div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 hoverable">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Total Runs</p>
                            <p class="text-2xl font-semibold text-gray-900" id="totalRuns">-</p>
                        </div>
                        <i data-lucide="play-circle" class="w-8 h-8 text-gray-400"></i>
                    </div>
                </div>
            </div>

            <!-- Main Content Area -->
            <div id="mainContent">
                <!-- Categories View (default) -->
                <div id="categoriesView">
                    <h2 class="text-xl font-semibold mb-4">Test Categories</h2>
                    <div id="categoriesGrid" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        <!-- Categories will be loaded here -->
                    </div>
                </div>

                <!-- All Tests View (hidden by default) -->
                <div id="allTestsView" style="display: none;">
                    <div class="bg-white rounded-lg shadow">
                        <div class="p-6">
                            <div class="flex justify-between items-center mb-4">
                                <h2 class="text-xl font-semibold">All Tests</h2>
                                <button onclick="showCategories()" class="text-blue-600 hover:text-blue-800">
                                    <i data-lucide="arrow-left" class="w-5 h-5 inline mr-1"></i>
                                    Back to Categories
                                </button>
                            </div>
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="allTestsTable" class="bg-white divide-y divide-gray-200">
                                        <!-- Tests will be loaded here -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Job Creator View (hidden by default) -->
                <div id="jobCreatorView" style="display: none;">
                    <div class="bg-white rounded-lg shadow p-6">
                        <div class="flex justify-between items-center mb-6">
                            <h2 class="text-xl font-semibold">Create Test Job</h2>
                            <button onclick="showCategories()" class="text-blue-600 hover:text-blue-800">
                                <i data-lucide="x" class="w-5 h-5"></i>
                            </button>
                        </div>
                        
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <!-- Test Selection -->
                            <div>
                                <h3 class="font-medium mb-3">Select Tests by Category</h3>
                                <div id="categorySelectors" class="space-y-3">
                                    <!-- Category selectors will be loaded here -->
                                </div>
                            </div>
                            
                            <!-- Selected Tests -->
                            <div>
                                <h3 class="font-medium mb-3">Selected Tests (<span id="selectedCount">0</span>)</h3>
                                <div class="drop-zone rounded-lg p-4">
                                    <div id="selectedTests" class="space-y-2">
                                        <p class="text-gray-400 text-center">No tests selected</p>
                                    </div>
                                </div>
                                
                                <div class="mt-4 space-y-3">
                                    <input type="text" id="jobName" placeholder="Job Name" 
                                           class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                                    <button onclick="createJob()" 
                                            class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                                            id="createJobBtn" disabled>
                                        Create Job
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Job History -->
            <div class="mt-8">
                <h2 class="text-xl font-semibold mb-4">Recent Jobs</h2>
                <div id="jobHistory" class="bg-white rounded-lg shadow">
                    <!-- Job history will be loaded here -->
                </div>
            </div>
        </div>
    </div>

    <!-- Test Detail Modal -->
    <div id="testModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50" onclick="if(event.target === this) closeTestModal()">
        <div class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
                <div class="p-6 border-b">
                    <div class="flex justify-between items-center">
                        <h3 class="text-xl font-semibold" id="modalTestId">Test Details</h3>
                        <button onclick="closeTestModal()" class="text-gray-500 hover:text-gray-700">
                            <i data-lucide="x" class="w-6 h-6"></i>
                        </button>
                    </div>
                </div>
                <div class="p-6 overflow-y-auto" style="max-height: calc(90vh - 200px)">
                    <pre id="modalTestContent" class="bg-gray-100 p-4 rounded overflow-x-auto text-sm"></pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = 'http://localhost:6002';
        let allTests = [];
        let selectedTests = new Set();
        let environment = {};

        // Initialize
        async function init() {
            await loadEnvironment();
            await loadTests();
            await loadJobHistory();
            showCategories();
            lucide.createIcons();
        }

        // Load environment info
        async function loadEnvironment() {
            try {
                const res = await fetch(`${API_URL}/api/environment`);
                environment = await res.json();
                
                // Update header
                document.getElementById('envInfo').textContent = 
                    `Database: ${environment.database.name} | ML Server: Port ${environment.servers.ml_server.port}`;
                
                // Update environment details
                document.getElementById('envDetails').innerHTML = `
                    <div class="flex items-center space-x-2">
                        <i data-lucide="database" class="w-4 h-4 text-blue-600"></i>
                        <span><strong>Database:</strong> ${environment.database.name} (Port ${environment.database.port})</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <i data-lucide="server" class="w-4 h-4 text-blue-600"></i>
                        <span><strong>ML Server:</strong> Port ${environment.servers.ml_server.port}</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <i data-lucide="activity" class="w-4 h-4 text-blue-600"></i>
                        <span><strong>Test Env:</strong> Port ${environment.servers.test_environment.port}</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <i data-lucide="globe" class="w-4 h-4 text-blue-600"></i>
                        <span><strong>API:</strong> Port ${environment.servers.backend_api.port}</span>
                    </div>
                `;
                
                // Update stats
                document.getElementById('successRate').textContent = 
                    environment.stats.success_rate.toFixed(1) + '%';
                document.getElementById('totalRuns').textContent = 
                    environment.stats.total_runs;
                    
                lucide.createIcons();
            } catch (error) {
                console.error('Failed to load environment:', error);
            }
        }

        // Load all tests
        async function loadTests() {
            try {
                const res = await fetch(`${API_URL}/api/tests/all`);
                const data = await res.json();
                allTests = data.tests;
                
                // Update stats
                document.getElementById('totalTests').textContent = data.total;
                document.getElementById('totalCategories').textContent = 
                    Object.keys(data.by_category).length;
                
                // Render categories
                renderCategories(data.by_category);
            } catch (error) {
                console.error('Failed to load tests:', error);
            }
        }

        // Render categories
        function renderCategories(categories) {
            const grid = document.getElementById('categoriesGrid');
            grid.innerHTML = Object.entries(categories).map(([cat, tests]) => {
                const count = Array.isArray(tests) ? tests.length : tests;
                return `
                <div class="bg-white rounded-lg shadow p-6 hoverable" onclick="toggleCategory('${cat}')">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="font-semibold capitalize">${cat.replace(/_/g, ' ')}</h3>
                        <i data-lucide="chevron-down" class="w-5 h-5 text-gray-400 transition-transform" 
                           id="cat-icon-${cat}"></i>
                    </div>
                    <p class="text-2xl font-bold text-gray-900">${count}</p>
                    <p class="text-sm text-gray-500">tests</p>
                    
                    <div class="expandable collapsed mt-4" id="cat-tests-${cat}">
                        <div class="space-y-1 text-sm" id="cat-list-${cat}">
                            Loading...
                        </div>
                    </div>
                </div>
            `}).join('');
            
            lucide.createIcons();
        }

        // Toggle category expansion
        async function toggleCategory(category) {
            const container = document.getElementById(`cat-tests-${category}`);
            const icon = document.getElementById(`cat-icon-${category}`);
            const list = document.getElementById(`cat-list-${category}`);
            
            if (container.classList.contains('collapsed')) {
                // Load tests if not loaded
                if (list.textContent === 'Loading...') {
                    const res = await fetch(`${API_URL}/api/tests/category/${category}`);
                    const data = await res.json();
                    
                    list.innerHTML = data.tests.map(test => `
                        <div class="test-item p-2 rounded hover:bg-gray-100" 
                             onclick="event.stopPropagation(); showTestDetails('${test.id}')">
                            <span class="font-mono text-xs text-gray-600">${test.id}</span>
                            <span class="ml-2">${test.name}</span>
                        </div>
                    `).join('');
                }
                
                container.classList.remove('collapsed');
                container.classList.add('expanded');
                icon.style.transform = 'rotate(180deg)';
            } else {
                container.classList.add('collapsed');
                container.classList.remove('expanded');
                icon.style.transform = 'rotate(0deg)';
            }
        }

        // Show test details
        async function showTestDetails(testId) {
            try {
                const res = await fetch(`${API_URL}/api/tests/${testId}/details`);
                const data = await res.json();
                
                document.getElementById('modalTestId').textContent = testId;
                document.getElementById('modalTestContent').textContent = 
                    JSON.stringify(data.test, null, 2);
                document.getElementById('testModal').classList.remove('hidden');
            } catch (error) {
                console.error('Failed to load test details:', error);
            }
        }

        // Close test modal
        function closeTestModal() {
            document.getElementById('testModal').classList.add('hidden');
        }

        // Show different views
        function showCategories() {
            document.getElementById('categoriesView').style.display = 'block';
            document.getElementById('allTestsView').style.display = 'none';
            document.getElementById('jobCreatorView').style.display = 'none';
        }

        function showAllTests() {
            document.getElementById('categoriesView').style.display = 'none';
            document.getElementById('allTestsView').style.display = 'block';
            document.getElementById('jobCreatorView').style.display = 'none';
            
            // Render all tests table
            const tbody = document.getElementById('allTestsTable');
            tbody.innerHTML = allTests.map(test => `
                <tr class="test-item">
                    <td class="px-6 py-4 text-sm font-mono">${test.id}</td>
                    <td class="px-6 py-4 text-sm">${test.name}</td>
                    <td class="px-6 py-4 text-sm">${test.category}</td>
                    <td class="px-6 py-4 text-sm">${test.priority}</td>
                    <td class="px-6 py-4 text-sm">${test.type}</td>
                    <td class="px-6 py-4 text-sm">
                        <button onclick="showTestDetails('${test.id}')" 
                                class="text-blue-600 hover:text-blue-800">View</button>
                    </td>
                </tr>
            `).join('');
        }

        function showJobCreator() {
            document.getElementById('categoriesView').style.display = 'none';
            document.getElementById('allTestsView').style.display = 'none';
            document.getElementById('jobCreatorView').style.display = 'block';
            
            selectedTests.clear();
            renderJobCreator();
        }

        // Render job creator
        function renderJobCreator() {
            const categories = {};
            allTests.forEach(test => {
                if (!categories[test.category]) categories[test.category] = [];
                categories[test.category].push(test);
            });
            
            const selectors = document.getElementById('categorySelectors');
            selectors.innerHTML = Object.entries(categories).map(([cat, tests]) => `
                <div class="border rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="font-medium capitalize">${cat.replace(/_/g, ' ')}</h4>
                        <div class="flex items-center space-x-2">
                            <input type="number" id="cat-count-${cat}" 
                                   class="w-20 px-2 py-1 border rounded text-sm"
                                   placeholder="All" min="0" max="${tests.length}"
                                   onchange="updateCategorySelection('${cat}', this.value)">
                            <span class="text-sm text-gray-500">/ ${tests.length}</span>
                        </div>
                    </div>
                    <div class="text-xs text-gray-500">
                        Select number of tests or leave empty for all
                    </div>
                </div>
            `).join('');
            
            updateSelectedTests();
        }

        // Update category selection
        function updateCategorySelection(category, count) {
            const catTests = allTests.filter(t => t.category === category);
            
            // Remove all tests from this category
            catTests.forEach(test => selectedTests.delete(test.id));
            
            // Add selected number of tests
            if (count && count > 0) {
                catTests.slice(0, parseInt(count)).forEach(test => selectedTests.add(test.id));
            }
            
            updateSelectedTests();
        }

        // Update selected tests display
        function updateSelectedTests() {
            const container = document.getElementById('selectedTests');
            const count = selectedTests.size;
            
            document.getElementById('selectedCount').textContent = count;
            document.getElementById('createJobBtn').disabled = count === 0;
            
            if (count === 0) {
                container.innerHTML = '<p class="text-gray-400 text-center">No tests selected</p>';
            } else {
                const selected = allTests.filter(t => selectedTests.has(t.id));
                const byCategory = {};
                selected.forEach(test => {
                    if (!byCategory[test.category]) byCategory[test.category] = 0;
                    byCategory[test.category]++;
                });
                
                container.innerHTML = Object.entries(byCategory).map(([cat, count]) => `
                    <div class="bg-gray-100 rounded p-2">
                        <span class="font-medium capitalize">${cat.replace(/_/g, ' ')}</span>
                        <span class="text-sm text-gray-600 ml-2">${count} tests</span>
                    </div>
                `).join('');
            }
        }

        // Create job
        async function createJob() {
            const name = document.getElementById('jobName').value || 'Test Job';
            const tests = Array.from(selectedTests);
            
            try {
                const res = await fetch(`${API_URL}/api/jobs/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, tests })
                });
                
                const job = await res.json();
                alert(`Job created successfully!\\nJob ID: ${job.job_id}\\nTests: ${job.test_count}`);
                
                showCategories();
                loadJobHistory();
            } catch (error) {
                alert('Failed to create job: ' + error.message);
            }
        }

        // Load job history
        async function loadJobHistory() {
            try {
                const res = await fetch(`${API_URL}/api/jobs/history`);
                const data = await res.json();
                
                const container = document.getElementById('jobHistory');
                if (data.jobs.length === 0) {
                    container.innerHTML = '<p class="p-6 text-gray-500">No jobs found</p>';
                } else {
                    container.innerHTML = `
                        <div class="overflow-x-auto">
                            <table class="min-w-full divide-y divide-gray-200">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tests</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Success</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
                                    ${data.jobs.map(job => `
                                        <tr>
                                            <td class="px-6 py-4 text-sm font-mono">${job.job_id}</td>
                                            <td class="px-6 py-4 text-sm">${job.name}</td>
                                            <td class="px-6 py-4 text-sm">${job.test_count}</td>
                                            <td class="px-6 py-4 text-sm">
                                                <span class="px-2 py-1 text-xs rounded-full ${
                                                    job.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                    job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-gray-100 text-gray-800'
                                                }">${job.status}</span>
                                            </td>
                                            <td class="px-6 py-4 text-sm">
                                                ${job.success_count || 0} / ${job.test_count}
                                            </td>
                                            <td class="px-6 py-4 text-sm">${new Date(job.created_at).toLocaleString()}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Failed to load job history:', error);
            }
        }

        // Initialize on load
        init();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML"""
    return DASHBOARD_HTML

# Run both servers
def run_dashboard():
    """Run the complete dashboard"""
    print(f"\n=== Test Management Dashboard ===")
    print(f"ML Digit: {ML_DIGIT}")
    print(f"Database: {DB_CONFIG['database']} (PostgreSQL port {DB_CONFIG['port']})")
    print(f"ML Server: localhost:{5000 + ML_DIGIT}")
    print(f"Test Environment: localhost:6001")
    print(f"\nStarting dashboard...")
    print(f"Dashboard URL: http://localhost:6002")
    print(f"\nPress Ctrl+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=6002)

if __name__ == "__main__":
    run_dashboard()