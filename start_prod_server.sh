#!/bin/bash
# Start ML server with production database

# Activate virtual environment
source youwo-ml-venv/bin/activate

# Set production database environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_USERNAME=postgres
export DB_PASSWORD=031203
export DB_ACTIVE_DATABASE=youwoai

# Start the server
echo "Starting ML server with production database..."
echo "Database: $DB_ACTIVE_DATABASE on port $DB_PORT"
python src/main.py