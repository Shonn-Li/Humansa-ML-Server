#!/bin/bash

# Humansa Test Environment Setup Script

echo "🏥 Setting up Humansa Test Environment"
echo "======================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
    for i in {1..30}; do
        if docker exec humansa_test_postgres pg_isready -U youwo -d youwoai > /dev/null 2>&1; then
            echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    return 1
}

# Step 1: Stop any existing containers
echo -e "\n${YELLOW}1. Stopping existing containers...${NC}"
docker-compose -f "$ROOT_DIR/docker/docker-compose.yml" down

# Step 2: Start test database
echo -e "\n${YELLOW}2. Starting test database...${NC}"
docker-compose -f "$ROOT_DIR/docker/docker-compose.yml" up -d

# Step 3: Wait for database to be ready
if ! wait_for_postgres; then
    exit 1
fi

# Step 4: Setup database schema
echo -e "\n${YELLOW}3. Setting up database schema...${NC}"
docker exec -i humansa_test_postgres psql -U youwo -d youwoai < "$ROOT_DIR/sql/setup_humansa_test_db.sql"

# Step 5: Check for virtual environment
echo -e "\n${YELLOW}4. Checking Python environment...${NC}"
if [ -f "../youwo-ml-venv/bin/activate" ]; then
    echo "🐍 Using existing virtual environment..."
    source ../youwo-ml-venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Install any missing dependencies
echo "Installing required dependencies..."
pip install asyncpg psycopg2-binary > /dev/null 2>&1

# Step 6: Set environment variables
echo -e "\n${YELLOW}5. Setting environment variables...${NC}"
export DB_HOST=localhost
export DB_PORT=5456
export DB_NAME=youwoai
export DB_USER=youwo
export DB_PASSWORD=youwo123

# Step 7: Run database population script
echo -e "\n${YELLOW}6. Populating test database...${NC}"
cd "$ROOT_DIR"
python3 scripts/populate_humansa_test_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test database populated successfully!${NC}"
else
    echo -e "${RED}❌ Failed to populate test database${NC}"
    exit 1
fi

# Step 7a: Setup Mem0 for memory management
echo -e "\n${YELLOW}6a. Setting up Mem0 memory layer...${NC}"
cd "$ROOT_DIR"
./scripts/setup_mem0.sh

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Mem0 setup completed successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Mem0 setup failed (optional - tests can still run)${NC}"
fi

# Step 8: Skip PgAdmin for isolated environment
echo -e "\n${YELLOW}7. Skipping PgAdmin (not needed for test environment)...${NC}"

# Step 9: Create test environment file
echo -e "\n${YELLOW}8. Creating test environment configuration...${NC}"
cat > .env.test << EOF
# Humansa Test Environment Configuration
DB_HOST=localhost
DB_PORT=5456
DB_NAME=youwoai
DB_USER=youwo
DB_PASSWORD=youwo123
ML_SERVER_PORT=5001

# API Keys (add your keys here)
OPENAI_API_KEY=your_openai_key_here
EOF

echo -e "${GREEN}✅ Created .env.test file${NC}"

# Summary
echo -e "\n${GREEN}🎉 Humansa Test Environment Setup Complete!${NC}"
echo "========================================"
echo "Test Database: localhost:5456"
echo "PgAdmin: http://localhost:5455"
echo ""
echo "To test the connection:"
echo "  cd humansa_test_environment"
echo "  python3 tests/test_connection.py"
echo ""
echo "To reset data only:"
echo "  cd humansa_test_environment"
echo "  ./scripts/reset_data.sh"
echo ""
echo "To clean up everything:"
echo "  cd humansa_test_environment"
echo "  ./cleanup.sh"
echo ""