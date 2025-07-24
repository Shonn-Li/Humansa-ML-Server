#!/bin/bash

# Humansa Test Environment Cleanup Script

echo "🧹 Cleaning up Humansa Test Environment"
echo "========================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Stop and remove containers
echo -e "\n${YELLOW}1. Stopping and removing test containers...${NC}"
docker-compose -f "$ROOT_DIR/docker/docker-compose.yml" down -v

# Step 2: Remove any orphaned containers
echo -e "\n${YELLOW}2. Removing orphaned containers...${NC}"
docker container prune -f

# Step 3: Remove test volumes explicitly
echo -e "\n${YELLOW}3. Removing test volumes...${NC}"
docker volume rm humansa_test_postgres_data 2>/dev/null || true

# Step 4: Skip virtual environment cleanup (using main environment)
echo -e "\n${YELLOW}4. Keeping virtual environment (shared with main project)...${NC}"

# Step 5: Clean up any test artifacts
echo -e "\n${YELLOW}5. Cleaning test artifacts...${NC}"
rm -f .env.test 2>/dev/null || true
rm -f requirements-test.txt 2>/dev/null || true

# Summary
echo -e "\n${GREEN}✅ Cleanup complete!${NC}"
echo "========================================"
echo "The test environment has been completely removed."
echo "You can run ./setup.sh to create a fresh environment."