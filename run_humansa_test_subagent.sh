#!/bin/bash

# HUMANSA V2 Test Environment with Sub-Agent Architecture
# This script runs the ML server with sub-agent architecture enabled

echo "🚀 Starting HUMANSA V2 Test Environment with Sub-Agent Architecture..."
echo "=================================================="

# Set environment variables
export ENVIRONMENT=test
export HUMANSA_ENHANCED_LOGGING=true
export HUMANSA_USE_SUBAGENT_ARCHITECTURE=true

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source youwo-ml-venv/bin/activate

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment!"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

# Create temporary test runner that enables sub-agent architecture
cat > test_subagent_runner.py << 'EOF'
import asyncio
import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def start_test_server():
    """Start the test server with sub-agent architecture"""
    from src.main import app, initialize_humansa_v2
    from quart import Quart
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    # Initialize Humansa V2 with sub-agent architecture
    db_pool = await app.db_pool()
    await initialize_humansa_v2(db_pool, use_subagent_architecture=True)
    
    # Configure Hypercorn
    config = Config()
    config.bind = ["0.0.0.0:6001"]
    config.workers = 1
    
    print("\n✅ HUMANSA V2 Test Server Started with Sub-Agent Architecture!")
    print("📍 Server running on: http://localhost:6001")
    print("🚀 Sub-Agent Architecture: ENABLED")
    print("📊 Enhanced Logging: ENABLED")
    print("\nPress Ctrl+C to stop the server")
    
    # Run server
    await hypercorn.asyncio.serve(app, config)

if __name__ == "__main__":
    asyncio.run(start_test_server())
EOF

# Run the test server
echo ""
echo "🌟 Starting HUMANSA V2 with Sub-Agent Architecture..."
echo "=================================================="
python test_subagent_runner.py

# Cleanup
rm -f test_subagent_runner.py