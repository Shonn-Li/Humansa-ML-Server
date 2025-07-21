#!/bin/bash
# Start ML server on port 5002 for testing

echo "Starting ML Server on port 5002..."

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Set test environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export ML_SERVER_PORT=5002
export DB_NAME=youwo_test
export DB_PORT=5454

# Kill any existing process on port 5002
echo "Checking for existing process on port 5002..."
lsof -ti:5002 | xargs kill -9 2>/dev/null

# Start the server
echo "Starting server..."
python src/main.py --port 5002