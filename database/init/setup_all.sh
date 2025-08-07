#!/bin/bash
# Complete setup script for test dashboard environment
# This script initializes all databases needed for the test dashboard

set -e  # Exit on error

echo "==================================="
echo "Test Dashboard Database Setup"
echo "==================================="

# Configuration
DIGIT=${DIGIT:-5}
DB_HOST=${DB_HOST:-localhost}
DB_PASSWORD=${DB_PASSWORD:-youwo123}

echo "Using DIGIT=$DIGIT"
echo ""

# Step 1: Initialize test management schema (main database)
echo "Step 1: Setting up test management schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p 5432 -U postgres -d test$DIGIT \
  -f test_management/01_schema.sql \
  -q --single-transaction

echo "✅ Test management schema created"
echo ""

# Step 2: Start Docker containers for test instances
echo "Step 2: Starting test instance containers..."
cd ../../test_dashboard
docker-compose -f docker-compose.test-instances.yml up -d
cd ../database/init

# Wait for containers to be ready
echo "Waiting for containers to start..."
sleep 10

# Step 3: Initialize each test instance
echo "Step 3: Initializing test instances..."
for i in 1 2 3 4; do
  PORT=$((5060 + i))
  echo "  Initializing instance $i on port $PORT..."
  
  # Check if container is ready
  until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $PORT -U youwo -d youwoai -c '\q' 2>/dev/null; do
    echo "    Waiting for port $PORT to be ready..."
    sleep 2
  done
  
  # Apply initialization script
  PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $PORT -U youwo -d youwoai \
    -f test_instances/init_instance.sql \
    -q --single-transaction
    
  echo "  ✅ Instance $i initialized"
done

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Database Status:"
echo "  - Test Management DB: test$DIGIT on port 5432"
echo "  - Test Instance 1: youwoai on port 5061"
echo "  - Test Instance 2: youwoai on port 5062"
echo "  - Test Instance 3: youwoai on port 5063"
echo "  - Test Instance 4: youwoai on port 5064"
echo ""
echo "To start the test dashboard:"
echo "  cd ../../"
echo "  ./launch_dashboard.sh"
echo ""