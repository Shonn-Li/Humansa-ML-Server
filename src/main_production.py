"""
Production runner for YouWoAI ML Server
This runs the server without debug mode and with proper cleanup
"""

import os
import sys
import signal
import asyncio
import logging
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the app after path is set
from main import create_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()

async def run_server():
    """Run the server with Hypercorn for production"""
    app = create_app()
    
    # Get port from environment
    port = int(os.getenv('ML_SERVER_PORT', '5001'))
    
    # Configure Hypercorn
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    config.workers = 1  # Single worker for simplicity
    config.accesslog = "-"  # Log to stdout
    config.errorlog = "-"   # Log errors to stdout
    config.loglevel = "info"
    
    # Set memory limits
    config.worker_class = "asyncio"
    config.keepalive_timeout = 30
    config.shutdown_timeout = 30
    
    logger.info(f"Starting production ML server on port {port}")
    
    # Run server
    await serve(app, config, shutdown_trigger=shutdown_event.wait)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the async server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shutdown by keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()