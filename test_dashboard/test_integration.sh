#!/bin/bash

# Test Dashboard Integration Test
# ===============================
# This script tests the complete dashboard functionality

echo "Test Dashboard Integration Test"
echo "==============================="

# Test Backend Direct
echo "Testing backend API..."
BACKEND_HEALTH=$(curl -s http://localhost:6002/health | jq -r '.status')
if [ "$BACKEND_HEALTH" = "healthy" ]; then
    echo "✓ Backend health check passed"
else
    echo "✗ Backend health check failed"
    exit 1
fi

# Test environments endpoint
ENV_COUNT=$(curl -s http://localhost:6002/api/environments | jq -r 'length')
if [ "$ENV_COUNT" -gt 0 ]; then
    echo "✓ Backend environments API working ($ENV_COUNT environments)"
else
    echo "✗ Backend environments API failed"
    exit 1
fi

# Test tests endpoint
TEST_COUNT=$(curl -s http://localhost:6002/api/tests | jq -r 'length')
if [ "$TEST_COUNT" -gt 0 ]; then
    echo "✓ Backend tests API working ($TEST_COUNT tests)"
else
    echo "✗ Backend tests API failed"
    exit 1
fi

# Test Frontend Direct
echo "Testing frontend server..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3020)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✓ Frontend server responding"
else
    echo "✗ Frontend server not responding (status: $FRONTEND_STATUS)"
    exit 1
fi

# Test Frontend API Proxy
echo "Testing frontend API proxy..."
PROXY_ENV_COUNT=$(curl -s http://localhost:3020/api/environments | jq -r 'length')
if [ "$PROXY_ENV_COUNT" = "$ENV_COUNT" ]; then
    echo "✓ Frontend API proxy working"
else
    echo "✗ Frontend API proxy failed"
    exit 1
fi

# Test trailing slash issue fix
echo "Testing trailing slash fix..."
NO_SLASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6002/api/environments)
WITH_SLASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6002/api/environments/)

if [ "$NO_SLASH_STATUS" = "200" ] && [ "$WITH_SLASH_STATUS" = "200" ]; then
    echo "✓ Trailing slash issue fixed (both return 200)"
else
    echo "✗ Trailing slash issue not fixed (no slash: $NO_SLASH_STATUS, with slash: $WITH_SLASH_STATUS)"
    exit 1
fi

echo ""
echo "🎉 All integration tests passed!"
echo "Dashboard is working correctly:"
echo "  - Backend API endpoints working"
echo "  - Frontend server responding"
echo "  - API proxy functioning"
echo "  - Trailing slash issue resolved"
echo ""
echo "Access the dashboard at: http://localhost:3020"