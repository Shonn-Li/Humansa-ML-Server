#!/usr/bin/env python3
"""Simple Test Dashboard Backend - Minimal Dependencies"""

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
    allow_origins=["http://localhost:3020", "http://localhost:3000"],
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
    # Return sample tests based on the inventory
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
            "edge_case": 22
        }
    }

@app.get("/api/jobs")
async def get_jobs():
    return {
        "jobs": [],
        "total": 0
    }

@app.get("/api/results")
async def get_results():
    return {
        "results": [],
        "total": 0,
        "success_rate": 43.5
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
    print(f"Starting Test Dashboard Backend on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)