"""
YouWoAI ML Server - Test Instance on Port 5002

This is a test instance of the ML server for development and testing purposes.
It runs on port 5002 to avoid conflicts with the main server on port 5001.
"""

import os
import sys

# CRITICAL: Add current directory to Python path for imports to work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the main server module
from main import app, logger

if __name__ == "__main__":
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    
    config = Config()
    config.bind = ["0.0.0.0:5002"]  # Different port for testing
    config.workers = 1
    config.accesslog = "-"
    config.errorlog = "-"
    config.loglevel = "INFO"
    
    logger.info("🚀 Starting YouWoAI ML Test Server on port 5002...")
    logger.info("📍 This is a test instance for development purposes")
    logger.info("🔗 Test endpoint: http://localhost:5002/v1/chat/completions")
    logger.info("🔗 Multi-agent endpoint: http://localhost:5002/v1/multi-agent/response")
    
    asyncio.run(serve(app, config))