#!/usr/bin/env python3
"""
Production startup script for YouWoAI ML Server using Hypercorn
"""
import os
import sys
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the app
from main import app

async def main():
    # Configure Hypercorn
    config = Config()
    
    # Get port from environment
    port = int(os.getenv('ML_SERVER_PORT', '5001'))
    config.bind = [f"0.0.0.0:{port}"]
    
    # Production settings
    config.workers = 1  # Single worker for now (can increase based on CPU cores)
    config.accesslog = "-"  # Log to stdout
    config.errorlog = "-"   # Log errors to stdout
    
    # Connection settings
    config.keep_alive_timeout = 75  # Keep connections alive for 75 seconds
    config.h11_max_incomplete_size = 16384  # Increase buffer size
    
    # Graceful shutdown
    config.shutdown_timeout = 30  # 30 seconds for graceful shutdown
    
    # Performance settings
    config.backlog = 100  # Connection backlog
    
    # SSL/TLS (uncomment if using HTTPS)
    # config.certfile = "/path/to/cert.pem"
    # config.keyfile = "/path/to/key.pem"
    
    print(f"🚀 Starting YouWoAI ML Server on port {port} with Hypercorn...")
    print(f"📊 Workers: {config.workers}")
    print(f"⏱️  Keep-alive timeout: {config.keep_alive_timeout}s")
    
    # Use uvloop for better performance if available
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("✅ Using uvloop for enhanced performance")
    except ImportError:
        print("ℹ️  uvloop not available, using default asyncio")
    
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())