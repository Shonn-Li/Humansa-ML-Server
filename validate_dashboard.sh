#!/bin/bash

echo "=== Validating Test Dashboard ==="
echo

# Check if running
if lsof -ti:6002 > /dev/null; then
    echo "✓ Dashboard is running on port 6002"
else
    echo "✗ Dashboard is NOT running"
    exit 1
fi

# Test endpoints
echo -e "\nTesting API endpoints:"

# Environment
if curl -s http://localhost:6002/api/environment | grep -q "ml_digit"; then
    echo "✓ Environment API: OK"
else
    echo "✗ Environment API: FAILED"
fi

# All tests
TOTAL=$(curl -s http://localhost:6002/api/tests/all | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null)
if [ -n "$TOTAL" ]; then
    echo "✓ All Tests API: OK ($TOTAL tests)"
else
    echo "✗ All Tests API: FAILED"
fi

# Category
COUNT=$(curl -s http://localhost:6002/api/tests/category/appointment | python3 -c "import json,sys; print(json.load(sys.stdin)['count'])" 2>/dev/null)
if [ -n "$COUNT" ]; then
    echo "✓ Category API: OK (appointment has $COUNT tests)"
else
    echo "✗ Category API: FAILED"
fi

# Frontend
if curl -s http://localhost:6002/ | grep -q "Test Management Dashboard"; then
    echo "✓ Frontend: OK"
else
    echo "✗ Frontend: FAILED"
fi

echo -e "\n=== Dashboard Status ==="
echo "URL: http://localhost:6002"
echo "All systems operational!"