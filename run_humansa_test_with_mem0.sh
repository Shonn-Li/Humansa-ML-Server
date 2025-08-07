#!/bin/bash

# Run HUMANSA Test Environment with Mem0 Integration Test
# This script starts the test environment and automatically runs Mem0 tests

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}HUMANSA Test Environment with Mem0 Testing${NC}"
echo -e "${GREEN}================================================${NC}"

# Step 1: Start the test environment
echo -e "\n${YELLOW}Step 1: Starting HUMANSA test environment...${NC}"
./run_HUMANSA_test_environment.sh

# Wait for services to be fully ready
echo -e "\n${YELLOW}Waiting for services to stabilize...${NC}"
sleep 10

# Step 2: Check if ML server is running
echo -e "\n${YELLOW}Step 2: Checking ML server health...${NC}"
if curl -s http://localhost:6001/health > /dev/null; then
    echo -e "${GREEN}✓ ML Server is healthy on port 6001${NC}"
else
    echo -e "${RED}✗ ML Server is not responding on port 6001${NC}"
    echo -e "${YELLOW}Please ensure the test environment is running with ./run_HUMANSA_test_environment.sh${NC}"
    # Don't exit, continue with existing server
fi

# Step 3: Check database connectivity
echo -e "\n${YELLOW}Step 3: Verifying database connectivity...${NC}"
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -c "SELECT 1;" > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database is accessible${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    exit 1
fi

# Step 4: Check if Mem0 schema exists
echo -e "\n${YELLOW}Step 4: Checking Mem0 schema...${NC}"
SCHEMA_EXISTS=$(PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d test4 -t -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mem0_test';" | xargs)
if [ "$SCHEMA_EXISTS" = "mem0_test" ]; then
    echo -e "${GREEN}✓ Mem0 test schema exists${NC}"
else
    echo -e "${YELLOW}! Mem0 test schema will be created by the test${NC}"
fi

# Step 5: Activate virtual environment if it exists
echo -e "\n${YELLOW}Step 5: Setting up Python environment...${NC}"
if [ -d "youwo-ml-venv" ]; then
    source youwo-ml-venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}! No virtual environment found, using system Python${NC}"
fi

# Step 6: Run Mem0 integration tests
echo -e "\n${YELLOW}Step 6: Running Mem0 integration tests...${NC}"
echo -e "${YELLOW}This will test all 10 memory scenarios...${NC}\n"

# Set environment variables for test
export DB_HOST=localhost
export DB_PORT=5454
export DB_USER=postgres
export DB_PASSWORD=12931
export DB_NAME=test4
export ENVIRONMENT=test

# Run the tests
python test_mem0_humansa_integration.py

# Check test results
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}================================================${NC}"
    echo -e "${GREEN}✓ All Mem0 integration tests completed!${NC}"
    echo -e "${GREEN}================================================${NC}"
else
    echo -e "\n${RED}================================================${NC}"
    echo -e "${RED}✗ Some tests failed. Check the output above.${NC}"
    echo -e "${RED}================================================${NC}"
fi

# Step 7: Quick API test with Mem0
echo -e "\n${YELLOW}Step 7: Testing Mem0 via API...${NC}"

# Test adding a memory via API
echo -e "${YELLOW}Adding test memory via API...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:6001/v2/humansa/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_10001",
    "messages": [
      {"role": "user", "content": "I prefer Dr. Chen for cardiology appointments"},
      {"role": "assistant", "content": "I have noted your preference for Dr. Chen for cardiology appointments."}
    ]
  }')

if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ Memory added successfully via API${NC}"
else
    echo -e "${RED}✗ Failed to add memory via API${NC}"
    echo "Response: $RESPONSE"
fi

# Test retrieving memories
echo -e "${YELLOW}Retrieving memories via API...${NC}"
SEARCH_RESPONSE=$(curl -s -X POST http://localhost:6001/v2/humansa/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_10001",
    "query": "doctor preference"
  }')

if echo "$SEARCH_RESPONSE" | grep -q "Dr. Chen"; then
    echo -e "${GREEN}✓ Memory retrieved successfully via API${NC}"
else
    echo -e "${YELLOW}! Memory search returned: $SEARCH_RESPONSE${NC}"
fi

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}Test environment is running with Mem0 active!${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "\nYou can now:"
echo -e "  - Access the ML server at: http://localhost:6001"
echo -e "  - View test results in: mem0_test_results_*.json"
echo -e "  - Run additional tests with: python test_mem0_humansa_integration.py"
echo -e "\nTo stop the environment: docker-compose -f HUMANSA_test_environment/docker-compose.yml down"