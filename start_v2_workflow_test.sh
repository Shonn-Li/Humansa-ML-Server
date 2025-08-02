#!/bin/bash
# Start V2 test server with workflow orchestrator enabled

echo "Starting HUMANSA V2 Test Server with Workflow Orchestrator..."

# Kill any existing server on port 6001
if lsof -i :6001 > /dev/null 2>&1; then
    echo "Killing existing server on port 6001..."
    lsof -ti :6001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Set environment variables
export ENVIRONMENT=test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ML_SERVER_PORT=6001
export HUMANSA_ENHANCED_LOGGING=true
export HUMANSA_USE_WORKFLOW_ORCHESTRATOR=true
export USE_AZURE_OPENAI=true

# Show configuration
echo "Configuration:"
echo "  - HUMANSA_USE_WORKFLOW_ORCHESTRATOR: $HUMANSA_USE_WORKFLOW_ORCHESTRATOR"
echo "  - HUMANSA_ENHANCED_LOGGING: $HUMANSA_ENHANCED_LOGGING"
echo "  - DB: $DB_HOST:$DB_PORT/$DB_NAME"
echo "  - Server port: $ML_SERVER_PORT"

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Start server in background
echo "Starting server..."
python3 -m src.main --port 6001 > server_v2_workflow.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo -n "Waiting for server to start"
for i in {1..30}; do
    if curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
        echo -e "\n✅ Server is ready!"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:6001/v2/humansa/health > /dev/null 2>&1; then
    echo -e "\n❌ Server failed to start. Check server_v2_workflow.log"
    tail -20 server_v2_workflow.log
    exit 1
fi

# Check V2 health
echo -e "\nV2 Health Check:"
curl -s http://localhost:6001/v2/humansa/health | python3 -m json.tool

echo -e "\nServer is running with Workflow Orchestrator enabled!"
echo "Logs: tail -f server_v2_workflow.log"
echo "To stop: kill $SERVER_PID"