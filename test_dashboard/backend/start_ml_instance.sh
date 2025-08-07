#!/bin/bash
# Start ML server instance with dependencies

# Get arguments
PORT=$1
DIGIT=$2

# Set environment
export ML_SERVER_PORT=$PORT
export DIGIT=$DIGIT
export DB_HOST=127.0.0.1
export DB_PORT=$((5060 + $DIGIT))
export DB_NAME="youwoai"
export DB_USER=youwo
export DB_PASSWORD=youwo123
export INSTANCE_ID=$DIGIT
export HUMANSA_ENHANCED_LOGGING=true

# Go to repo root
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/humansa-ml-server

# Check if virtual environment exists and create if not
if [ ! -d "youwo-ml-venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv youwo-ml-venv
fi

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Install dependencies from requirements.txt if needed, but skip unoconv
if [ ! -f "youwo-ml-venv/.deps_installed" ]; then
    echo "Installing dependencies..."
    # Remove unoconv line temporarily
    grep -v "unoconv" requirements.txt > /tmp/requirements_temp.txt
    pip install -r /tmp/requirements_temp.txt
    touch youwo-ml-venv/.deps_installed
fi

# Start the server
exec python -m src.main --port $PORT