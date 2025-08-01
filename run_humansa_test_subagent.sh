#!/bin/bash

# HUMANSA V2 Test Environment with Sub-Agent Architecture
# This script runs the ML server with sub-agent architecture enabled

echo "🚀 Starting HUMANSA V2 Test Environment with Sub-Agent Architecture..."
echo "=================================================="

# Set environment variables for TEST ENVIRONMENT
export ENVIRONMENT=test
export HUMANSA_ENHANCED_LOGGING=true
export HUMANSA_USE_SUBAGENT_ARCHITECTURE=true
export PORT=6001  # TEST ENVIRONMENT PORT

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

# Run the test server directly
echo ""
echo "🌟 Starting HUMANSA V2 with Sub-Agent Architecture..."
echo "=================================================="
python -m src.main

# Cleanup
rm -f test_subagent_runner.py