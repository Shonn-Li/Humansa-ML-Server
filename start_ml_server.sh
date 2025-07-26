#!/bin/bash

# ML Server Startup Script
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Set environment variables
export PYTHONUNBUFFERED=1
export ML_SERVER_PORT=5005

# Kill any existing processes on port 5005
lsof -ti:5005 | xargs kill -9 2>/dev/null || true

echo "Starting ML Server on port 5005..."

# Run the server
python src/main.py