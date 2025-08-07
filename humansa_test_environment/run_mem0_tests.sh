#!/bin/bash

# Run Mem0 integration tests in Humansa test environment

echo "========================================"
echo "Mem0 Integration Test Suite for Humansa"
echo "========================================"

# Set environment variables for test
export DB_HOST=localhost
export DB_PORT=5456  # Humansa test DB port
export DB_USER=youwo
export DB_PASSWORD=youwo123
export DB_NAME=youwoai

# Check if Azure credentials are set (optional for testing with mock)
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: AZURE_OPENAI_API_KEY not set. Tests will run with mock memory."
    export AZURE_OPENAI_API_KEY=test-key
    export AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com
    export AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
fi

# Function to check if database is ready
check_db() {
    echo "Checking database connection..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1
    return $?
}

# Function to setup Mem0 schema
setup_mem0_schema() {
    echo "Setting up Mem0 test schema..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < sql/setup_mem0_test.sql
    
    if [ $? -eq 0 ]; then
        echo "✓ Mem0 schema setup completed"
    else
        echo "✗ Failed to setup Mem0 schema"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo "Installing Mem0 dependencies..."
    pip install mem0ai asyncpg pytest
    
    if [ $? -eq 0 ]; then
        echo "✓ Dependencies installed"
    else
        echo "✗ Failed to install dependencies"
        exit 1
    fi
}

# Main execution
echo ""
echo "1. Starting Humansa test database..."
cd "$(dirname "$0")"

# Check if docker compose is running
if ! docker ps | grep -q humansa_test_postgres; then
    echo "Starting docker containers..."
    cd docker
    docker-compose up -d
    cd ..
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    for i in {1..30}; do
        if check_db; then
            echo "✓ Database is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
else
    echo "✓ Database container already running"
fi

# Ensure database is accessible
if ! check_db; then
    echo "✗ Cannot connect to database"
    exit 1
fi

echo ""
echo "2. Setting up Mem0 schema..."
setup_mem0_schema

echo ""
echo "3. Installing Python dependencies..."
install_dependencies

echo ""
echo "4. Running Mem0 integration tests..."
cd ..  # Go back to ML server root
python test_mem0_humansa_integration.py

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
echo "========================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests completed successfully!"
else
    echo "✗ Some tests failed. Check the logs above."
fi
echo "========================================"

# Optional: Keep database running for inspection
echo ""
echo "Database is still running on port 5456"
echo "To stop it, run: cd humansa_test_environment/docker && docker-compose down"
echo ""
echo "To connect via psql:"
echo "PGPASSWORD=youwo123 psql -h localhost -p 5456 -U youwo -d youwoai"

exit $TEST_EXIT_CODE