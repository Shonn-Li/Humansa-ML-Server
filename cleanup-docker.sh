#!/bin/bash

# Docker Cleanup Script for ML Server
# This script cleans up all ML server related Docker resources

echo "🧹 Cleaning up ML Server Docker resources..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[CLEANUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Stop all ml-server containers
print_status "Stopping all ml-server containers..."
docker ps -a | grep -E "(ml-server|youwo.*ml)" | awk '{print $1}' | xargs -r docker stop

# Remove all ml-server containers
print_status "Removing all ml-server containers..."
docker ps -a | grep -E "(ml-server|youwo.*ml)" | awk '{print $1}' | xargs -r docker rm

# Stop containers using port 5001
print_status "Stopping containers using port 5001..."
docker ps --filter "publish=5001" -q | xargs -r docker stop
docker ps -a --filter "publish=5001" -q | xargs -r docker rm

# Remove ml-server images
print_status "Removing ml-server images..."
docker images | grep -E "(ml-server|youwo.*ml)" | awk '{print $3}' | xargs -r docker rmi -f

# Kill processes on port 5001
print_status "Checking for processes on port 5001..."
if lsof -i :5001 > /dev/null 2>&1; then
    print_warning "Found processes on port 5001, terminating..."
    lsof -ti :5001 | xargs -r kill -9
    sleep 2
    print_status "Port 5001 cleared"
else
    print_status "Port 5001 is free"
fi

# Clean up Docker system
print_status "Cleaning up Docker system..."
docker system prune -f

# Clean up dangling volumes
print_status "Cleaning up dangling volumes..."
docker volume prune -f

print_status "✅ Cleanup complete!"
print_status "Port 5001 is now available"
print_status "All ML server containers and images have been removed"
