#!/bin/bash

# Setup script for test instance databases
# Initializes Humansa tables in containers on ports 5061-5064

set -e

echo "Setting up test databases..."

# Path to SQL files
SQL_DIR="../HUMANSA_test_environment/sql"

# Setup each test database
for digit in 1 2 3 4; do
    port=$((5060 + digit))
    echo "Setting up database on port $port..."
    
    # Check if container is running
    if ! docker ps | grep -q "humansa_test_db_$digit"; then
        echo "  Warning: Container humansa_test_db_$digit is not running"
        continue
    fi
    
    # Apply Humansa schema
    echo "  Applying Humansa schema..."
    PGPASSWORD=youwo123 psql -h localhost -p $port -U youwo -d youwoai \
        -f "$SQL_DIR/setup_humansa_test_db.sql" 2>/dev/null || echo "    Schema may already exist"
    
    # Apply test data
    echo "  Applying test data..."
    PGPASSWORD=youwo123 psql -h localhost -p $port -U youwo -d youwoai \
        -f ../test_dashboard/apply_standardized_test_data.sql 2>/dev/null || echo "    Data may already exist"
    
    echo "  Database $digit setup complete"
done

echo "All test databases initialized!"