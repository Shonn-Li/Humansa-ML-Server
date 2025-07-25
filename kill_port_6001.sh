#!/bin/bash
# Kill any process using port 6001

echo "🔍 Checking for processes on port 6001..."

# Method 1: Using lsof
if command -v lsof &> /dev/null; then
    PIDS=$(lsof -ti:6001)
    if [ ! -z "$PIDS" ]; then
        echo "Found processes on port 6001: $PIDS"
        echo "Killing processes..."
        echo $PIDS | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ Processes killed"
    else
        echo "✅ No processes found on port 6001"
    fi
fi

# Method 2: Kill any Python processes running main.py
echo "🔍 Checking for Python ML server processes..."
PYTHON_PIDS=$(ps aux | grep -E "python.*main\.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$PYTHON_PIDS" ]; then
    echo "Found Python ML server processes: $PYTHON_PIDS"
    echo "Killing processes..."
    echo $PYTHON_PIDS | xargs kill -9 2>/dev/null
    sleep 2
    echo "✅ Python processes killed"
else
    echo "✅ No Python ML server processes found"
fi

# Verify port is free
if lsof -i:6001 > /dev/null 2>&1; then
    echo "❌ WARNING: Port 6001 is still in use!"
    exit 1
else
    echo "✅ Port 6001 is now free"
fi