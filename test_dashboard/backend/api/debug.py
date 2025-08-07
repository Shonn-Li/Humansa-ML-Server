"""
Debug endpoints for troubleshooting
"""

from fastapi import APIRouter
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test-async")
async def test_async():
    """Test if async execution works"""
    logger.info("Test async endpoint called")
    
    async def background_work():
        logger.info("Background work started")
        await asyncio.sleep(1)
        logger.info("Background work completed")
        return "done"
    
    # Start background task
    task = asyncio.create_task(background_work())
    
    return {"message": "Async test started", "status": "ok"}

@router.get("/test-imports")
async def test_imports():
    """Test if all imports work"""
    try:
        import httpx
        httpx_ok = True
    except Exception as e:
        httpx_ok = str(e)
    
    try:
        from test_dashboard.backend.api.tests import test_definitions
        test_defs_count = len(test_definitions)
    except Exception as e:
        test_defs_count = str(e)
    
    try:
        from test_dashboard.backend.core.config import settings
        ml_port = settings.ML_SERVER_PORT
    except Exception as e:
        ml_port = str(e)
    
    return {
        "httpx": httpx_ok,
        "test_definitions": test_defs_count,
        "ml_port": ml_port
    }