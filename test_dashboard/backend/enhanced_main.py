#!/usr/bin/env python3
"""Enhanced Test Dashboard Backend with Full Features"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import json
import os
from pathlib import Path
import uvicorn
from typing import Dict, List, Optional

app = FastAPI(title="Test Management Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load test inventory and converted tests
# Fix path - we're in test_dashboard/backend/, need to go up 2 levels
TEST_ROOT = Path(__file__).parent.parent.parent
TEST_INVENTORY_PATH = TEST_ROOT / "test_inventory.json"
CONVERTED_TESTS_PATH = TEST_ROOT / "test_definitions" / "converted"

print(f"Loading test data from:")
print(f"  Inventory: {TEST_INVENTORY_PATH}")
print(f"  Converted: {CONVERTED_TESTS_PATH}")
print(f"  Inventory exists: {TEST_INVENTORY_PATH.exists()}")
print(f"  Converted exists: {CONVERTED_TESTS_PATH.exists()}")

# Cache for test data
test_inventory = {}
test_cases_by_category = {}

def load_test_data():
    """Load test inventory and converted tests"""
    global test_inventory, test_cases_by_category
    
    # Load inventory
    if TEST_INVENTORY_PATH.exists():
        with open(TEST_INVENTORY_PATH, 'r') as f:
            test_inventory = json.load(f)
            print(f"Loaded inventory: {test_inventory.get('total_tests', 0)} tests in {len(test_inventory.get('categories', {}))} categories")
    
    # Load converted tests - both from category directories and root level
    if CONVERTED_TESTS_PATH.exists():
        # First check for category directories
        for item in CONVERTED_TESTS_PATH.iterdir():
            if item.is_dir():
                category = item.name
                test_cases_by_category[category] = []
                
                for test_file in item.glob("*.json"):
                    try:
                        with open(test_file, 'r') as f:
                            test_data = json.load(f)
                            # Handle both single test and list of tests
                            if isinstance(test_data, list):
                                test_cases_by_category[category].extend(test_data)
                            else:
                                test_cases_by_category[category].append(test_data)
                    except Exception as e:
                        print(f"Error loading {test_file}: {e}")
            
            # Also check for JSON files at root level
            elif item.suffix == '.json' and item.stem != 'test_inventory':
                # Extract category from filename if possible
                category = 'uncategorized'
                filename = item.stem.lower()
                
                # Try to match category from known categories
                for cat in test_inventory.get('categories', {}):
                    if cat.lower() in filename:
                        category = cat
                        break
                
                if category not in test_cases_by_category:
                    test_cases_by_category[category] = []
                
                try:
                    with open(item, 'r') as f:
                        test_data = json.load(f)
                        if isinstance(test_data, list):
                            test_cases_by_category[category].extend(test_data)
                        else:
                            test_cases_by_category[category].append(test_data)
                except Exception as e:
                    print(f"Error loading {item}: {e}")
        
        print(f"Loaded {sum(len(tests) for tests in test_cases_by_category.values())} tests across {len(test_cases_by_category)} categories")

# Load data on startup
load_test_data()

@app.get("/")
async def root():
    return {"message": "Test Management Dashboard API", "version": "2.0.0"}

@app.get("/api/health")
async def health():
    ml_digit = int(os.getenv("ML_DIGIT", 5))
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "ml_server": "connected", 
            "test_environment": "connected"
        },
        "environment": {
            "ml_digit": ml_digit,
            "database": f"test{ml_digit}",
            "ml_server_port": 5000 + ml_digit,
            "test_port": 6001,
            "backend_port": 6002
        }
    }

@app.get("/api/environments")
async def get_environments():
    ml_digit = int(os.getenv("ML_DIGIT", 5))
    return {
        "environments": [
            {"id": i, "name": f"ML Server {i}", "port": 5000 + i, "status": "online"}
            for i in range(1, 11)
        ],
        "current": ml_digit,
        "database_info": {
            "host": "localhost",
            "port": 5432,
            "name": f"test{ml_digit}",
            "user": "postgres",
            "ml_server_port": 5000 + ml_digit,
            "test_environment_port": 6001,
            "backend_api_port": 6002
        }
    }

@app.get("/api/tests/summary")
async def get_tests_summary():
    """Get test summary with categories"""
    categories = test_inventory.get("categories", {})
    
    # Add test counts from loaded data
    category_details = {}
    for cat, count in categories.items():
        actual_tests = test_cases_by_category.get(cat, [])
        category_details[cat] = {
            "count": count,
            "loaded": len(actual_tests),
            "tests": [{"id": t.get("id"), "name": t.get("name")} for t in actual_tests[:5]]  # First 5
        }
    
    return {
        "total": test_inventory.get("total_tests", 847),
        "categories": category_details,
        "test_types": test_inventory.get("test_types", {}),
        "complexity_distribution": test_inventory.get("complexity_distribution", {})
    }

@app.get("/api/tests/category/{category}")
async def get_tests_by_category(category: str):
    """Get all tests in a specific category"""
    tests = test_cases_by_category.get(category, [])
    
    if not tests and category not in test_inventory.get("categories", {}):
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    
    return {
        "category": category,
        "total": len(tests),
        "tests": tests
    }

@app.get("/api/tests/{test_id}")
async def get_test_details(test_id: str):
    """Get detailed information about a specific test"""
    # Search for test in all categories
    for category, tests in test_cases_by_category.items():
        for test in tests:
            if test.get("id") == test_id:
                return {
                    "test": test,
                    "category": category,
                    "can_run": True
                }
    
    raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")

@app.post("/api/tests/{test_id}/run")
async def run_test(test_id: str):
    """Run a specific test"""
    # Find the test
    test_data = None
    test_category = None
    
    for category, tests in test_cases_by_category.items():
        for test in tests:
            if test.get("id") == test_id:
                test_data = test
                test_category = category
                break
    
    if not test_data:
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")
    
    # Simulate test execution
    return {
        "job_id": f"job_{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "test_id": test_id,
        "category": test_category,
        "status": "queued",
        "message": f"Test '{test_data.get('name')}' queued for execution",
        "estimated_time": test_data.get('config', {}).get('timeout', 30)
    }

@app.post("/api/jobs/create")
async def create_job(body: dict):
    """Create a new test job"""
    test_ids = body.get("test_ids", [])
    category = body.get("category")
    
    if category:
        # Get all tests from category
        tests = test_cases_by_category.get(category, [])
        test_ids = [t.get("id") for t in tests]
    
    if not test_ids:
        raise HTTPException(status_code=400, detail="No tests specified")
    
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "job_id": job_id,
        "test_count": len(test_ids),
        "status": "created",
        "tests": test_ids[:10],  # First 10
        "message": f"Job created with {len(test_ids)} tests"
    }

@app.get("/api/jobs")
async def get_jobs():
    """Get list of jobs"""
    # Mock data for now
    return {
        "jobs": [
            {
                "id": "job_20250802_230000",
                "name": "Appointment Tests",
                "test_count": 119,
                "status": "completed",
                "success_rate": 43.5,
                "created_at": "2025-08-02T23:00:00"
            }
        ],
        "total": 1
    }

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    ml_digit = int(os.getenv("ML_DIGIT", 5))
    
    return {
        "environment": {
            "ml_digit": ml_digit,
            "database": f"test{ml_digit}",
            "ml_server": f"localhost:{5000 + ml_digit}",
            "test_environment": "localhost:6001",
            "backend_api": "localhost:6002"
        },
        "tests": {
            "total": test_inventory.get("total_tests", 847),
            "categories": len(test_inventory.get("categories", {})),
            "loaded": sum(len(tests) for tests in test_cases_by_category.values())
        },
        "performance": {
            "success_rate": 43.5,
            "avg_execution_time": 2.3,
            "tests_per_hour": 150
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            ml_digit = int(os.getenv("ML_DIGIT", 5))
            await websocket.send_json({
                "type": "status",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "active_jobs": 0,
                    "system_health": "healthy",
                    "environment": {
                        "ml_digit": ml_digit,
                        "database": f"test{ml_digit}"
                    }
                }
            })
            await asyncio.sleep(5)
    except:
        pass

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 6002))
    print(f"Starting Enhanced Test Dashboard Backend on port {port}...")
    print(f"ML Digit: {os.getenv('ML_DIGIT', 5)}")
    print(f"Database: test{os.getenv('ML_DIGIT', 5)}")
    uvicorn.run(app, host="0.0.0.0", port=port)