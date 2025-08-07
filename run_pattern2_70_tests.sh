#!/bin/bash

# Run HUMANSA V2 Pattern 2 with 70 test cases
echo "🚀 Starting HUMANSA V2 Pattern 2 Test Suite"
echo "============================================"

# Set environment variables for Pattern 2
export HUMANSA_USE_PATTERN2=true
export HUMANSA_ENHANCED_LOGGING=true
export ML_SERVER_PORT=6001
export ENVIRONMENT=test

# Check if server is running
echo "🔍 Checking if test server is running on port $ML_SERVER_PORT..."
if ! nc -z localhost $ML_SERVER_PORT 2>/dev/null; then
    echo "❌ Test server is not running on port $ML_SERVER_PORT"
    echo "Please start the test server first:"
    echo "  ./run_HUMANSA_test_environment_v2_enhanced.sh"
    exit 1
fi

echo "✅ Test server is running"
echo ""
echo "🔧 Configuration:"
echo "  - Pattern 2 Enabled: $HUMANSA_USE_PATTERN2"
echo "  - Enhanced Logging: $HUMANSA_ENHANCED_LOGGING"
echo "  - Test Port: $ML_SERVER_PORT"
echo "  - Log File: pattern2_test_$(date +%Y%m%d_%H%M%S).log"
echo ""

# Activate virtual environment
if [ -d "youwo-ml-venv" ]; then
    echo "🐍 Activating virtual environment..."
    source youwo-ml-venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Run the Pattern 2 test suite
echo "🧪 Running 70 test cases with Pattern 2 orchestrator..."
echo "============================================"
python test_pattern2_70_cases.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Pattern 2 test suite completed successfully!"
    echo "📋 Check the log file for detailed results"
else
    echo ""
    echo "❌ Pattern 2 test suite failed"
    echo "Check the logs for errors"
fi

# Show latest log file
echo ""
echo "📄 Latest log file:"
ls -la pattern2_test_*.log | tail -1