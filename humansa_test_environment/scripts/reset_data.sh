#!/bin/bash

# Quick reset script - keeps containers but resets data

echo "🔄 Resetting Humansa Test Data"
echo "==============================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if container is running
if ! docker ps | grep -q humansa_test_postgres; then
    echo "❌ Test database is not running. Start it first with:"
    echo "   cd humansa_test_environment"
    echo "   docker-compose -f docker/docker-compose.yml up -d"
    exit 1
fi

# Step 1: Drop and recreate all tables
echo "1. Recreating database schema..."
docker exec -i humansa_test_postgres psql -U youwo -d youwoai < "$ROOT_DIR/sql/setup_humansa_test_db.sql"

# Step 2: Activate virtual environment if exists
if [ -f "$ROOT_DIR/../youwo-ml-venv/bin/activate" ]; then
    source "$ROOT_DIR/../youwo-ml-venv/bin/activate"
fi

# Step 3: Repopulate test data
echo "2. Populating fresh test data..."
cd "$ROOT_DIR"
DB_PORT=5456 python3 scripts/populate_humansa_test_data.py

echo "✅ Test data reset complete!"