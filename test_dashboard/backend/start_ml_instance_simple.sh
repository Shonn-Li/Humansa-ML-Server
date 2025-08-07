#!/bin/bash
# Simple ML server instance starter

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

# Activate virtual environment
source /Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/humansa-ml-server/youwo-ml-venv/bin/activate

# Start the server using venv Python
exec python -m src.main --port $PORT