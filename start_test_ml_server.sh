#!/bin/bash

# Start ML server with test environment configuration

echo "Starting ML server with test environment configuration..."

# Kill any existing processes on port 6001
lsof -ti:6001 | xargs kill -9 2>/dev/null || true

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Export test environment variables (override .env)
export DB_HOST=localhost
export DB_PORT=5456
export DB_USER=youwo
export DB_PASSWORD=youwo123
export DB_NAME=youwoai
export ML_SERVER_PORT=6001
export ENVIRONMENT=test

# Start the server
echo "Starting server on port 6001 with test database on port 5456..."
python3 src/main.py --port 6001