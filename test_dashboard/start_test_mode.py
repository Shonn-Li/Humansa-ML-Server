#!/usr/bin/env python3
"""
Test Dashboard - Test Mode Startup
=================================

Starts the test dashboard backend with database initialization disabled
for testing purposes.
"""

import os
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variable to skip database initialization
os.environ["SKIP_DB_INIT"] = "true"

# Now import and run the main application
from test_dashboard.backend.main import app
import uvicorn

if __name__ == "__main__":
    print("Starting Test Dashboard in test mode (no database)...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=6002,
        log_level="info"
    )