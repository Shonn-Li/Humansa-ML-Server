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
    export,
    instances
)

from test_dashboard.backend.core.config import settings as app_settings
from test_dashboard.backend.core.database import init_db
from test_dashboard.backend.core.websocket import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from test_dashboard.backend.api import settings


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
    
    # Initialize settings and instance pool based on configuration
    from test_dashboard.backend.core.settings import settings_manager
    from test_dashboard.backend.api.instances import instance_pool
    
    dashboard_settings = settings_manager.get()
    
    # Check if multi-instance mode is enabled
    if dashboard_settings.multi_instance.enabled and dashboard_settings.multi_instance.auto_start:
        num_instances = dashboard_settings.multi_instance.default_instances
        logger.info(f"Multi-instance mode enabled. Initializing {num_instances} instances...")
        try:
            await instance_pool.initialize(num_instances)
            logger.info("Multi-instance pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize instance pool: {e}")
    else:
        logger.info("Multi-instance mode disabled or auto-start disabled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Test Management Dashboard...")
    
    # Shutdown instance pool if initialized
    from test_dashboard.backend.api.instances import instance_pool
    if instance_pool.instances:
        logger.info("Shutting down instance pool...")
        await instance_pool.shutdown()
    
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
app.include_router(instances.router, prefix="/api/instances", tags=["instances"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

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
        "port": app_settings.PORT
    }


@app.get("/system-info")
async def get_system_info():
    """Get system configuration information"""
    from test_dashboard.backend.core.database import is_database_available
    
    # Get environment info from database if available
    environments = []
    if is_database_available():
        from test_dashboard.backend.core.database import execute_query
        env_query = "SELECT name, config, is_active FROM test_management.environments ORDER BY name"
        env_rows = await execute_query(env_query, {})
        environments = [
            {
                "name": row['name'],
                "config": row['config'],
                "active": row['is_active']
            }
            for row in env_rows
        ]
    
    return {
        "dashboard": {
            "backend_port": app_settings.PORT,
            "frontend_port": 3020,
            "api_docs": f"http://localhost:{app_settings.PORT}/docs"
        },
        "database": {
            "host": app_settings.DB_HOST,
            "port": app_settings.DB_PORT,
            "database": app_settings.DB_NAME,
            "user": app_settings.DB_USER,
            "password": "*" * len(app_settings.DB_PASSWORD) if app_settings.DB_PASSWORD else "Not set",
            "schema": "test_management",
            "available": is_database_available()
        },
        "test_environments": environments,
        "ml_server": {
            "base_port": 6000,
            "digit": app_settings.ML_SERVER_DIGIT,
            "test_port": 6000 + app_settings.ML_SERVER_DIGIT,
            "description": f"ML Server runs on port {6000 + app_settings.ML_SERVER_DIGIT} (base_port + digit)"
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
        port=app_settings.PORT,
        reload=app_settings.DEBUG,
        log_level="info"
    )