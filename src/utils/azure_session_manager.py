#!/usr/bin/env python3
"""
Azure Client Session Manager - Proper cleanup for Azure AI Inference

This module provides proper session management for Azure AI Inference to prevent
unclosed client session warnings.
"""

import asyncio
import logging
import warnings
from contextlib import asynccontextmanager
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class AzureSessionManager:
    """Manages Azure client sessions with proper cleanup"""

    def __init__(self):
        self.session_pool = {}
        self.cleanup_tasks = set()

    async def get_session(self, endpoint: str) -> aiohttp.ClientSession:
        """Get or create a session for the endpoint"""
        if endpoint not in self.session_pool:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
                force_close=True
            )

            session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=120, connect=30)
            )

            self.session_pool[endpoint] = session
            logger.debug(f"Created new session for {endpoint}")

        return self.session_pool[endpoint]

    async def cleanup_sessions(self):
        """Properly close all sessions"""
        for endpoint, session in self.session_pool.items():
            if not session.closed:
                await session.close()
                logger.debug(f"Closed session for {endpoint}")

        self.session_pool.clear()

        # Wait for underlying connections to close
        await asyncio.sleep(0.1)

    async def cleanup_on_exit(self):
        """Cleanup when the application exits"""
        await self.cleanup_sessions()

        # Cancel any pending cleanup tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()

        # Force garbage collection
        import gc
        gc.collect()


# Global session manager
session_manager = AzureSessionManager()


def suppress_azure_warnings():
    """Suppress all Azure-related unclosed session warnings"""

    # Suppress ResourceWarnings completely
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings(
        "ignore", message=".*unclosed.*", category=ResourceWarning)
    warnings.filterwarnings("ignore", message=".*Unclosed.*")

    # Override asyncio's default exception handler
    def custom_exception_handler(loop, context):
        # Check if this is an unclosed session warning
        exception = context.get('exception')
        message = context.get('message', '')

        # Skip unclosed session warnings
        if any(phrase in message.lower() for phrase in [
            'unclosed client session',
            'unclosed connector',
            'unclosed ssl transport',
            'unclosed event loop'
        ]):
            return  # Ignore this warning

        # For other exceptions, use default handling
        if exception:
            logger.warning(f"Asyncio exception: {message}: {exception}")
        else:
            logger.warning(f"Asyncio message: {message}")

    # Set the custom exception handler for the current event loop
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(custom_exception_handler)
    except RuntimeError:
        # No event loop running yet, will be set when one starts
        pass


def configure_clean_azure_logging():
    """Configure clean Azure logging with proper session management"""

    # Apply warning suppression
    suppress_azure_warnings()

    # Configure Azure loggers to only show important messages
    azure_loggers = [
        'azure.core.pipeline.policies.http_logging_policy',
        'azure.ai.inference',
        'azure.core.pipeline',
        'azure.identity',
        'azure.core',
        'aiohttp.access',
        'aiohttp.client',
        'aiohttp.server'
    ]

    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
        azure_logger.propagate = False

    # Specifically handle asyncio logger
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.ERROR)  # Only errors, no warnings
    asyncio_logger.propagate = False

    logger.info("🔇 Clean Azure logging configured - session warnings suppressed")


async def cleanup_azure_sessions():
    """Cleanup function to call after Azure operations"""
    await session_manager.cleanup_sessions()


def setup_application_cleanup():
    """Setup cleanup handlers for application shutdown"""
    import atexit
    import signal
    import threading

    def sync_cleanup():
        """Synchronous cleanup for atexit"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(session_manager.cleanup_on_exit())
            loop.close()
        except Exception as e:
            logger.debug(f"Cleanup error (non-critical): {e}")

    # Register cleanup on normal exit
    atexit.register(sync_cleanup)

    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, cleaning up...")
        sync_cleanup()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
