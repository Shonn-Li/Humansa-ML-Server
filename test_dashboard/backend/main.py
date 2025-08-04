"""
Test Management Dashboard Backend
=================================

FastAPI server for managing ML server tests
Runs on port 6002
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_dashboard.backend.api import (
    environments,
    jobs,
    tests,
    runs,
    results,
    export
)
from test_dashboard.backend.core.config import settings
from test_dashboard.backend.core.database import init_db
from test_dashboard.backend.core.websocket import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    # Startup
    logger.info("Starting Test Management Dashboard...")
    
    # Initialize database
    await init_db()
    
    # Discover tests on startup
    from test_dashboard.backend.api.tests import startup_discover_tests
    await startup_discover_tests()
    
    # Start background tasks
    app.state.tasks = []
    
    yield
    
    # Shutdown
    logger.info("Shutting down Test Management Dashboard...")
    
    # Cancel background tasks
    for task in app.state.tasks:
        task.cancel()
    
    # Close WebSocket connections
    await app.state.manager.disconnect_all()


# Create FastAPI app
app = FastAPI(
    title="Test Management Dashboard",
    description="Centralized test execution and monitoring for YouWo AI ML Server",
    version="1.0.0",
    lifespan=lifespan
)

# Disable automatic slash redirect (to fix 307 redirect issues)
from fastapi.middleware.trustedhost import TrustedHostMiddleware

class NoRedirectFastAPI(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.router.redirect_slashes = False

# Apply no-redirect configuration
app.router.redirect_slashes = False

# WebSocket connection manager
app.state.manager = ConnectionManager()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(environments.router, prefix="/api/environments", tags=["environments"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(export.router, prefix="/api/export", tags=["export"])

# Mount static files (for React build)
if Path("test_dashboard/frontend/build").exists():
    app.mount("/", StaticFiles(directory="test_dashboard/frontend/build", html=True), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Test Management Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "test-dashboard",
        "port": settings.PORT
    }


@app.get("/system-info")
async def get_system_info():
    """Get system configuration information"""
    from test_dashboard.backend.core.database import is_database_available
    
    # Get environment info from database if available
    environments = []
    if is_database_available():
        from test_dashboard.backend.core.database import execute_query
        env_query = "SELECT name, digit, base_port, status FROM test_management.environments ORDER BY digit"
        env_rows = await execute_query(env_query, {})
        environments = [
            {
                "name": row['name'],
                "digit": row['digit'],
                "port": row['base_port'] + row['digit'],
                "status": row['status']
            }
            for row in env_rows
        ]
    
    return {
        "dashboard": {
            "backend_port": settings.PORT,
            "frontend_port": 3020,
            "api_docs": f"http://localhost:{settings.PORT}/docs"
        },
        "database": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "database": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": "*" * len(settings.DB_PASSWORD) if settings.DB_PASSWORD else "Not set",
            "schema": "test_management",
            "available": is_database_available()
        },
        "test_environments": environments,
        "ml_server": {
            "base_port": 6000,
            "digit": settings.ML_SERVER_DIGIT,
            "test_port": 6000 + settings.ML_SERVER_DIGIT,
            "description": f"ML Server runs on port {6000 + settings.ML_SERVER_DIGIT} (base_port + digit)"
        }
    }


@app.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time run updates"""
    await app.state.manager.connect(websocket, run_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle any client messages if needed
    except WebSocketDisconnect:
        app.state.manager.disconnect(websocket, run_id)


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )