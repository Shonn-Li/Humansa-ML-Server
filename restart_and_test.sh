#!/bin/bash
# Restart ML server with new changes and run tests

echo "Stopping ML server..."
lsof -ti:5001 | xargs kill -9 2>/dev/null
sleep 2

echo "Starting ML server with new features..."
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
nohup python src/main.py > ml_server_new.log 2>&1 &

echo "Waiting for server to start..."
sleep 10

# Check if server is running
if lsof -i:5001 > /dev/null; then
    echo "✅ ML server is running"
    
    echo -e "\nRunning feature tests..."
    python test_new_features.py
else
    echo "❌ ML server failed to start"
    echo "Check ml_server_new.log for errors"
fi