#!/bin/bash

# Start YouWoAI ML Test Server on port 5002

echo "🚀 Starting YouWoAI ML Test Server on port 5002..."

# Kill any existing process on port 5002
echo "🔍 Checking for existing processes on port 5002..."
lsof -ti tcp:5002 | xargs -r kill -9 2>/dev/null || true

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/youwo-ml-venv/bin/activate

# Start the test server
echo "🏃 Starting test server..."
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
python src/main_test.py