#!/bin/bash

# Mem0 Setup for Humansa Test Environment
# This script is called by the main setup.sh

echo "🧠 Setting up Mem0 for Humansa..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if database is ready
check_db() {
    PGPASSWORD=youwo123 psql -h localhost -p 5456 -U youwo -d youwoai -c "SELECT 1" > /dev/null 2>&1
    return $?
}

# Setup Mem0 schema
setup_mem0_schema() {
    echo -e "${YELLOW}Creating Mem0 schema and permissions...${NC}"
    
    # Use the existing SQL file
    PGPASSWORD=youwo123 psql -h localhost -p 5456 -U youwo -d youwoai < ../sql/setup_mem0_test.sql
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Mem0 schema created successfully${NC}"
        return 0
    else
        echo "❌ Failed to create Mem0 schema"
        return 1
    fi
}

# Install Mem0 if not already installed
install_mem0() {
    echo -e "${YELLOW}Checking Mem0 installation...${NC}"
    
    if python -c "import mem0" 2>/dev/null; then
        echo -e "${GREEN}✅ Mem0 is already installed${NC}"
    else
        echo "Installing Mem0..."
        pip install mem0ai asyncpg
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Mem0 installed successfully${NC}"
        else
            echo "❌ Failed to install Mem0"
            return 1
        fi
    fi
}

# Main execution
if check_db; then
    setup_mem0_schema
    install_mem0
else
    echo "❌ Database not ready. Please ensure Humansa test database is running."
    exit 1
fi